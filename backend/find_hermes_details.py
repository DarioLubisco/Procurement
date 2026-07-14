import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('10.147.18.204', username='root', password='Twinc3pt.2')
    
    # Check processes
    stdin, stdout, stderr = ssh.exec_command("ps aux | grep -i hermes")
    print("--- PROCESSES ---")
    print(stdout.read().decode('utf-8'))
    
    # Read config.yaml
    stdin, stdout, stderr = ssh.exec_command("cat /root/.hermes/config.yaml")
    print("--- config.yaml ---")
    print(stdout.read().decode('utf-8'))
    
except Exception as e:
    print("Error:", e)
finally:
    ssh.close()
