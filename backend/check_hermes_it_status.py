import paramiko

def run_test():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    print("--- STATUS ---")
    stdin, stdout, stderr = ssh.exec_command("systemctl status hermes-it.service")
    print(stdout.read().decode('utf-8', errors='ignore'))
    
    print("--- LOGS ---")
    stdin, stdout, stderr = ssh.exec_command("journalctl -u hermes-it.service -n 20 --no-pager")
    print(stdout.read().decode('utf-8', errors='ignore'))
    ssh.close()

if __name__ == "__main__":
    run_test()
