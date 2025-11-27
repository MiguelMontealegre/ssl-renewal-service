import paramiko
import os
import time

HOSTNAME = "34.73.29.221"
USERNAME = "wgomez"
PASSWORD = "ASlkjadf3908j,."
REMOTE_DIR = "/home/wgomez/last-ssl-renew"

def create_ssh_client(server, port, user, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, port, user, password)
    return client

def sftp_put_dir(sftp, local_dir, remote_dir):
    for root, dirs, files in os.walk(local_dir):
        rel_path = os.path.relpath(root, local_dir)
        remote_path = os.path.join(remote_dir, rel_path)
        
        # Create remote directory
        try:
            sftp.mkdir(remote_path)
        except IOError:
            pass # Directory probably exists

        for file in files:
            if file == "__pycache__" or file.endswith(".pyc"):
                continue
                
            local_file = os.path.join(root, file)
            remote_file = os.path.join(remote_path, file)
            print(f"Uploading {local_file} to {remote_file}...")
            sftp.put(local_file, remote_file)

def execute_command(ssh, command, sudo=False):
    print(f"Executing: {command}")
    if sudo:
        command = f"echo '{PASSWORD}' | sudo -S -p '' {command}"
    
    stdin, stdout, stderr = ssh.exec_command(command)
    
    # Wait for command to complete and capture output
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    
    if out:
        print(f"STDOUT: {out}")
    if err:
        print(f"STDERR: {err}")
        
    return out, err, stdout.channel.recv_exit_status()

def main():
    print("Connecting to server...")
    ssh = create_ssh_client(HOSTNAME, 22, USERNAME, PASSWORD)
    sftp = ssh.open_sftp()

    print(f"Creating remote directory {REMOTE_DIR}...")
    try:
        sftp.mkdir(REMOTE_DIR)
    except IOError:
        pass # Exists
    
    # Upload files
    print("Uploading files...")
    sftp.put("Dockerfile", f"{REMOTE_DIR}/Dockerfile")
    sftp.put("requirements.txt", f"{REMOTE_DIR}/requirements.txt")
    
    # Recursively upload app directory
    # First make sure app dir exists
    try:
        sftp.mkdir(f"{REMOTE_DIR}/app")
    except:
        pass
    sftp_put_dir(sftp, "app", f"{REMOTE_DIR}/app")
    
    sftp.close()
    
    # Check docker
    out, err, status = execute_command(ssh, "docker --version")
    if status != 0:
        print("Docker not found. Attempting to install...")
        # Install docker (assuming ubuntu/debian)
        cmds = [
            "apt-get update",
            "apt-get install -y docker.io",
            "systemctl start docker",
            "systemctl enable docker",
            f"usermod -aG docker {USERNAME}"
        ]
        for cmd in cmds:
            execute_command(ssh, cmd, sudo=True)
            
    # Build docker image
    print("Building Docker image...")
    # Use absolute path for build context instead of cd
    execute_command(ssh, f"docker build -t ssl-service {REMOTE_DIR}", sudo=True)
    
    # Stop existing container if running
    print("Stopping existing container...")
    execute_command(ssh, "docker stop ssl-service || true", sudo=True)
    execute_command(ssh, "docker rm ssl-service || true", sudo=True)
    
    # Run container
    # We map /etc/letsencrypt to persist certs
    # We use host networking or map port 80
    print("Running container...")
    run_cmd = (
        f"docker run -d --name ssl-service "
        f"-p 80:80 "
        f"-v {REMOTE_DIR}/certs:/etc/letsencrypt "
        f"--restart unless-stopped "
        f"ssl-service"
    )
    out, err, status = execute_command(ssh, run_cmd, sudo=True)
    
    if status == 0:
        print("Deployment successful!")
    else:
        print("Deployment failed.")
        
    ssh.close()

if __name__ == "__main__":
    main()

