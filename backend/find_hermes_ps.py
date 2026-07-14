import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('10.147.18.204', username='root', password='Twinc3pt.2')
    
    stdin, stdout, stderr = ssh.exec_command("ps aux | grep hermes")
    out = stdout.read().decode('utf-8')
    print("--- PS AUX ---")
    print(out)
    
except Exception as e:
    print("Error:", e)
finally:
    ssh.close()
