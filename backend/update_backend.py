import paramiko

def update_backend():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"

    local_backend = "c:\\source\\Synapse\\backend\\hermes_it_agent.py"
    remote_dir = "/opt/stacks/synapse-app/HermesIT/"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    sftp = ssh.open_sftp()
    
    print("Uploading backend script...")
    sftp.put(local_backend, remote_dir + "hermes_it_agent.py")
    
    print("Restarting service...")
    ssh.exec_command("systemctl restart hermes-it")
    
    sftp.close()
    ssh.close()
    print("Backend updated and restarted!")

if __name__ == "__main__":
    update_backend()
