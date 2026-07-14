import paramiko
import os

def install_backend():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"

    local_backend = "c:\\source\\Synapse\\backend\\hermes_it_agent.py"
    remote_dir = "/opt/stacks/synapse-app/HermesIT/"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    sftp = ssh.open_sftp()
    
    stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
    stdout.read() # block
    
    print("Uploading backend script...")
    sftp.put(local_backend, remote_dir + "hermes_it_agent.py")
    
    # Also we need requirements: fastapi, uvicorn, openai
    print("Installing requirements on Debian...")
    stdin, stdout, stderr = ssh.exec_command("pip install fastapi uvicorn openai python-dotenv")
    print(stdout.read().decode())
    
    # Start with PM2
    print("Starting backend with PM2...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {remote_dir} && pm2 start hermes_it_agent.py --interpreter python3 --name hermes_it_agent")
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    ssh.exec_command("pm2 save")
    
    sftp.close()
    ssh.close()
    print("Backend installed and started!")

if __name__ == "__main__":
    install_backend()
