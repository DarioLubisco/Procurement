import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.147.18.204', username='root', password='Twinc3pt.2')

with open(r'c:\source\Synapse\backend\hermes_it_agent.py', 'r', encoding='utf-8') as f:
    script = f.read()

sftp = ssh.open_sftp()
with sftp.file('/opt/stacks/synapse-app/HermesIT/hermes_it_agent.py', 'w') as f:
    f.write(script)
sftp.close()

_, stdout, stderr = ssh.exec_command('systemctl restart hermes-it.service')
print("Restarted hermes-it.service")
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())
ssh.close()
