import paramiko

def check_env():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    stdin, stdout, stderr = ssh.exec_command("cat /opt/stacks/synapse-app/.env")
    print("App env:", stdout.read().decode('utf-8', 'ignore'))
    
    ssh.close()

if __name__ == "__main__":
    check_env()
