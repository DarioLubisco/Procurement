import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('10.147.18.204', username='root', password='Twinc3pt.2')

cmd = '''
cat << 'EOF' > /tmp/tg_test3.py
import asyncio, httpx
async def test():
    async with httpx.AsyncClient() as c:
        u = 'https://api.telegram.org/bot8795593743:AAEebBKpsAlITvv72Fb8BaQNbfwPdVjP-3s/getUpdates'
        try:
            r = await c.get(u, params={"offset": 0, "timeout": 5})
            print(r.json())
        except Exception as e:
            print(e)
asyncio.run(test())
EOF
/opt/stacks/synapse-app/HermesIT/venv/bin/python /tmp/tg_test3.py
'''

_, stdout, _ = ssh.exec_command(cmd)
print(stdout.read().decode('utf-8'))
ssh.close()
