import paramiko

def setup_systemd():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"

    remote_dir = "/opt/stacks/synapse-app/HermesIT/"
    service_file = "/etc/systemd/system/hermes-it.service"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    sftp = ssh.open_sftp()
    
    service_content = f"""[Unit]
Description=Hermes IT Agent API
After=network.target

[Service]
User=root
WorkingDirectory={remote_dir}
ExecStart=/usr/bin/python3 hermes_it_agent.py
Restart=always

[Install]
WantedBy=multi-user.target
"""
    print("Writing systemd service...")
    with sftp.file(service_file, "w") as f:
        f.write(service_content)
        
    print("Reloading systemd and starting service...")
    stdin, stdout, stderr = ssh.exec_command("systemctl daemon-reload && systemctl enable hermes-it && systemctl restart hermes-it")
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    # Check status
    stdin, stdout, stderr = ssh.exec_command("systemctl status hermes-it --no-pager")
    print(stdout.read().decode())
    
    sftp.close()
    ssh.close()
    print("Systemd setup complete.")

if __name__ == "__main__":
    setup_systemd()
