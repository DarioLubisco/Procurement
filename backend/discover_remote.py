"""
Quick targeted discovery of synapse paths on the Debian server.
"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("10.147.18.204", username="root", password="Twinc3pt.2")

cmds = [
    "docker ps --format '{{.Names}} {{.Image}}' 2>/dev/null",
    "ls -la /root/synapse-api/ 2>/dev/null || echo '/root/synapse-api NOT FOUND'",
    "ls -la /opt/stacks/synapse-app/ 2>/dev/null || echo '/opt/stacks/synapse-app NOT FOUND'",
    "docker exec synapse-api ls /app/routers/ 2>/dev/null || echo 'synapse-api container not found or no /app/routers'",
    "docker exec synapse-api ls /app/ 2>/dev/null || echo 'synapse-api /app/ not found'",
    "ls -la /root/ 2>/dev/null | head -20",
]

for cmd in cmds:
    print(f"\n>>> {cmd}")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=10)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print(out)
    if err: print(f"  STDERR: {err}")

ssh.close()
