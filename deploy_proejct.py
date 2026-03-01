"""
CLI tool to manage and deploy workspace projects to AWS Lambda.

Usage:
    python deploy_proejct.py --list
    python deploy_proejct.py --deploy <project_name>
    python deploy_proejct.py --status
    python deploy_proejct.py --delete <project_name>
"""

import argparse
import os
import re
import sys

import boto3
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.join(BASE_DIR, os.getenv("WORKSPACE_DIR", "workspace"))
REGION = "ap-southeast-1"


def get_session() -> boto3.Session:
    return boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=REGION,
    )


# ── --list ───────────────────────────────────────────────────────────────────

def cmd_list():
    """List all projects in the workspace directory."""
    if not os.path.isdir(WORKSPACE):
        print(f"Workspace not found: {WORKSPACE}")
        sys.exit(1)

    projects = sorted(
        d for d in os.listdir(WORKSPACE)
        if os.path.isdir(os.path.join(WORKSPACE, d))
    )

    if not projects:
        print("No projects found in workspace.")
        return

    print(f"Projects in {WORKSPACE}:\n")
    for i, name in enumerate(projects, 1):
        project_dir = os.path.join(WORKSPACE, name)
        has_backend = os.path.isdir(os.path.join(project_dir, "backend"))
        has_frontend = os.path.isdir(os.path.join(project_dir, "frontend"))
        parts = []
        if has_backend:
            parts.append("backend")
        if has_frontend:
            parts.append("frontend")
        status = ", ".join(parts) if parts else "empty"
        print(f"  {i}. {name}  ({status})")

    print(f"\nTotal: {len(projects)} project(s)")


# ── --status ─────────────────────────────────────────────────────────────────

def cmd_status():
    """Show all Lambda functions deployed in the region."""
    session = get_session()
    client = session.client("lambda")

    print(f"Lambda functions in {REGION}:\n")

    paginator = client.get_paginator("list_functions")
    functions = []
    for page in paginator.paginate():
        functions.extend(page["Functions"])

    if not functions:
        print("  No Lambda functions found.")
        return

    for fn in functions:
        name = fn["FunctionName"]
        state = fn.get("State", "Unknown")
        runtime = fn.get("PackageType", "Unknown")
        last_modified = fn.get("LastModified", "N/A")
        memory = fn.get("MemorySize", "N/A")
        timeout = fn.get("Timeout", "N/A")

        # Try to get Function URL
        url = "N/A"
        try:
            url_resp = client.get_function_url_config(FunctionName=name)
            url = url_resp["FunctionUrl"]
        except client.exceptions.ResourceNotFoundException:
            pass

        print(f"  {name}")
        print(f"    State    : {state}")
        print(f"    Type     : {runtime}")
        print(f"    Memory   : {memory} MB")
        print(f"    Timeout  : {timeout}s")
        print(f"    Modified : {last_modified}")
        print(f"    URL      : {url}")
        print()

    print(f"Total: {len(functions)} function(s)")


# ── --deploy ─────────────────────────────────────────────────────────────────

def _update_api_js(project_dir: str, function_url: str) -> bool:
    """Update API_URL in frontend/js/api.js to point to the Lambda function URL."""
    url = function_url.rstrip("/")
    api_js_path = os.path.join(project_dir, "frontend", "js", "api.js")
    if not os.path.exists(api_js_path):
        return False

    with open(api_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = re.sub(
        r"const\s+API_URL\s*=\s*['\"].*?['\"]",
        f"const API_URL = '{url}'",
        content,
    )

    if new_content != content:
        with open(api_js_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    return False


def cmd_deploy(project_name: str):
    """Deploy a project's backend to AWS Lambda."""
    project_dir = os.path.join(WORKSPACE, project_name)
    if not os.path.isdir(project_dir):
        print(f"Project not found: {project_dir}")
        sys.exit(1)

    backend_dir = os.path.join(project_dir, "backend")
    if not os.path.isdir(backend_dir):
        print(f"Backend directory not found: {backend_dir}")
        sys.exit(1)

    from utils.deploy import deploy_project

    def on_step(step, total, msg):
        print(f"  [{step}/{total}] {msg}")

    print(f"\nDeploying '{project_name}' to AWS Lambda...\n")

    try:
        info = deploy_project(project_dir, function_name=project_name, on_step=on_step)
    except RuntimeError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    print(f"\nDeploy successful!")
    print(f"  Function : {info.function_name}")
    print(f"  URL      : {info.function_url}")
    print(f"  Region   : {info.region}")

    if _update_api_js(project_dir, info.function_url):
        print(f"  api.js   : Updated API_URL -> {info.function_url.rstrip('/')}")
    else:
        print(f"  api.js   : Not found (skipped)")

    print()


# ── --delete ─────────────────────────────────────────────────────────────────

def cmd_delete(function_name: str):
    """Delete a Lambda function and its ECR repository."""
    session = get_session()
    client = session.client("lambda")
    ecr = session.client("ecr")

    print(f"\nDeleting Lambda function '{function_name}'...")

    # Delete Function URL config
    try:
        client.delete_function_url_config(FunctionName=function_name)
        print(f"  [OK] Function URL deleted")
    except client.exceptions.ResourceNotFoundException:
        pass

    # Delete Lambda function
    try:
        client.delete_function(FunctionName=function_name)
        print(f"  [OK] Lambda function deleted")
    except client.exceptions.ResourceNotFoundException:
        print(f"  [--] Lambda function not found (already deleted)")

    # Delete ECR repository
    try:
        ecr.delete_repository(repositoryName=function_name, force=True)
        print(f"  [OK] ECR repository deleted")
    except ecr.exceptions.RepositoryNotFoundException:
        print(f"  [--] ECR repository not found (already deleted)")

    print()


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Manage and deploy workspace projects to AWS Lambda",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python deploy_proejct.py --list\n"
            "  python deploy_proejct.py --deploy ds-jk\n"
            "  python deploy_proejct.py --status\n"
            "  python deploy_proejct.py --delete ds-jk\n"
        ),
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="List all projects in workspace")
    group.add_argument("--deploy", metavar="PROJECT", help="Deploy a project to Lambda")
    group.add_argument("--status", action="store_true", help="Show all deployed Lambda functions")
    group.add_argument("--delete", metavar="PROJECT", help="Delete a Lambda function and its ECR repo")

    args = parser.parse_args()

    if args.list:
        cmd_list()
    elif args.deploy:
        cmd_deploy(args.deploy)
    elif args.status:
        cmd_status()
    elif args.delete:
        cmd_delete(args.delete)


if __name__ == "__main__":
    main()
