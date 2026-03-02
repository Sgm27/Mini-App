"""
Deploy a FastAPI backend to AWS Lambda using Docker container image.

Flow:
  1. Create/get IAM role
  2. Create ECR repository (if needed)
  3. Build Docker image
  4. Push image to ECR
  5. Create/update Lambda function from container image
  6. Create Function URL (public)

Usage:
    from utils import deploy_project
    info = deploy_project("/path/to/project")
    print(info.function_url)
"""

import base64
import json
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Optional

import boto3
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGION = "ap-southeast-1"
ROLE_NAME = "lambda-basic-execution-role"

TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}


def _get_session() -> boto3.Session:
    return boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=REGION,
    )


def _get_or_create_role(session: boto3.Session) -> str:
    iam = session.client("iam")

    REQUIRED_POLICIES = [
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        "arn:aws:iam::aws:policy/AmazonS3FullAccess",
    ]

    try:
        resp = iam.get_role(RoleName=ROLE_NAME)
        role_arn = resp["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        resp = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(TRUST_POLICY),
            Description="Basic execution role for Lambda functions",
        )
        role_arn = resp["Role"]["Arn"]
        time.sleep(10)

    # Always ensure required policies are attached
    attached = {
        p["PolicyArn"]
        for p in iam.list_attached_role_policies(RoleName=ROLE_NAME)["AttachedPolicies"]
    }
    for policy_arn in REQUIRED_POLICIES:
        if policy_arn not in attached:
            iam.attach_role_policy(RoleName=ROLE_NAME, PolicyArn=policy_arn)

    return role_arn


def _get_or_create_ecr_repo(session: boto3.Session, repo_name: str) -> str:
    ecr = session.client("ecr")
    try:
        resp = ecr.describe_repositories(repositoryNames=[repo_name])
        return resp["repositories"][0]["repositoryUri"]
    except ecr.exceptions.RepositoryNotFoundException:
        pass

    resp = ecr.create_repository(
        repositoryName=repo_name,
        imageScanningConfiguration={"scanOnPush": False},
        imageTagMutability="MUTABLE",
    )
    return resp["repository"]["repositoryUri"]


DOCKERFILE_CONTENT = """\
FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

COPY app/ ${LAMBDA_TASK_ROOT}/app/
COPY handler.py ${LAMBDA_TASK_ROOT}/

CMD ["handler.lambda_handler"]
"""

HANDLER_CONTENT = """\
from mangum import Mangum
from app.main import app

lambda_handler = Mangum(app, lifespan="off")
"""


