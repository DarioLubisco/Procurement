import paramiko
import sys
import yaml

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect('10.147.18.204', username='root', password='Twinc3pt.2')
    
    print("Installing cloakbrowsermcp...")
    stdin, stdout, stderr = ssh.exec_command("/root/hermes/venv/bin/pip install cloakbrowsermcp")
    print(stdout.read().decode('utf-8'))
    print("STDERR:", stderr.read().decode('utf-8'))
    
    print("Updating config.yaml...")
    # read config
    stdin, stdout, stderr = ssh.exec_command("cat /root/.hermes/config.yaml")
    config_content = stdout.read().decode('utf-8')
    
    config = yaml.safe_load(config_content)
    if 'mcp_servers' not in config:
        config['mcp_servers'] = {}
        
    config['mcp_servers']['cloakbrowser'] = {
        'command': 'cloakbrowsermcp',
        'args': ['--caps', 'all'],
        'timeout': 120
    }
    
    new_config_content = yaml.dump(config, default_flow_style=False)
    
    # write back config
    sftp = ssh.open_sftp()
    with sftp.file('/root/.hermes/config.yaml', 'w') as f:
        f.write(new_config_content)
    sftp.close()
    
    print("Restarting Hermes Agent service...")
    # Find service name
    stdin, stdout, stderr = ssh.exec_command("systemctl list-units --type=service | grep -i hermes")
    services = stdout.read().decode('utf-8').strip().split('\n')
    for svc in services:
        if 'hermes' in svc.lower() and 'hermes-it' not in svc.lower():
            svc_name = svc.split()[0]
            print(f"Found service: {svc_name}, restarting...")
            ssh.exec_command(f"systemctl restart {svc_name}")
            break
    else:
        print("No hermes systemd service found, maybe kill the process?")
        ssh.exec_command("pkill -f 'hermes_agent'")
        print("Killed process, hopefully it restarts or we need to start it.")
    
    print("Done.")

except Exception as e:
    print("Error:", e)
finally:
    ssh.close()
