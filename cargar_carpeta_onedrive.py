"""
Sincronización OneDrive → Google AI Studio (Gemini File Search)
===============================================================
Escanea la carpeta sincronizada de OneDrive en Windows, sube todos los
archivos compatibles a Google AI Studio, y genera un índice JSON que el
skill de Hermes (gemini_admin_search.py) lee en producción.

Uso:
  python cargar_carpeta_onedrive.py              # Subir archivos nuevos/modificados
  python cargar_carpeta_onedrive.py --force       # Forzar re-subida de todo
  python cargar_carpeta_onedrive.py --list        # Listar archivos ya indexados en Google
  python cargar_carpeta_onedrive.py --cleanup     # Eliminar archivos huérfanos de Google

El JSON generado (archivos_indexados.json) se guarda junto a este script
y debe ser desplegado al servidor Debian para que Hermes lo lea.

SDK: Usa google-genai (nuevo) con fallback a google.generativeai (legacy).
"""

import os
import sys
import json
import hashlib
from datetime import datetime

# ── SDK Import (nuevo google-genai con fallback a legacy) ─────
_USE_NEW_SDK = False
try:
    from google import genai
    _USE_NEW_SDK = True
except ImportError:
    try:
        import google.generativeai as genai
    except ImportError:
        print("ERROR: Instala una de estas librerías:")
        print("  pip install google-genai          (recomendado)")
        print("  pip install google-generativeai   (legacy)")
        sys.exit(1)


# ── Configuración ─────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get(
    "GEMINI_API_KEY",
    "AIzaSyCwq1nA3hcsUbT-uZ5UcxLeq4bGeGCiO_s"
)

# Inicializar SDK
if _USE_NEW_SDK:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    genai.configure(api_key=GEMINI_API_KEY)
    client = None

# Ruta donde se guarda el índice (junto a este script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_FILE = os.path.join(SCRIPT_DIR, "archivos_indexados.json")

# Extensiones aceptadas por la Gemini File API
EXTENSIONES_VALIDAS = ('.pdf', '.txt', '.csv', '.md', '.docx')


# ── Wrappers para compatibilidad SDK nuevo/legacy ─────────────

def _upload_file(filepath: str, display_name: str):
    if _USE_NEW_SDK:
        return client.files.upload(file=filepath, config={"display_name": display_name})
    else:
        return genai.upload_file(path=filepath, display_name=display_name)

def _delete_file(file_id: str):
    if _USE_NEW_SDK:
        client.files.delete(name=file_id)
    else:
        genai.delete_file(file_id)

def _list_files():
    if _USE_NEW_SDK:
        return client.files.list()
    else:
        return genai.list_files()


# ── Detección automática de la carpeta OneDrive ───────────────

def obtener_ruta_onedrive() -> str:
    """
    Busca la carpeta de manuales. En Windows busca OneDrive.
    En Linux (Debian) usa un directorio local predeterminado.
    """
    if os.name == 'posix':
        return "/root/manuales_farmacia"

    candidatas = [
        r"C:\OneDrive\Farmacia Americana\Manual Farmacia",
        os.path.join(os.environ.get("USERPROFILE", ""),
                     "OneDrive", "Farmacia Americana", "Manual Farmacia"),
        os.path.join(os.environ.get("USERPROFILE", ""),
                     "OneDrive - Farmacia Americana", "Manual Farmacia"),
    ]

    for ruta in candidatas:
        if os.path.isdir(ruta):
            return ruta

    return candidatas[0]


# ── Utilidades ────────────────────────────────────────────────

