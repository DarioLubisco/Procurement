import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('10.147.18.204', username='root', password='Twinc3pt.2')
    # Let's find hermes directories or services
    commands = [
        "systemctl list-units --all | grep -i hermes",
        "find / -name 'hermes' -type d 2>/dev/null | grep -v 'HermesIT'",
        "ps aux | grep -i hermes"
    ]
    for cmd in commands:
        print(f"--- {cmd} ---")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode('utf-8'))
        err = stderr.read().decode('utf-8')
        if err:
            print("STDERR:", err)
except Exception as e:
    print("Error:", e)
finally:
    ssh.close()
