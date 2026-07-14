import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('10.147.18.204', username='root', password='Twinc3pt.2')
    commands = [
        "ps aux | grep -i hermes",
        "ls -la /root/.hermes",
        "ls -la /opt/stacks/synapse-app/HermesIT/",
        "find /opt -name 'hermes' -type d 2>/dev/null",
        "systemctl list-units --type=service | grep -i hermes"
    ]
    for cmd in commands:
        print(f"--- {cmd} ---")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
finally:
    ssh.close()