def sha256_file(filepath: str) -> str:
    """SHA-256 del contenido del archivo para detección de cambios."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for bloque in iter(lambda: f.read(8192), b""):
            h.update(bloque)
    return h.hexdigest()


def cargar_indice_existente() -> list:
    if os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def guardar_indice(archivos: list):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(archivos, f, indent=4, ensure_ascii=False)


# ── Acciones principales ─────────────────────────────────────

def sincronizar_carpeta(force: bool = False):
    """Escanea la carpeta OneDrive y sube archivos nuevos/modificados a Google."""
    ruta = obtener_ruta_onedrive()

    if not os.path.isdir(ruta):
        print(f"❌ No se pudo localizar la carpeta de OneDrive.")
        print(f"   Ruta intentada: {ruta}")
        print("   Asegúrate de que OneDrive esté sincronizado localmente.")
        sys.exit(1)

    sdk_label = "google-genai (nuevo)" if _USE_NEW_SDK else "google-generativeai (legacy)"
    print(f"📂 Carpeta OneDrive: {ruta}")
    print(f"   SDK: {sdk_label}")
    print(f"   Extensiones válidas: {', '.join(EXTENSIONES_VALIDAS)}")
    print()

    # Cargar índice previo para idempotencia
    indice_previo = cargar_indice_existente()
    hashes_previos = {item["nombre_local"]: item.get("sha256", "") for item in indice_previo}
    ids_previos = {item["nombre_local"]: item.get("id_gemini", "") for item in indice_previo}

    archivos_nuevos = []
    archivos_saltados = 0
    archivos_actualizados = 0

    for raiz, dirs, ficheros in os.walk(ruta):
        for nombre in ficheros:
            if not nombre.lower().endswith(EXTENSIONES_VALIDAS):
                continue

            ruta_completa = os.path.join(raiz, nombre)
            ruta_relativa = os.path.relpath(ruta_completa, ruta)
            hash_actual = sha256_file(ruta_completa)

            # Idempotencia: saltar si el hash no cambió
            if not force and ruta_relativa in hashes_previos:
                if hashes_previos[ruta_relativa] == hash_actual:
                    print(f"  ⏭️  Sin cambios: {ruta_relativa}")
                    for item in indice_previo:
                        if item["nombre_local"] == ruta_relativa:
                            archivos_nuevos.append(item)
                            break
                    archivos_saltados += 1
                    continue
                else:
                    viejo_id = ids_previos.get(ruta_relativa, "")
                    if viejo_id:
                        try:
                            _delete_file(viejo_id)
                            print(f"  🗑️  Eliminado versión anterior: {viejo_id}")
                        except Exception:
                            pass
                    archivos_actualizados += 1

            # Subir a Google AI Studio
            print(f"  ⬆️  Subiendo: {ruta_relativa} ({os.path.getsize(ruta_completa):,} bytes)...")
            try:
                archivo_gemini = _upload_file(ruta_completa, ruta_relativa)
                print(f"     ✅ ID: {archivo_gemini.name}")

                archivos_nuevos.append({
                    "nombre_local": ruta_relativa,
                    "id_gemini": archivo_gemini.name,
                    "uri": getattr(archivo_gemini, 'uri', ''),
                    "sha256": hash_actual,
                    "tamaño_bytes": os.path.getsize(ruta_completa),
                    "fecha_subida": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"     ❌ Error: {e}")

    guardar_indice(archivos_nuevos)

    print()
    print("=" * 55)
    print(f"🎉 Sincronización completada")
    print(f"   Archivos subidos/actualizados: {len(archivos_nuevos) - archivos_saltados}")
    print(f"   Archivos sin cambios:          {archivos_saltados}")
    print(f"   Archivos re-subidos:           {archivos_actualizados}")
    print(f"   Total en índice:               {len(archivos_nuevos)}")
    print(f"   Índice guardado en: {INDEX_FILE}")
    print("=" * 55)
    print()
    print("📋 SIGUIENTE PASO:")
    print("   Ejecuta 'python deploy_gemini_admin_search.py' para")
    print("   desplegar el índice actualizado al servidor Hermes.")


def listar_archivos_google():
    """Lista todos los archivos actualmente en tu cuenta de Google AI Studio."""
    print("Archivos en Google AI Studio:")
    print("-" * 60)
    count = 0
    for f in _list_files():
        size = getattr(f, 'size_bytes', '?')
        state = getattr(f.state, 'name', str(f.state)) if hasattr(f, 'state') else '?'
        display = getattr(f, 'display_name', '?')
        print(f"  {f.name}")
        print(f"    Display: {display} | {size} bytes | Estado: {state}")
        count += 1
    print("-" * 60)
    print(f"Total: {count} archivos")


def cleanup_huerfanos():
    """Elimina archivos de Google que ya no están en el índice local."""
    indice = cargar_indice_existente()
    ids_locales = {item["id_gemini"] for item in indice}

    print("Buscando archivos huérfanos en Google AI Studio...")
    eliminados = 0
    for f in _list_files():
        if f.name not in ids_locales:
            try:
                _delete_file(f.name)
                display = getattr(f, 'display_name', '?')
                print(f"  🗑️  Eliminado: {f.name} ({display})")
                eliminados += 1
            except Exception as e:
                print(f"  ❌ Error eliminando {f.name}: {e}")

    print(f"\nEliminados: {eliminados} archivos huérfanos.")


if __name__ == "__main__":
    if "--list" in sys.argv:
        listar_archivos_google()
    elif "--cleanup" in sys.argv:
        cleanup_huerfanos()
    else:
        force = "--force" in sys.argv
        if os.name == 'posix':
            print("Sincronizando OneDrive con rclone...")
            os.system('rclone sync "onedrive:Farmacia Americana/Manual Farmacia" /root/manuales_farmacia')
            print("Sincronización rclone finalizada.")
        sincronizar_carpeta(force=force)
