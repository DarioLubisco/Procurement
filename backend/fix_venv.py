import paramiko

def fix_venv():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"

    remote_dir = "/opt/stacks/synapse-app/HermesIT/"
    service_file = "/etc/systemd/system/hermes-it.service"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    # Create venv and install
    print("Creating venv and installing packages...")
    stdin, stdout, stderr = ssh.exec_command(f"cd {remote_dir} && python3 -m venv venv && ./venv/bin/pip install fastapi uvicorn openai python-dotenv pydantic requests")
    print(stdout.read().decode())
    
    # Update systemd
    sftp = ssh.open_sftp()
    service_content = f"""[Unit]
Description=Hermes IT Agent API
After=network.target

[Service]
User=root
WorkingDirectory={remote_dir}
ExecStart={remote_dir}venv/bin/python hermes_it_agent.py
Restart=always

[Install]
WantedBy=multi-user.target
"""
    with sftp.file(service_file, "w") as f:
        f.write(service_content)
        
    print("Restarting service...")
    ssh.exec_command("systemctl daemon-reload && systemctl restart hermes-it")
    
    ssh.close()

if __name__ == "__main__":
    fix_venv()
