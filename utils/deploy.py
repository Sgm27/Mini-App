"""
Deploy a FastAPI backend to AWS Lambda using Docker container image via AWS CodeBuild.

Flow:
  1. Ensure Dockerfile and handler.py exist
  2. Use pre-created IAM role from .env
  3. Create/get ECR repository
  4. Zip backend source and upload to S3
  5. Create/update CodeBuild project
  6. Trigger CodeBuild (docker build + push to ECR)
  7. Create/update Lambda function from container image

Usage:
    from utils import deploy_project
    info = deploy_project("/path/to/project")
    print(info.function_url)
"""

import io
import json
import os
import time
import zipfile
from dataclasses import dataclass
from typing import Callable, Optional

import boto3

from config import cfg

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
        aws_access_key_id=cfg.get("aws_access_key_id"),
        aws_secret_access_key=cfg.get("aws_secret_access_key"),
        region_name=REGION,
    )


def _get_or_create_role(session: boto3.Session) -> str:
    iam = session.client("iam")

    REQUIRED_POLICIES = [
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
        "arn:aws:iam::aws:policy/AmazonElasticFileSystemClientReadWriteAccess",
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


BUILDSPEC = """\
version: 0.2
phases:
  pre_build:
    commands:
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
  build:
    commands:
      - docker build --platform linux/amd64 --provenance=false -t $IMAGE_URI .
  post_build:
    commands:
      - docker push $IMAGE_URI
"""


def _zip_and_upload_source(session: boto3.Session, backend_dir: str, s3_bucket: str, function_name: str) -> str:
    """Zip backend_dir and upload to S3. Returns S3 key."""
    s3_key = f"codebuild-source/{function_name}/source.zip"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(backend_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".venv", "venv", ".git")]
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, backend_dir)
                zf.write(file_path, arcname)

    buf.seek(0)
    session.client("s3").put_object(Bucket=s3_bucket, Key=s3_key, Body=buf.read())
    return s3_key


def _get_or_create_codebuild_project(
    session: boto3.Session,
    project_name: str,
    repo_uri: str,
    s3_bucket: str,
    s3_key: str,
    codebuild_role_arn: str,
) -> None:
    """Create or update a CodeBuild project that builds and pushes a Docker image to ECR."""
    cb = session.client("codebuild")
    ecr_registry = repo_uri.split("/")[0]
    image_uri = f"{repo_uri}:latest"

    project_params = dict(
        source={
            "type": "S3",
            "location": f"{s3_bucket}/{s3_key}",
            "buildspec": BUILDSPEC,
        },
        artifacts={"type": "NO_ARTIFACTS"},
        environment={
            "type": "LINUX_CONTAINER",
            "image": "aws/codebuild/standard:7.0",
            "computeType": "BUILD_GENERAL1_SMALL",
            "privilegedMode": True,
            "environmentVariables": [
                {"name": "ECR_REGISTRY", "value": ecr_registry, "type": "PLAINTEXT"},
                {"name": "IMAGE_URI", "value": image_uri, "type": "PLAINTEXT"},
            ],
        },
        serviceRole=codebuild_role_arn,
    )

    result = cb.batch_get_projects(names=[project_name])
    if result["projects"]:
        cb.update_project(name=project_name, **project_params)
    else:
        cb.create_project(name=project_name, **project_params)


def _run_codebuild_and_wait(session: boto3.Session, project_name: str) -> None:
    """Trigger a CodeBuild build and poll until it succeeds or fails."""
    cb = session.client("codebuild")
    build_id = cb.start_build(projectName=project_name)["build"]["id"]

    while True:
        build = cb.batch_get_builds(ids=[build_id])["builds"][0]
        status = build["buildStatus"]
        phase = build.get("currentPhase", "")
        print(f"    CodeBuild status: {status} | phase: {phase}")

        if status == "SUCCEEDED":
            return
        if status in ("FAILED", "FAULT", "STOPPED", "TIMED_OUT"):
            deep_link = build.get("logs", {}).get("deepLink", "")
            raise RuntimeError(f"CodeBuild {status}. Logs: {deep_link}")
        time.sleep(15)


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
    role_arn = cfg.get("aws_lambda_role_arn")
    if not role_arn:
        raise ValueError("aws_lambda_role_arn not set in .env.json")
    log(2, 7, f"Using IAM role: {role_arn}")

    # 2. ECR Repository
    log(3, 7, f"Getting/creating ECR repository '{function_name}'...")
    repo_uri = _get_or_create_ecr_repo(session, function_name)

    # 3. Zip source and upload to S3
    s3_bucket = cfg.get("s3_bucket_name")
    codebuild_role_arn = cfg.get("codebuild_role_arn")
    if not s3_bucket:
        raise ValueError("s3_bucket_name not set in .env.json")
    if not codebuild_role_arn:
        raise ValueError("codebuild_role_arn not set in .env.json")

    log(4, 7, "Zipping and uploading source to S3...")
    s3_key = _zip_and_upload_source(session, backend_dir, s3_bucket, function_name)

    # 4. Create/update CodeBuild project
    log(5, 7, "Syncing CodeBuild project...")
    _get_or_create_codebuild_project(session, function_name, repo_uri, s3_bucket, s3_key, codebuild_role_arn)

    # 5. Run CodeBuild and wait
    log(6, 7, "Building and pushing image via CodeBuild...")
    _run_codebuild_and_wait(session, function_name)
    image_uri = f"{repo_uri}:latest"

    # 6. Environment variables from backend .env
    env_vars = _read_backend_env(backend_dir)

    # 7. Create/update Lambda function
    log(7, 7, "Creating/updating Lambda function...")
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
            Timeout=60,
            MemorySize=256,
            VpcConfig={
                "SubnetIds": cfg.get("lambda_subnet_ids", "").split(","),
                "SecurityGroupIds": [cfg.get("lambda_security_group_id")],
            },
            FileSystemConfigs=[{
                "Arn": cfg.get("efs_access_point_arn"),
                "LocalMountPath": "/mnt/efs",
            }],
        )
        waiter.wait(FunctionName=function_name)

        # Get or create Function URL (no CORS here — handled by FastAPI middleware)
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
                    Timeout=60,
                    MemorySize=256,
                    Environment={"Variables": env_vars},
                    VpcConfig={
                        "SubnetIds": cfg.get("lambda_subnet_ids", "").split(","),
                        "SecurityGroupIds": [cfg.get("lambda_security_group_id")],
                    },
                    FileSystemConfigs=[{
                        "Arn": cfg.get("efs_access_point_arn"),
                        "LocalMountPath": "/mnt/efs",
                    }],
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
