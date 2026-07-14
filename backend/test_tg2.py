import paramiko

host = "10.147.18.204"
user = "root"
password = "Twinc3pt.2"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password)

test_script = """
import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv('/opt/stacks/synapse-app/HermesIT/.env')

async def test():
    async with httpx.AsyncClient() as c:
        u = f'https://api.telegram.org/bot{os.getenv("TELEGRAM_TOKEN")}/getUpdates'
        print("Sending request...")
        try:
            r = await c.get(u, params={"offset": 0, "timeout": 30})
            print(r.json())
        except Exception as e:
            print(f"Error: {type(e).__name__} - {e}")

if __name__ == "__main__":
    asyncio.run(test())
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/tg_test2.py', 'w') as f:
    f.write(test_script)
sftp.close()

_, stdout, _ = ssh.exec_command('/opt/stacks/synapse-app/HermesIT/venv/bin/python /tmp/tg_test2.py')
print(stdout.read().decode('utf-8'))

ssh.close()
