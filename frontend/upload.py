import paramiko
import sys

def main():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"
    local_path = r"c:\source\Synapse\frontend\synapse_v11.html"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("Conectando SSH...")
        ssh.connect(host, username=user, password=password)
        
        # Subir archivo al home de root temporalmente
        print("Subiendo archivo via SFTP...")
        sftp = ssh.open_sftp()
        sftp.put(local_path, "/root/synapse_v11.html")
        sftp.close()
        
        print("Buscando configuracion NGINX para synapse.farmaciaamericana.es...")
        stdin, stdout, stderr = ssh.exec_command("grep -R 'synapse.farmaciaamericana.es' /etc/nginx/sites-enabled/ 2>/dev/null")
        nginx_conf = stdout.read().decode().strip()
        print("Nginx Conf:", nginx_conf)
        
        # Intentar adivinar el document root
        stdin, stdout, stderr = ssh.exec_command("find /var/www -name 'synapse.html' 2>/dev/null")
        paths = stdout.read().decode().strip()
        if paths:
            print(f"Encontrado synapse.html en: {paths}")
            target_path = paths.split('\n')[0] # Tomar el primero
            
            print(f"Copiando /root/synapse_v11.html a {target_path}...")
            # Respaldar original
            ssh.exec_command(f"cp {target_path} {target_path}.bak")
            # Mover nuevo
            ssh.exec_command(f"cp /root/synapse_v11.html {target_path}")
            print("Copia completada!")
        else:
            print("No se encontro synapse.html en /var/www. El archivo esta en /root/synapse_v11.html listo para mover.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
