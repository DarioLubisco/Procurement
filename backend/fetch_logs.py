import paramiko

host = "10.147.18.204"
user = "root"
password = "Twinc3pt.2"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password)

_, stdout, _ = ssh.exec_command('journalctl -u hermes-it -n 50 --no-pager')
with open('hermes_logs.txt', 'w', encoding='utf-8') as f:
    f.write(stdout.read().decode('utf-8'))

ssh.close()
print("Logs fetched.")
