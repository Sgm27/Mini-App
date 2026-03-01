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
    python create_lambda.py <function_name> [--env KEY=VALUE ...]
"""

import argparse
import json
import os
import subprocess
import time

import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = "ap-southeast-1"
ROLE_NAME = "lambda-basic-execution-role"
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "function", "backend")

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


def get_session() -> boto3.Session:
    return boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=REGION,
    )


def get_or_create_role(session: boto3.Session) -> str:
    """Get existing role ARN or create a new one with basic Lambda permissions."""
    iam = session.client("iam")

    try:
        resp = iam.get_role(RoleName=ROLE_NAME)
        print(f"[OK] Role '{ROLE_NAME}' already exists.")
        return resp["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        pass

    print(f"[..] Creating IAM role '{ROLE_NAME}'...")
    resp = iam.create_role(
        RoleName=ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(TRUST_POLICY),
        Description="Basic execution role for Lambda functions",
    )
    role_arn = resp["Role"]["Arn"]

    iam.attach_role_policy(
        RoleName=ROLE_NAME,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )
    print(f"[OK] Role created: {role_arn}")

    print("[..] Waiting for role to propagate...")
    time.sleep(10)

    return role_arn


def get_or_create_ecr_repo(session: boto3.Session, repo_name: str) -> str:
    """Get or create an ECR repository. Returns the repository URI."""
    ecr = session.client("ecr")

    try:
        resp = ecr.describe_repositories(repositoryNames=[repo_name])
        uri = resp["repositories"][0]["repositoryUri"]
        print(f"[OK] ECR repo '{repo_name}' already exists: {uri}")
        return uri
    except ecr.exceptions.RepositoryNotFoundException:
        pass

    print(f"[..] Creating ECR repository '{repo_name}'...")
    resp = ecr.create_repository(
        repositoryName=repo_name,
        imageScanningConfiguration={"scanOnPush": False},
        imageTagMutability="MUTABLE",
    )
    uri = resp["repository"]["repositoryUri"]
    print(f"[OK] ECR repo created: {uri}")
    return uri


def docker_login_ecr(session: boto3.Session) -> str:
    """Authenticate Docker with ECR. Returns the registry URL."""
    ecr = session.client("ecr")
    token_resp = ecr.get_authorization_token()
    auth = token_resp["authorizationData"][0]
    registry = auth["proxyEndpoint"]  # https://<account>.dkr.ecr.<region>.amazonaws.com

    # Use docker login via stdin for security
    import base64
    decoded = base64.b64decode(auth["authorizationToken"]).decode()
    username, password = decoded.split(":", 1)

    print(f"[..] Logging in to ECR: {registry}")
    proc = subprocess.run(
        ["docker", "login", "--username", username, "--password-stdin", registry],
        input=password,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Docker login failed: {proc.stderr}")
    print("[OK] Docker logged in to ECR.")
    return registry


def build_and_push_image(repo_uri: str, tag: str = "latest") -> str:
    """Build Docker image and push to ECR. Returns the full image URI."""
    image_uri = f"{repo_uri}:{tag}"

    print(f"[..] Building Docker image from {BACKEND_DIR}...")
    proc = subprocess.run(
        ["docker", "build", "--platform", "linux/amd64", "--provenance=false", "-t", image_uri, "."],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr)
        raise RuntimeError("Docker build failed.")
    print(f"[OK] Image built: {image_uri}")

    print(f"[..] Pushing image to ECR...")
    proc = subprocess.run(
        ["docker", "push", image_uri],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stderr)
        raise RuntimeError("Docker push failed.")
    print(f"[OK] Image pushed: {image_uri}")

    return image_uri


def read_backend_env() -> dict[str, str]:
    """Read environment variables from the backend .env file."""
    env_path = os.path.join(BACKEND_DIR, ".env")
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip()
    return env_vars


def create_lambda(function_name: str, extra_env: list[str] | None = None):
    """Create or update a Lambda function using a Docker container image."""
    session = get_session()
    role_arn = get_or_create_role(session)

    # --- ECR ---
    repo_name = function_name
    repo_uri = get_or_create_ecr_repo(session, repo_name)

    # --- Docker build & push ---
    docker_login_ecr(session)
    image_uri = build_and_push_image(repo_uri)

    # --- Environment variables ---
    env_vars = read_backend_env()
    # Override/add from CLI --env flags
    if extra_env:
        for item in extra_env:
            key, _, value = item.partition("=")
            env_vars[key] = value

    # --- Lambda ---
    client = session.client("lambda")

    try:
        # Function already exists → update code + config
        client.get_function(FunctionName=function_name)
        print(f"[..] Function '{function_name}' exists, updating...")

        client.update_function_code(
            FunctionName=function_name,
            ImageUri=image_uri,
        )
        # Wait for update to complete
        waiter = client.get_waiter("function_updated_v2")
        waiter.wait(FunctionName=function_name)

        client.update_function_configuration(
            FunctionName=function_name,
            Environment={"Variables": env_vars},
            Timeout=30,
            MemorySize=256,
        )
        waiter.wait(FunctionName=function_name)

        print(f"[OK] Function updated!")

        # Get existing Function URL
        try:
            url_resp = client.get_function_url_config(FunctionName=function_name)
            print(f"[OK] Function URL: {url_resp['FunctionUrl']}")
        except client.exceptions.ResourceNotFoundException:
            url_resp = client.create_function_url_config(
                FunctionName=function_name,
                AuthType="NONE",
            )
            print(f"[OK] Function URL: {url_resp['FunctionUrl']}")
        return

    except client.exceptions.ResourceNotFoundException:
        pass

    # --- Create new function ---
    print(f"[..] Creating Lambda function '{function_name}'...")
    for attempt in range(6):
        try:
            resp = client.create_function(
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
                print(f"[..] Role not ready, retrying in 5s... ({attempt + 1}/5)")
                time.sleep(5)
            else:
                raise

    # Wait for function to become Active
    print("[..] Waiting for function to become Active...")
    waiter = client.get_waiter("function_active_v2")
    waiter.wait(FunctionName=function_name)

    print(f"[OK] Function created!")
    print(f"     ARN:    {resp['FunctionArn']}")
    print(f"     Region: {REGION}")

    # --- Function URL ---
    print(f"[..] Creating Function URL...")
    url_resp = client.create_function_url_config(
        FunctionName=function_name,
        AuthType="NONE",
    )

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

    print(f"[OK] Function URL: {url_resp['FunctionUrl']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deploy FastAPI backend to AWS Lambda (Docker)"
    )
    parser.add_argument("function_name", help="Name of the Lambda function")
    parser.add_argument(
        "--env",
        dest="env_vars",
        action="append",
        help="Extra env vars: --env KEY=VALUE (can repeat)",
    )
    args = parser.parse_args()

    create_lambda(args.function_name, args.env_vars)
