import paramiko

def main():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    # Buscar el proceso nginx
    stdin, stdout, stderr = ssh.exec_command("ps aux | grep nginx")
    print("Nginx processes:\n", stdout.read().decode().strip())
    
    # Buscar el conf de nginx
    stdin, stdout, stderr = ssh.exec_command("grep -R 'farmaciaamericana' /etc/nginx/ 2>/dev/null")
    print("Nginx confs:\n", stdout.read().decode().strip())
    
    # Si no esta en nginx, quiza esta en docker
    stdin, stdout, stderr = ssh.exec_command("docker ps | grep nginx")
    print("Docker Nginx:\n", stdout.read().decode().strip())

    ssh.close()

if __name__ == "__main__":
    main()
