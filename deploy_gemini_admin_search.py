"""
Deploy Script: Gemini Admin Search Skill → Hermes Server (Debian)
================================================================
1. Crea la carpeta de skill en el servidor
2. Sube gemini_admin_search.py, SKILL.md y archivos_indexados.json
3. Configura la variable de entorno GEMINI_API_KEY
4. Instala google-generativeai si no está disponible
5. Registra el skill path en config.yaml
6. Actualiza el system prompt del webhook channel
7. Reinicia el servicio hermes-it

Prerequisito: Ejecutar cargar_carpeta_onedrive.py primero para generar
el archivos_indexados.json con los IDs de Google.
"""

import paramiko
import os
import sys

# ── Configuración ──────────────────────────────────────────────
DEBIAN_HOST = "10.147.18.204"
DEBIAN_USER = "root"
DEBIAN_PASS = "Twinc3pt.2"

# API Key de Google AI Studio (la que proporcionaste)
GEMINI_API_KEY = "AIzaSyCwq1nA3hcsUbT-uZ5UcxLeq4bGeGCiO_s"

# Rutas locales
LOCAL_SKILL_PY = r"c:\source\Synapse\gemini_admin_search.py"
LOCAL_SKILL_MD = r"c:\source\Synapse\gemini_admin_search_SKILL.md"
LOCAL_INDEX_JSON = r"c:\source\Synapse\archivos_indexados.json"

# Rutas remotas
REMOTE_SKILL_DIR = "/root/.hermes/skills/gemini_admin_search"
REMOTE_SKILL_PY = f"{REMOTE_SKILL_DIR}/gemini_admin_search.py"
REMOTE_SKILL_MD = f"{REMOTE_SKILL_DIR}/SKILL.md"
REMOTE_INDEX_JSON = f"{REMOTE_SKILL_DIR}/archivos_indexados.json"
REMOTE_CONFIG = "/root/.hermes/config.yaml"


