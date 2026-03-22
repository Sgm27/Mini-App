"""
Project creation utilities.

Creates a MySQL database and copies the full_stack_template_html
template into the workspace folder.
"""

import os
import shutil
from dataclasses import dataclass

import mysql.connector

from config import cfg

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "full_stack_template_html")

EFS_MOUNT_PATH = cfg.get("efs_mount_path", "/mnt/efs")


def _get_mysql_config() -> dict:
    return {
        "host": cfg.get("mysql_host", "localhost"),
        "port": int(cfg.get("mysql_port", 3306)),
        "user": cfg.get("mysql_user", "root"),
        "password": cfg.get("mysql_password", ""),
    }


@dataclass
class ProjectInfo:
    project_name: str
    db_name: str
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str

    @property
    def project_dir(self) -> str:
        workspace = cfg.get("workspace_dir", "workspace")
        return os.path.join(BASE_DIR, workspace, self.project_name)

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "db_name": self.db_name,
            "mysql_host": self.mysql_host,
            "mysql_port": self.mysql_port,
            "mysql_user": self.mysql_user,
        }


def create_project(
    name: str,
    on_step: callable = None,
) -> ProjectInfo:
    """
    Create a new project: MySQL database + workspace folder from template.

    Args:
        name: Project name (also used as database name).
        on_step: Optional callback(step, total, message) for progress.

    Returns:
        ProjectInfo with all project details.

    Raises:
        RuntimeError on failure.
    """
    def log(step: int, total: int, msg: str):
        if on_step:
            on_step(step, total, msg)

    mysql_cfg = _get_mysql_config()
    db_name = name.replace("-", "_").replace(" ", "_")

    # 1. Create MySQL database
    log(1, 3, f"Creating MySQL database '{db_name}'...")
    try:
        conn = mysql.connector.connect(**mysql_cfg)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as e:
        raise RuntimeError(f"Failed to create MySQL database: {e}")

    # 2. Copy template to workspace
    workspace = cfg.get("workspace_dir", "workspace")
    project_dir = os.path.join(BASE_DIR, workspace, name)

    if os.path.exists(project_dir):
        raise RuntimeError(f"Directory '{project_dir}' already exists.")

    log(2, 3, f"Copying template to {workspace}/{name}/...")
    shutil.copytree(TEMPLATE_DIR, project_dir)

    # 3. Configure backend .env
    log(3, 3, "Configuring backend .env...")
    backend_env = os.path.join(project_dir, "backend", ".env")
    upload_dir = f"{EFS_MOUNT_PATH}/{name}/uploads"
    with open(backend_env, "w") as f:
        f.write(f"PROJECT_NAME={name}\n")
        f.write("VERSION=0.1.0\n")
        f.write("\n")
        f.write("API_HOST=0.0.0.0\n")
        f.write("API_PORT=2701\n")
        f.write("RELOAD=true\n")
        f.write("\n")
        f.write("# MySQL Configuration\n")
        f.write(f"MYSQL_HOST={mysql_cfg['host']}\n")
        f.write(f"MYSQL_PORT={mysql_cfg['port']}\n")
        f.write(f"MYSQL_USER={mysql_cfg['user']}\n")
        f.write(f"MYSQL_PASSWORD={mysql_cfg['password']}\n")
        f.write(f"MYSQL_DATABASE={db_name}\n")
        f.write("\n")
        f.write("# EFS Upload Configuration\n")
        f.write(f"UPLOAD_DIR={upload_dir}\n")

    return ProjectInfo(
        project_name=name,
        db_name=db_name,
        mysql_host=mysql_cfg["host"],
        mysql_port=mysql_cfg["port"],
        mysql_user=mysql_cfg["user"],
        mysql_password=mysql_cfg["password"],
    )
