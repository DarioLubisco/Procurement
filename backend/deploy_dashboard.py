"""
Deploy dashboard assets + updated caja.py to Debian production server.
Uses docker cp to inject files into the synapse-api container.
"""
import paramiko
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SERVER   = "10.147.18.204"
USER     = "root"

LOCAL_DIST    = r"C:\source\Synapse\dashboard-react\dist"
LOCAL_CAJA    = r"C:\source\Synapse\backend\routers\caja.py"
REMOTE_STATIC = "/root/synapse-api/static/dashboard"
CONTAINER     = "synapse-api"

def get_ssh():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    # Load private key from local Windows user directory
    key_path = os.path.expanduser("~/.ssh/id_ed25519")
    ssh.connect(SERVER, username=USER, key_filename=key_path)
    return ssh

def upload_dir(sftp, local_dir, remote_dir):
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        sftp.mkdir(remote_dir)
    for item in os.listdir(local_dir):
        local_path  = os.path.join(local_dir, item)
        remote_path = f"{remote_dir}/{item}"
        if os.path.isdir(local_path):
            upload_dir(sftp, local_path, remote_path)
        else:
            print(f"  UP {item}")
            sftp.put(local_path, remote_path)

def run_ssh(ssh, cmd):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return out, err, exit_code

def main():
    ssh  = get_ssh()
    sftp = ssh.open_sftp()

    # 1. Upload frontend dist to host filesystem (served by nginx or static mount)
    print(f"\n[DEPLOY] Uploading frontend dist -> {REMOTE_STATIC}")
    run_ssh(ssh, f"rm -rf {REMOTE_STATIC} && mkdir -p {REMOTE_STATIC}")
    upload_dir(sftp, LOCAL_DIST, REMOTE_STATIC)
    print("[OK] Frontend uploaded to host.")

    # Also copy into container's /app/static/dashboard if it exists
    run_ssh(ssh, f"docker exec {CONTAINER} mkdir -p /app/static/dashboard")
    run_ssh(ssh, f"docker cp {REMOTE_STATIC}/. {CONTAINER}:/app/static/dashboard/")
    print("[OK] Frontend also copied into container.")

    # 2. Upload caja.py to a temp location, then docker cp into container
    TEMP_CAJA = "/tmp/caja_deploy.py"
    print(f"\n[DEPLOY] Uploading caja.py -> container {CONTAINER}:/app/routers/caja.py")
    sftp.put(LOCAL_CAJA, TEMP_CAJA)
    out, err, code = run_ssh(ssh, f"docker cp {TEMP_CAJA} {CONTAINER}:/app/routers/caja.py")
    if code != 0:
        print(f"  ERROR: {err}")
    else:
        print("[OK] caja.py injected into container.")
    run_ssh(ssh, f"rm -f {TEMP_CAJA}")

    # 3. Restart the container to reload
    print(f"\n[DEPLOY] Restarting {CONTAINER}...")
    out, err, code = run_ssh(ssh, f"docker restart {CONTAINER}")
    print(f"  Result: {out} (exit={code})")

    sftp.close()
    ssh.close()
    print("\n[DONE] Deploy complete!")

if __name__ == "__main__":
    main()
