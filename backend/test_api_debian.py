import paramiko

def run_test():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    # Send a request locally to the backend
    script = """
import requests
import json

url = 'http://localhost:8001/chat'
data = {'message': 'Ejecuta el comando: sudo docker ps', 'session_id': 'test1', 'channel': 'it'}
headers = {'Content-Type': 'application/json'}

try:
    resp = requests.post(url, json=data)
    print(resp.json())
except Exception as e:
    print('Error:', e)
"""
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/test_api.py', 'w') as f:
        f.write(script)
    sftp.close()
    
    stdin, stdout, stderr = ssh.exec_command("python3 /tmp/test_api.py")
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    print("STDOUT:\n", out)
    print("STDERR:\n", err)
    ssh.close()

if __name__ == "__main__":
    run_test()
