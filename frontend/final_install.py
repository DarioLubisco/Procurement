import paramiko

def main():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    # 1. Back up current
    print("Respaldando synapse.html actual en el host...")
    ssh.exec_command("cp /opt/stacks/synapse-app/Synapse/frontend/synapse.html /opt/stacks/synapse-app/Synapse/frontend/synapse_bak.html")
    
    # 2. Copy new file
    print("Moviendo synapse_v11.html...")
    stdin, stdout, stderr = ssh.exec_command("cp /root/synapse_v11.html /opt/stacks/synapse-app/Synapse/frontend/synapse.html")
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("Error:", err)
    
    # 3. Dar permisos
    ssh.exec_command("chmod 644 /opt/stacks/synapse-app/Synapse/frontend/synapse.html")
    
    print("Listo! Ya esta actualizado en producción.")

    ssh.close()

if __name__ == "__main__":
    main()
