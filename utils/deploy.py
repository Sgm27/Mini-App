"""
Deploy a React SPA project to VPS with a random subdomain using paramiko.

Usage:
    from utils import deploy_project
    info = deploy_project("/path/to/project")
    print(info.url)
"""

import json
import os
import random
import stat
import string
import subprocess
from dataclasses import dataclass
from typing import Callable, Optional

import paramiko

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "vps-config", "config.json")
PEM_FILE = os.path.join(BASE_DIR, "vps-config", "sonktx.pem")
DOMAIN = "sonktx.online"


def _load_vps_config() -> dict:
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def _generate_subdomain(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def _get_ssh_client() -> paramiko.SSHClient:
    config = _load_vps_config()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=config["host"],
        port=config["port"],
        username=config["username"],
        key_filename=PEM_FILE,
    )
    return client


def _ssh_exec(client: paramiko.SSHClient, command: str) -> str:
    _, stdout, stderr = client.exec_command(command)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code != 0:
        err = stderr.read().decode().strip()
        raise RuntimeError(f"SSH command failed (exit {exit_code}): {err}")
    return stdout.read().decode().strip()


def _upload_dir(sftp: paramiko.SFTPClient, local_dir: str, remote_dir: str):
    """Recursively upload a local directory to the remote server."""
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        remote_path = f"{remote_dir}/{item}"

        if os.path.isdir(local_path):
            try:
                sftp.stat(remote_path)
            except FileNotFoundError:
                sftp.mkdir(remote_path)
            _upload_dir(sftp, local_path, remote_path)
        else:
            sftp.put(local_path, remote_path)


def _clean_remote_dir(sftp: paramiko.SFTPClient, remote_dir: str):
    """Remove all files/dirs inside remote_dir (like rsync --delete)."""
    try:
        items = sftp.listdir_attr(remote_dir)
    except FileNotFoundError:
        return

    for item in items:
        remote_path = f"{remote_dir}/{item.filename}"
        if stat.S_ISDIR(item.st_mode):
            _clean_remote_dir(sftp, remote_path)
            sftp.rmdir(remote_path)
        else:
            sftp.remove(remote_path)


@dataclass
class DeployInfo:
    project_name: str
    subdomain: str
    url: str
    vps_path: str

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "subdomain": self.subdomain,
            "url": self.url,
            "vps_path": self.vps_path,
        }


def deploy_project(
    project_dir: str,
    subdomain: str | None = None,
    on_step: Optional[Callable[[int, int, str], None]] = None,
) -> DeployInfo:
    """
    Build and deploy a React SPA project to VPS.

    Args:
        project_dir: Absolute path to the project directory.
        subdomain: Optional subdomain (random 6 chars if not provided).
        on_step: Optional callback(step, total, message) for progress.

    Returns:
        DeployInfo with URL and deployment details.
    """
    def log(step: int, total: int, msg: str):
        if on_step:
            on_step(step, total, msg)

    project_name = os.path.basename(project_dir)

    if not subdomain:
        subdomain = _generate_subdomain()

    full_domain = f"{subdomain}.{DOMAIN}"
    vps_path = f"/var/www/{subdomain}"

    # 1. Build project
    log(1, 4, f"Building project '{project_name}'...")
    result = subprocess.run(
        ["npm", "install", "--silent"],
        capture_output=True, text=True, cwd=project_dir,
    )
    if result.returncode != 0:
        raise RuntimeError(f"npm install failed: {result.stderr.strip()}")

    result = subprocess.run(
        ["npm", "run", "build"],
        capture_output=True, text=True, cwd=project_dir,
    )
    if result.returncode != 0:
        raise RuntimeError(f"npm run build failed: {result.stderr.strip()}")

    dist_dir = os.path.join(project_dir, "dist")
    if not os.path.isdir(dist_dir):
        raise RuntimeError(f"Build failed: dist/ not found at {dist_dir}")

    # 2. Upload dist/ to VPS via SFTP
    log(2, 4, f"Uploading dist/ to VPS ({vps_path})...")
    client = _get_ssh_client()
    try:
        sftp = client.open_sftp()

        # Create remote dir
        _ssh_exec(client, f"mkdir -p {vps_path}")

        # Clean old files and upload new ones
        _clean_remote_dir(sftp, vps_path)
        _upload_dir(sftp, dist_dir, vps_path)
        sftp.close()

        # 3. Create Nginx config
        log(3, 4, f"Creating Nginx config for {full_domain}...")
        nginx_config = (
            "server {\\n"
            "    listen 80;\\n"
            f"    server_name {full_domain};\\n"
            "\\n"
            f"    root {vps_path};\\n"
            "    index index.html;\\n"
            "\\n"
            "    location / {\\n"
            "        try_files \\$uri \\$uri/ /index.html;\\n"
            "    }\\n"
            "\\n"
            '    location ~* \\\\.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {\\n'
            "        expires 1y;\\n"
            '        add_header Cache-Control \\"public, immutable\\";\\n'
            "    }\\n"
            "}"
        )

        _ssh_exec(
            client,
            f'echo -e "{nginx_config}" | sudo tee /etc/nginx/sites-available/{subdomain} > /dev/null '
            f"&& sudo ln -sf /etc/nginx/sites-available/{subdomain} /etc/nginx/sites-enabled/",
        )

        # 4. Reload Nginx
        log(4, 4, "Reloading Nginx...")
        _ssh_exec(client, "sudo nginx -t && sudo systemctl reload nginx")

    finally:
        client.close()

    return DeployInfo(
        project_name=project_name,
        subdomain=subdomain,
        url=f"https://{full_domain}",
        vps_path=vps_path,
    )
