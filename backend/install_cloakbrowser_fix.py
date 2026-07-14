import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('10.147.18.204', username='root', password='Twinc3pt.2')
    
    print("Installing cloakbrowsermcp via python3 -m pip...")
    stdin, stdout, stderr = ssh.exec_command("/root/hermes/venv/bin/python3 -m pip install cloakbrowsermcp")
    print(stdout.read().decode('utf-8'))
    print("STDERR:", stderr.read().decode('utf-8'))
    
    print("Checking if hermes agent process is running...")
    stdin, stdout, stderr = ssh.exec_command("ps aux | grep -i hermes_agent")
    print(stdout.read().decode('utf-8'))
    
except Exception as e:
    print("Error:", e)
finally:
    ssh.close()
