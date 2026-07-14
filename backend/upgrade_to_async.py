import paramiko

def upgrade_backend():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    # 1. Install httpx in venv
    print("Installing httpx...")
    ssh.exec_command('/opt/stacks/synapse-app/HermesIT/venv/bin/pip install httpx')
    
    # 2. Upload new hermes_it_agent.py
    print("Uploading new backend code...")
    sftp = ssh.open_sftp()
    sftp.put('hermes_it_agent.py', '/opt/stacks/synapse-app/HermesIT/hermes_it_agent.py')
    sftp.close()
    
    # 3. Restart service
    print("Restarting hermes-it service...")
    ssh.exec_command('systemctl restart hermes-it')
    
    ssh.close()
    print("Backend upgraded to ASYNC and restarted successfully.")

if __name__ == "__main__":
    upgrade_backend()
