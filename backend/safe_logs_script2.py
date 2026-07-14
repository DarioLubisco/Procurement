import paramiko

def get_more_logs():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    stdin, stdout, stderr = ssh.exec_command("journalctl -u hermes-it -n 100 --no-pager")
    logs = stdout.read().decode('utf-8', 'replace')
    
    with open("safe_logs2.txt", "w", encoding="utf-8") as f:
        f.write(logs)
        
    ssh.close()

if __name__ == "__main__":
    get_more_logs()
