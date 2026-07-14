import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('10.147.18.204', username='root', password='Twinc3pt.2')
    
    print("Restarting hermes docker container...")
    stdin, stdout, stderr = ssh.exec_command("docker restart hermes")
    print(stdout.read().decode('utf-8'))
    print("STDERR:", stderr.read().decode('utf-8'))
    
except Exception as e:
    print("Error:", e)
finally:
    ssh.close()
