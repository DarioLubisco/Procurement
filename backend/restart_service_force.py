import paramiko

def run_test():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    print("Killing...")
    ssh.exec_command('pkill -9 -f "python hermes_it_agent.py"')
    ssh.exec_command('pkill -9 -f "uvicorn"')
    
    print("Restarting...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart hermes-it")
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    print("Service restarted.")
    print("STDOUT:", out)
    print("STDERR:", err)
    ssh.close()

if __name__ == "__main__":
    run_test()