def _ensure_lambda_files(backend_dir: str):
    """Create Dockerfile and handler.py in backend_dir if they don't exist."""
    dockerfile_path = os.path.join(backend_dir, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        with open(dockerfile_path, "w") as f:
            f.write(DOCKERFILE_CONTENT)

    handler_path = os.path.join(backend_dir, "handler.py")
    if not os.path.exists(handler_path):
        with open(handler_path, "w") as f:
            f.write(HANDLER_CONTENT)


def _docker_login_ecr(session: boto3.Session) -> str:
    ecr = session.client("ecr")
    token_resp = ecr.get_authorization_token()
    auth = token_resp["authorizationData"][0]
    registry = auth["proxyEndpoint"]

    decoded = base64.b64decode(auth["authorizationToken"]).decode()
    username, password = decoded.split(":", 1)

    proc = subprocess.run(
        ["docker", "login", "--username", username, "--password-stdin", registry],
        input=password,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Docker login failed: {proc.stderr}")
    return registry


def _build_and_push_image(backend_dir: str, repo_uri: str, tag: str = "latest") -> str:
    image_uri = f"{repo_uri}:{tag}"

    proc = subprocess.run(
        ["docker", "build", "--platform", "linux/amd64", "--provenance=false", "-t", image_uri, "."],
        cwd=backend_dir,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Docker build failed: {proc.stderr}")

    proc = subprocess.run(
        ["docker", "push", image_uri],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Docker push failed: {proc.stderr}")

    return image_uri


def _read_backend_env(backend_dir: str) -> dict[str, str]:
    env_path = os.path.join(backend_dir, ".env")
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip()
    return env_vars


@dataclass
class DeployInfo:
    project_name: str
    function_name: str
    function_url: str
    region: str

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "function_name": self.function_name,
            "function_url": self.function_url,
            "region": self.region,
        }


def deploy_project(
    project_dir: str,
    function_name: str | None = None,
    on_step: Optional[Callable[[int, int, str], None]] = None,
) -> DeployInfo:
    """
    Deploy the FastAPI backend to AWS Lambda using Docker container image.

    Args:
        project_dir: Path to the project directory (used for project name).
        function_name: Lambda function name (defaults to project directory name).
        on_step: Optional callback(step, total, message) for progress.

    Returns:
        DeployInfo with Function URL and deployment details.
    """
    def log(step: int, total: int, msg: str):
        if on_step:
            on_step(step, total, msg)

    project_name = os.path.basename(project_dir)
    if not function_name:
        function_name = project_name

    backend_dir = os.path.join(project_dir, "backend")
    if not os.path.isdir(backend_dir):
        raise RuntimeError(f"Backend directory not found: {backend_dir}")

    # 0. Ensure Dockerfile and handler.py exist
    log(1, 7, "Ensuring Dockerfile and handler.py exist...")
    _ensure_lambda_files(backend_dir)

    session = _get_session()

    # 1. IAM Role
    log(2, 7, "Getting/creating IAM role...")
    role_arn = _get_or_create_role(session)

    # 2. ECR Repository
    log(3, 7, f"Getting/creating ECR repository '{function_name}'...")
    repo_uri = _get_or_create_ecr_repo(session, function_name)

    # 3. Docker login
    log(4, 7, "Logging in to ECR...")
    _docker_login_ecr(session)

    # 4. Build & push image
    log(5, 7, "Building and pushing Docker image...")
    image_uri = _build_and_push_image(backend_dir, repo_uri)

    # 5. Environment variables from backend .env
    env_vars = _read_backend_env(backend_dir)

    # 6. Create/update Lambda function
    log(6, 7, "Creating/updating Lambda function...")
    client = session.client("lambda")
    function_url = None

    try:
        # Function already exists → update
        client.get_function(FunctionName=function_name)

        client.update_function_code(
            FunctionName=function_name,
            ImageUri=image_uri,
        )
        waiter = client.get_waiter("function_updated_v2")
        waiter.wait(FunctionName=function_name)

        client.update_function_configuration(
            FunctionName=function_name,
            Environment={"Variables": env_vars},
            Timeout=30,
            MemorySize=256,
        )
        waiter.wait(FunctionName=function_name)

        # Get or create Function URL
        try:
            url_resp = client.get_function_url_config(FunctionName=function_name)
            function_url = url_resp["FunctionUrl"]
        except client.exceptions.ResourceNotFoundException:
            url_resp = client.create_function_url_config(
                FunctionName=function_name,
                AuthType="NONE",
            )
            function_url = url_resp["FunctionUrl"]

    except client.exceptions.ResourceNotFoundException:
        # Create new function
        for attempt in range(6):
            try:
                client.create_function(
                    FunctionName=function_name,
                    Role=role_arn,
                    Code={"ImageUri": image_uri},
                    PackageType="Image",
                    Timeout=30,
                    MemorySize=256,
                    Environment={"Variables": env_vars},
                )
                break
            except client.exceptions.InvalidParameterValueException as e:
                if "cannot be assumed by Lambda" in str(e) and attempt < 5:
                    time.sleep(5)
                else:
                    raise

        waiter = client.get_waiter("function_active_v2")
        waiter.wait(FunctionName=function_name)

        url_resp = client.create_function_url_config(
            FunctionName=function_name,
            AuthType="NONE",
        )
        function_url = url_resp["FunctionUrl"]

        client.add_permission(
            FunctionName=function_name,
            StatementId="FunctionURLAllowPublicAccess",
            Action="lambda:InvokeFunctionUrl",
            Principal="*",
            FunctionUrlAuthType="NONE",
        )

        client.add_permission(
            FunctionName=function_name,
            StatementId="FunctionURLAllowPublicInvoke",
            Action="lambda:InvokeFunction",
            Principal="*",
        )

    log(7, 7, f"Deploy complete! URL: {function_url}")

    return DeployInfo(
        project_name=project_name,
        function_name=function_name,
        function_url=function_url,
        region=REGION,
    )
