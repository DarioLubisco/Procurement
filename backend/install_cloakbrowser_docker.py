import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('10.147.18.204', username='root', password='Twinc3pt.2')
    
    print("Installing in docker...")
    stdin, stdout, stderr = ssh.exec_command("docker exec hermes /opt/hermes/.venv/bin/pip install cloakbrowsermcp")
    print(stdout.read().decode('utf-8'))
    print("STDERR:", stderr.read().decode('utf-8'))
    
    print("Restarting hermes docker container...")
    stdin, stdout, stderr = ssh.exec_command("docker restart hermes")
    print(stdout.read().decode('utf-8'))
    
    print("Checking config.yaml...")
    stdin, stdout, stderr = ssh.exec_command("cat /root/.hermes/config.yaml | grep -A 5 cloakbrowser")
    print(stdout.read().decode('utf-8'))

except Exception as e:
    print("Error:", e)
finally:
    ssh.close()
