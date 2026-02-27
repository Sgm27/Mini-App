"""
Supabase project creation utilities.

Provides a single high-level function `create_supabase_project()` that handles
the full lifecycle: create project → wait healthy → retrieve API keys.
"""

import os
import secrets
import string
import time
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.supabase.com/v1"


def _get_headers() -> dict:
    token = os.getenv("SUPABASE_ACCESS_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _generate_db_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _list_organizations() -> list[dict]:
    resp = requests.get(f"{API_BASE}/organizations", headers=_get_headers())
    resp.raise_for_status()
    return resp.json()


def _create_project(name: str, org_id: str, db_password: str, region: str) -> dict:
    payload = {
        "name": name,
        "organization_id": org_id,
        "db_pass": db_password,
        "region": region,
    }
    resp = requests.post(f"{API_BASE}/projects", headers=_get_headers(), json=payload)
    resp.raise_for_status()
    return resp.json()


def _wait_for_healthy(project_ref: str, timeout: int = 600, interval: int = 15) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(
            f"{API_BASE}/projects/{project_ref}/health",
            headers=_get_headers(),
            params={"services": "auth,rest,db,realtime,storage"},
        )
        if resp.status_code == 200:
            services = resp.json()
            if all(s.get("status") == "ACTIVE_HEALTHY" for s in services):
                return True
        time.sleep(interval)
    return False


def _get_api_keys(project_ref: str) -> tuple[str, str]:
    resp = requests.get(
        f"{API_BASE}/projects/{project_ref}/api-keys", headers=_get_headers()
    )
    resp.raise_for_status()
    anon_key = ""
    service_role_key = ""
    for key in resp.json():
        if key["name"] == "anon":
            anon_key = key["api_key"]
        elif key["name"] == "service_role":
            service_role_key = key["api_key"]
    return anon_key, service_role_key


@dataclass
class SupabaseProjectInfo:
    project_name: str
    project_ref: str
    region: str
    db_password: str
    url: str
    anon_key: str
    service_role_key: str

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "project_ref": self.project_ref,
            "region": self.region,
            "db_password": self.db_password,
            "url": self.url,
            "anon_key": self.anon_key,
            "service_role_key": self.service_role_key,
        }


def create_supabase_project(
    name: str,
    region: str = "ap-southeast-1",
    on_step: callable = None,
) -> SupabaseProjectInfo:
    """
    Create a Supabase project end-to-end and return its info.

    Args:
        name: Project name.
        region: Supabase region (default: ap-southeast-1).
        on_step: Optional callback(step: int, total: int, message: str) for progress.

    Returns:
        SupabaseProjectInfo with all credentials.

    Raises:
        RuntimeError: If no organizations found.
        requests.HTTPError: On API failures.
    """
    def log(step: int, total: int, msg: str):
        if on_step:
            on_step(step, total, msg)

    # 1. Get organization
    log(1, 3, f"Creating project '{name}'...")
    orgs = _list_organizations()
    if not orgs:
        raise RuntimeError("No organizations found in your Supabase account.")

    # 2. Create project and wait for healthy
    db_password = _generate_db_password()
    project = _create_project(name, orgs[0]["id"], db_password, region)
    project_ref = project["id"]

    log(2, 3, f"Waiting for project {project_ref} to be ready...")
    if not _wait_for_healthy(project_ref):
        log(2, 3, "WARNING: Project did not become healthy within timeout.")

    # 3. Retrieve API keys
    log(3, 3, "Retrieving API keys...")
    anon_key, service_role_key = _get_api_keys(project_ref)

    return SupabaseProjectInfo(
        project_name=name,
        project_ref=project_ref,
        region=region,
        db_password=db_password,
        url=f"https://{project_ref}.supabase.co",
        anon_key=anon_key,
        service_role_key=service_role_key,
    )
