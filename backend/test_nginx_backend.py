import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.147.18.204', username='root', password='Twinc3pt.2')

cmd = 'docker exec synapse-frontend curl -s -X POST http://10.147.18.204:8001/chat -H "Content-Type: application/json" -d \'{"message":"/status_flota","session_id":"123","target":"it_agent"}\''
_, stdout, _ = ssh.exec_command(cmd)
print(stdout.read().decode('utf-8'))
ssh.close()
