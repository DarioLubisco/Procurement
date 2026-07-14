import paramiko

def main():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    # 1. Back up current inside docker
    print("Respaldando synapse.html actual en docker...")
    ssh.exec_command("docker exec synapse-frontend cp /usr/share/nginx/html/synapse.html /usr/share/nginx/html/synapse_bak.html")
    
    # 2. Copy new file into docker
    print("Copiando synapse_v11.html al contenedor...")
    stdin, stdout, stderr = ssh.exec_command("docker cp /root/synapse_v11.html synapse-frontend:/usr/share/nginx/html/synapse.html")
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    print("Listo!")

    ssh.close()

if __name__ == "__main__":
    main()