def run_cmd(ssh, cmd, label=""):
    """Execute a remote command and print output."""
    print(f"  → {label or cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(f"    {out}")
    if err and "WARNING" not in err.upper():
        print(f"    [stderr] {err}")
    return out


def main():
    print("=" * 60)
    print("Deploy: Gemini Admin Search Skill → Hermes Server")
    print("=" * 60)

    # ── Conectar ───────────────────────────────────────────────
    print("\n[1/7] Conectando al servidor Debian...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(DEBIAN_HOST, username=DEBIAN_USER, password=DEBIAN_PASS)
    print("  ✅ Conectado")

    # ── Crear directorio ───────────────────────────────────────
    print("\n[2/7] Creando directorio de skill...")
    run_cmd(ssh, f"mkdir -p {REMOTE_SKILL_DIR}", "mkdir")
    run_cmd(ssh, f"chmod 755 {REMOTE_SKILL_DIR}", "chmod")

    # ── Subir archivos ─────────────────────────────────────────
    print("\n[3/7] Subiendo archivos...")
    sftp = ssh.open_sftp()

    # Skill Python
    with open(LOCAL_SKILL_PY, "r", encoding="utf-8") as f:
        code = f.read()
    with sftp.file(REMOTE_SKILL_PY, "w") as remote_file:
        remote_file.write(code)
    print(f"  ✅ {REMOTE_SKILL_PY}")

    # SKILL.md
    with open(LOCAL_SKILL_MD, "r", encoding="utf-8") as f:
        skill_md = f.read()
    with sftp.file(REMOTE_SKILL_MD, "w") as remote_file:
        remote_file.write(skill_md)
    print(f"  ✅ {REMOTE_SKILL_MD}")

    # Índice de archivos (generado por cargar_carpeta_onedrive.py)
    if os.path.exists(LOCAL_INDEX_JSON):
        with open(LOCAL_INDEX_JSON, "r", encoding="utf-8") as f:
            index_data = f.read()
        with sftp.file(REMOTE_INDEX_JSON, "w") as remote_file:
            remote_file.write(index_data)
        import json
        count = len(json.loads(index_data))
        print(f"  ✅ {REMOTE_INDEX_JSON} ({count} documentos indexados)")
    else:
        print(f"  ⚠️  {LOCAL_INDEX_JSON} no existe — ejecuta cargar_carpeta_onedrive.py primero")

    sftp.close()

    # ── Configurar variable de entorno ─────────────────────────
    print("\n[4/7] Configurando GEMINI_API_KEY...")
    # Verificar si ya existe en /etc/environment
    existing = run_cmd(ssh, "grep GEMINI_API_KEY /etc/environment || true", "check /etc/environment")
    if "GEMINI_API_KEY" not in existing:
        run_cmd(ssh, 
                f'echo \'GEMINI_API_KEY={GEMINI_API_KEY}\' >> /etc/environment',
                "append to /etc/environment")
        print("  ✅ Agregada a /etc/environment")
    else:
        print("  ⚠️  Ya existe en /etc/environment, no se modifica")

    # También exportar para la sesión actual y para systemd
    run_cmd(ssh, f"export GEMINI_API_KEY={GEMINI_API_KEY}", "export actual session")

    # Agregar al override de systemd del servicio hermes-it
    systemd_override = f"""[Service]
Environment="GEMINI_API_KEY={GEMINI_API_KEY}"
"""
    run_cmd(ssh, "mkdir -p /etc/systemd/system/hermes-it.service.d", "crear systemd override dir")
    run_cmd(ssh,
            f"echo '[Service]\nEnvironment=\"GEMINI_API_KEY={GEMINI_API_KEY}\"' > /etc/systemd/system/hermes-it.service.d/gemini.conf",
            "escribir systemd override")
    run_cmd(ssh, "systemctl daemon-reload", "daemon-reload")
    print("  ✅ Variable configurada en systemd")

    # ── Instalar dependencia ───────────────────────────────────
    print("\n[5/7] Verificando google-generativeai...")
    check = run_cmd(ssh, "pip3 show google-generativeai 2>/dev/null | head -2 || true", "pip3 show")
    if "google-generativeai" not in check.lower() and "Name:" not in check:
        print("  📦 Instalando google-generativeai...")
        run_cmd(ssh, "pip3 install google-generativeai --quiet", "pip3 install")
        print("  ✅ Instalado")
    else:
        print("  ✅ Ya está instalado")

    # ── Registrar en config.yaml ───────────────────────────────
    print("\n[6/7] Registrando skill en config.yaml...")
    
    # Verificar si ya está registrado
    check_config = run_cmd(ssh, f"grep 'gemini_admin_search' {REMOTE_CONFIG} || true", "grep config")
    
    if "gemini_admin_search" not in check_config:
        # Agregar la ruta del skill a external_dirs
        # Usamos sed para insertar después de la línea de farmacia_crm_tools
        run_cmd(ssh,
                f"sed -i '/farmacia_crm_tools/a\\  - {REMOTE_SKILL_DIR}' {REMOTE_CONFIG}",
                "agregar external_dir")
        
        # Agregar el subagent profile para admin_search
        # Insertar después de la sección de farmacia_safety
        subagent_block = (
            "    admin_search:\\n"
            "      child_timeout_seconds: 120\\n"
            "      fallback_model: google/gemini-2.0-flash-001\\n"
            "      max_iterations: 5\\n"
            "      model: google/gemini-2.5-flash\\n"
            "      reasoning_effort: low\\n"
            "      skills:\\n"
            "      - gemini_admin_search\\n"
            "      subagent_auto_approve: true\\n"
            "      toolsets:\\n"
            "      - file"
        )
        run_cmd(ssh,
                f"sed -i '/farmacia_safety:/i\\{subagent_block}' {REMOTE_CONFIG}",
                "agregar subagent profile")
        
        # Actualizar el system prompt del webhook para incluir la nueva herramienta
        old_prompt_line = "Usa la herramienta"
        new_tool_instruction = (
            "- Usa la herramienta 'consultar_manual_administrativo(pregunta)' para responder "
            "dudas sobre políticas internas, procedimientos, devoluciones y normativas."
        )
        run_cmd(ssh,
                f"sed -i '/consultar_horarios/a\\        \\ {new_tool_instruction}' {REMOTE_CONFIG}",
                "actualizar system prompt")
        
        print("  ✅ config.yaml actualizado")
    else:
        print("  ⚠️  Ya está registrado en config.yaml")

    # ── Reiniciar servicio ─────────────────────────────────────
    print("\n[7/7] Reiniciando hermes-it...")
    run_cmd(ssh, "systemctl restart hermes-it", "restart")
    
    import time
    time.sleep(3)
    
    status = run_cmd(ssh, "systemctl is-active hermes-it", "check status")
    if "active" in status:
        print("  ✅ hermes-it reiniciado y activo")
    else:
        print(f"  ⚠️  Estado del servicio: {status}")
        run_cmd(ssh, "journalctl -u hermes-it --no-pager -n 20", "últimos logs")

    ssh.close()

    print("\n" + "=" * 60)
    print("✅ Deploy completado exitosamente")
    print("=" * 60)
    print()
    if not os.path.exists(LOCAL_INDEX_JSON):
        print("📋 SIGUIENTE PASO REQUERIDO:")
        print("   Ejecuta la sincronización de OneDrive primero:")
        print("   > python cargar_carpeta_onedrive.py")
        print("   Luego re-ejecuta este deploy:")
        print("   > python deploy_gemini_admin_search.py")
    else:
        print("📋 FLUJO DE ACTUALIZACIÓN FUTURA:")
        print("   1. Agrega/modifica PDFs en OneDrive:")
        print("      C:\\OneDrive\\Farmacia Americana\\Manual Farmacia\\")
        print("   2. Sincroniza con Google:")
        print("      > python cargar_carpeta_onedrive.py")
        print("   3. Despliega al servidor:")
        print("      > python deploy_gemini_admin_search.py")


if __name__ == "__main__":
    main()
