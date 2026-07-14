import paramiko
import os

def update_remote():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"

    local_html = "synapse_v11.html"
    remote_html_dir = "/opt/stacks/synapse-app/Synapse/frontend/"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    sftp = ssh.open_sftp()
    
    # 1. Update synapse.html
    print("Uploading updated UI...")
    sftp.put(local_html, remote_html_dir + "synapse.html")
    print("UI updated.")
    
    # 2. Update default.conf
    nginx_conf_path = "/opt/stacks/synapse-app/Synapse/nginx/default.conf"
    
    stdin, stdout, stderr = ssh.exec_command(f"cat {nginx_conf_path}")
    conf_content = stdout.read().decode()
    
    if "location /api/hermes/" not in conf_content:
        print("Adding /api/hermes/ block to NGINX conf...")
        # Insert before location /api/
        new_block = """
    # Proxy a Hermes/IT Agent (Python)
    location /api/hermes/ {
        proxy_pass http://10.147.18.204:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
"""
        conf_content = conf_content.replace("location /api/ {", new_block + "\n    location /api/ {")
        
        with sftp.file(nginx_conf_path, "w") as f:
            f.write(conf_content)
        print("NGINX conf updated.")
    else:
        print("NGINX conf already has /api/hermes/.")
        
    sftp.close()
    
    # 3. Reload NGINX in docker
    print("Restarting synapse-frontend container...")
    stdin, stdout, stderr = ssh.exec_command("docker restart synapse-frontend")
    print(stdout.read().decode())
    print(stderr.read().decode())
    
    ssh.close()
    print("Done!")

if __name__ == "__main__":
    update_remote()
