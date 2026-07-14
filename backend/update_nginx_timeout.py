import paramiko

def update_nginx():
    host = "10.147.18.204"
    user = "root"
    password = "Twinc3pt.2"
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=password)
    
    nginx_conf = """server {
    listen 80;
    server_name amc.caja amc.cuentaspagar amc.cuentasporpagar amc.pedidos amc.dashboard synapse.amc amc.synapse localhost;
    client_max_body_size 50M;

    # Servir Frontend
    location / {
        root   /usr/share/nginx/html;
        index  index.html index.htm;
        try_files $uri $uri/ =404;
    }

    # Proxy a Hermes/IT Agent (Python)
    location /api/hermes/ {
        proxy_pass http://10.147.18.204:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Aumentar timeouts para HITL (Human-In-The-Loop)
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }

    location /api/ {
        proxy_pass http://synapse-api:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Proxy para el módulo de Caja
    location /caja/ {
        proxy_pass http://synapse-api:8000/caja/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
"""
    # Write to a temp file on server
    sftp = ssh.open_sftp()
    with sftp.file('/tmp/default.conf', 'w') as f:
        f.write(nginx_conf)
    sftp.close()
    
    # Move and restart nginx container
    # Assuming nginx is running in a docker container named 'synapse-frontend' or similar
    # In the previous logs I saw /opt/stacks/synapse-app/Synapse/nginx/default.conf
    # This is likely a bind mount.
    
    ssh.exec_command('cp /tmp/default.conf /opt/stacks/synapse-app/Synapse/nginx/default.conf')
    
    # Identify nginx container and reload/restart
    stdin, stdout, stderr = ssh.exec_command('docker ps --filter "name=synapse-frontend" --format "{{.Names}}"')
    container_name = stdout.read().decode('utf-8').strip()
    if not container_name:
        # Try generic nginx
        stdin, stdout, stderr = ssh.exec_command('docker ps --filter "ancestor=nginx" --format "{{.Names}}"')
        container_name = stdout.read().decode('utf-8').strip()
    
    if container_name:
        print(f"Reloading NGINX in container: {container_name}")
        ssh.exec_command(f'docker exec {container_name} nginx -s reload')
    else:
        print("NGINX container not found, trying systemctl if it is host-based")
        ssh.exec_command('systemctl reload nginx')

    ssh.close()
    print("NGINX configuration updated with 300s timeout.")

if __name__ == "__main__":
    update_nginx()
