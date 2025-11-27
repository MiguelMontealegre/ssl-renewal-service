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

    # 1. Stop and remove the old manual deployment container
    print("Cleaning up old manual deployment...")
    execute_command(ssh, "docker stop ssl-service || true", sudo=True)
    execute_command(ssh, "docker rm ssl-service || true", sudo=True)
    execute_command(ssh, "rm -rf /home/wgomez/last-ssl-renew", sudo=False) # Remove old manual dir

    # 2. Setup/Update Git Repository
    REPO_DIR = "/home/wgomez/ssl-renewal-service"
    REPO_URL = "https://github.com/MiguelMontealegre/ssl-renewal-service.git"
    
    print(f"Updating repository at {REPO_DIR}...")
    # Check if repo exists
    out, _, _ = execute_command(ssh, f"test -d {REPO_DIR} && echo exists || echo not_found")
    if "exists" in out:
        execute_command(ssh, f"cd {REPO_DIR} && git pull origin main")
    else:
        execute_command(ssh, f"git clone {REPO_URL} {REPO_DIR}")

    # 3. Create .env file in the repo directory (optional, if needed for production secrets)
    # Or rely on default config. Ideally secrets should be injected here or exist on server.
    
    # 4. Build and Run from the Git Repo
    print("Building Docker image from git repo...")
    execute_command(ssh, f"docker build -t ssl-service {REPO_DIR}", sudo=True)
    
    print("Running container...")
    # Ensure certs directory exists outside (or inside repo if we want, but better outside to persist)
    # Let's keep certs in a persistent user directory
    CERTS_HOST_DIR = "/home/wgomez/ssl-certs-data"
    execute_command(ssh, f"mkdir -p {CERTS_HOST_DIR}")
    
    run_cmd = (
        f"docker run -d --name ssl-service "
        f"-p 80:80 "
        f"-v {CERTS_HOST_DIR}:/etc/letsencrypt "
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

