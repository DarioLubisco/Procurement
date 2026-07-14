import paramiko

def main():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    # Inspect docker container synapse-frontend
    stdin, stdout, stderr = ssh.exec_command("docker inspect synapse-frontend | grep -A 30 'Mounts'")
    print("Mounts:\n", stdout.read().decode().strip())

    ssh.close()

if __name__ == "__main__":
    main()
