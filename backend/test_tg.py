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
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    print(f"Token: {bool(token)}, Chat: {bool(chat_id)}")
    
    async with httpx.AsyncClient() as c:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": "Prueba ASYNC desde Debian"}
        r = await c.post(url, json=payload)
        print(r.json())

if __name__ == "__main__":
    asyncio.run(test())
"""

sftp = ssh.open_sftp()
with sftp.file('/tmp/test_tg.py', 'w') as f:
    f.write(test_script)
sftp.close()

_, stdout, _ = ssh.exec_command('/opt/stacks/synapse-app/HermesIT/venv/bin/python /tmp/test_tg.py')
print(stdout.read().decode('utf-8'))

ssh.close()
