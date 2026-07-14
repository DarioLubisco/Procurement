import paramiko

def run_test():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    stdin, stdout, stderr = ssh.exec_command("cat /etc/systemd/system/hermes-it.service")
    out = stdout.read().decode('utf-8')
    print("Service file:\n", out)
    ssh.close()

if __name__ == "__main__":
    run_test()
