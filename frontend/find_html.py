import paramiko

def main():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=user, password=password)
        
        # Primero buscar globalmente (omitiendo errores)
        stdin, stdout, stderr = ssh.exec_command("find / -name 'synapse.html' 2>/dev/null | head -n 5")
        paths = stdout.read().decode().strip()
        print("Búsqueda global (find / -name 'synapse.html'):\n", paths)

        # Buscar configuraciones de NGINX
        stdin, stdout, stderr = ssh.exec_command("grep -R 'synapse.farmaciaamericana.es' /etc/nginx/ 2>/dev/null")
        nginx_conf = stdout.read().decode().strip()
        print("\nConfiguración NGINX (grep 'synapse.farmaciaamericana.es'):\n", nginx_conf)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
