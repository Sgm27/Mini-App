"""
Project creation utilities.

Creates a MySQL database, an S3 bucket, and copies the full_stack_template_html
template into the workspace folder.
"""

import json
import os
import re
import shutil
from dataclasses import dataclass

import boto3
import mysql.connector
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "full_stack_template_html")


REGION = "ap-southeast-1"


def _get_mysql_config() -> dict:
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
    }


def _get_account_id() -> str:
    """Get AWS account ID for unique bucket naming."""
    session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=REGION,
    )
    sts = session.client("sts")
    return sts.get_caller_identity()["Account"]


def _to_s3_bucket_name(name: str, account_id: str) -> str:
    """Convert project name to a globally unique S3 bucket name."""
    # Lowercase, replace underscores/spaces with hyphens
    bucket = name.lower().replace("_", "-").replace(" ", "-")
    # Remove invalid characters (only lowercase, numbers, hyphens allowed)
    bucket = re.sub(r"[^a-z0-9\-]", "", bucket)
    # Collapse consecutive hyphens
    bucket = re.sub(r"-+", "-", bucket)
    # Strip leading/trailing hyphens
    bucket = bucket.strip("-")
    # Append account ID for global uniqueness
    bucket = f"{bucket}-{account_id}"
    # S3 bucket names must be 3-63 characters
    if len(bucket) > 63:
        bucket = bucket[:63].rstrip("-")
    return bucket


def _create_s3_bucket(bucket_name: str) -> str:
    """Create an S3 bucket with public read access. Returns the bucket name."""
    session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=REGION,
    )
    
    s3 = session.client(
        "s3",
        region_name=REGION,
        endpoint_url=f"https://s3.{REGION}.amazonaws.com",
    )

    # Create bucket if it doesn't exist
    bucket_exists = False
    try:
        s3.head_bucket(Bucket=bucket_name)
        bucket_exists = True
    except ClientError:
        pass

    if not bucket_exists:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )

    # Disable "Block Public Access" so bucket policy can allow public reads
    s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )

    # Set bucket policy to allow public read on all objects
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
            }
        ],
    }
    s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))

    # Set CORS configuration to allow browser uploads (presigned URL PUT)
    cors_config = {
        "CORSRules": [
            {
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["GET", "PUT", "POST"],
                "AllowedOrigins": ["*"],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": 3600,
            }
        ]
    }
    s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_config)

    return bucket_name


@dataclass
class ProjectInfo:
    project_name: str
    db_name: str
    s3_bucket_name: str
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str

    @property
    def project_dir(self) -> str:
        workspace = os.getenv("WORKSPACE_DIR", "workspace")
        return os.path.join(BASE_DIR, workspace, self.project_name)

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "db_name": self.db_name,
            "s3_bucket_name": self.s3_bucket_name,
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

    account_id = _get_account_id()
    s3_bucket_name = _to_s3_bucket_name(name, account_id)

    # 1. Create MySQL database
    log(1, 4, f"Creating MySQL database '{db_name}'...")
    try:
        conn = mysql.connector.connect(**mysql_cfg)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        cursor.close()
        conn.close()
    except mysql.connector.Error as e:
        raise RuntimeError(f"Failed to create MySQL database: {e}")

    # 2. Create S3 bucket
    log(2, 4, f"Creating S3 bucket '{s3_bucket_name}'...")
    try:
        _create_s3_bucket(s3_bucket_name)
    except Exception as e:
        raise RuntimeError(f"Failed to create S3 bucket: {e}")

    # 3. Copy template to workspace
    workspace = os.getenv("WORKSPACE_DIR", "workspace")
    project_dir = os.path.join(BASE_DIR, workspace, name)

    if os.path.exists(project_dir):
        raise RuntimeError(f"Directory '{project_dir}' already exists.")

    log(3, 4, f"Copying template to {workspace}/{name}/...")
    shutil.copytree(TEMPLATE_DIR, project_dir)

    # 4. Configure backend .env
    log(4, 4, "Configuring backend .env...")
    backend_env = os.path.join(project_dir, "backend", ".env")
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
        f.write("# S3 Configuration\n")
        f.write(f"S3_BUCKET_NAME={s3_bucket_name}\n")
        f.write(f"S3_REGION={REGION}\n")

    return ProjectInfo(
        project_name=name,
        db_name=db_name,
        s3_bucket_name=s3_bucket_name,
        mysql_host=mysql_cfg["host"],
        mysql_port=mysql_cfg["port"],
        mysql_user=mysql_cfg["user"],
        mysql_password=mysql_cfg["password"],
    )
