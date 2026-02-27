"""
Terminal chat interface for Claude Agent SDK.
Run: python main.py
Commands:
  /new-project <name>  — Create a new Supabase project and scaffold workspace
  /deploy              — Deploy current project to VPS (random subdomain on sonktx.online)
  exit / quit          — Exit the chat
"""

import asyncio
import json
import os
import shutil
import sys

from dotenv import load_dotenv, set_key
from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

from utils import APP_BUILDER_SYSTEM_PROMPT, create_supabase_project, deploy_project

load_dotenv()

# Allow running inside a Claude Code session (e.g. VSCode terminal)
os.environ.pop("CLAUDECODE", None)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.getenv("WORKSPACE_DIR", "workspace")
CWD = os.path.join(BASE_DIR, WORKSPACE)
SESSION_ID = None

SUPABASE_PROJECT_ID = os.getenv("SUPABASE_PROJECT_ID", "")
SUPABASE_ACCESS_TOKEN = os.getenv("SUPABASE_ACCESS_TOKEN", "")

SUBMIT_MCP_SERVER = os.path.join(BASE_DIR, "utils", "submit_mcp_server.py")
PYTHON_BIN = sys.executable


def handle_new_project(project_name: str):
    """Create a Supabase project, copy template, and configure credentials."""
    global CWD, SUPABASE_PROJECT_ID, SESSION_ID

    def on_step(step, total, msg):
        print(f"  [{step}/{total}] {msg}")

    # --- 1. Create Supabase project ---
    print(f"\nCreating Supabase project '{project_name}'...")
    try:
        info = create_supabase_project(project_name, on_step=on_step)
    except RuntimeError as e:
        print(f"Error: {e}")
        return

    # --- 2. Copy template to workspace ---
    template_dir = os.path.join(BASE_DIR, "template")
    project_dir = os.path.join(BASE_DIR, WORKSPACE, project_name)

    if os.path.exists(project_dir):
        print(f"  Error: Directory '{project_dir}' already exists.")
        return

    print(f"  Copying template to {WORKSPACE}/{project_name}/...")
    shutil.copytree(template_dir, project_dir)

    # --- 3. Configure project credentials ---
    print("  Configuring project credentials...")

    # .env for the frontend project
    env_file = os.path.join(project_dir, ".env")
    with open(env_file, "w") as f:
        f.write(f'VITE_SUPABASE_PROJECT_ID="{info.project_ref}"\n')
        f.write(f'VITE_SUPABASE_PUBLISHABLE_KEY="{info.anon_key}"\n')
        f.write(f'VITE_SUPABASE_URL="{info.url}"\n')

    # supabase/config.toml
    config_toml = os.path.join(project_dir, "supabase", "config.toml")
    if os.path.exists(config_toml):
        with open(config_toml, "r") as f:
            content = f.read()
        content = content.replace('project_id = ""', f'project_id = "{info.project_ref}"')
        with open(config_toml, "w") as f:
            f.write(content)

    # Root .env — so MCP points to new project
    set_key(os.path.join(BASE_DIR, ".env"), "SUPABASE_PROJECT_ID", info.project_ref)
    SUPABASE_PROJECT_ID = info.project_ref

    # Save project info JSON
    info_file = os.path.join(BASE_DIR, f"{project_name}_supabase.json")
    with open(info_file, "w") as f:
        json.dump(info.to_dict(), f, indent=2)

    # Switch CWD and reset session
    CWD = project_dir
    SESSION_ID = None

    print(f"\nDone! Project '{project_name}' is ready.")
    print(f"  Supabase URL : {info.url}")
    print(f"  Workspace    : {WORKSPACE}/{project_name}/")
    print(f"  Project info : {project_name}_supabase.json")
    print(f"\nChat is now pointed at the new project. Start building!\n")


def handle_deploy():
    """Build and deploy the current project to VPS with a random subdomain."""
    def on_step(step, total, msg):
        print(f"  [{step}/{total}] {msg}")

    print(f"\nDeploying project from '{CWD}'...")
    try:
        info = deploy_project(CWD, on_step=on_step)
    except RuntimeError as e:
        print(f"Error: {e}")
        return

    print(f"\nDeploy successful!")
    print(f"  URL      : {info.url}")
    print(f"  Subdomain: {info.subdomain}")
    print(f"  VPS path : {info.vps_path}\n")


async def chat(prompt: str):
    """Send a message to Claude and print the streamed response."""
    global SESSION_ID

    options = ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": APP_BUILDER_SYSTEM_PROMPT,
        },
        mcp_servers={
            "supabase": {
                "type": "http",
                "url": f"https://mcp.supabase.com/mcp?project_ref={SUPABASE_PROJECT_ID}",
                "headers": {
                    "Authorization": f"Bearer {SUPABASE_ACCESS_TOKEN}"
                }
            },
            "submit": {
                "type": "stdio",
                "command": PYTHON_BIN,
                "args": [SUBMIT_MCP_SERVER],
                "env": {
                    "SUBMIT_CWD": CWD,
                    "SUBMIT_BASE_DIR": BASE_DIR,
                },
            },
        },
        allowed_tools=["mcp__supabase__*", "mcp__submit__*"],
        cwd=CWD,
        permission_mode="bypassPermissions",
        setting_sources=["user", "project", "local"],
        model="claude-sonnet-4-5",
        effort="low",
    )

    if SESSION_ID:
        options.resume = SESSION_ID

    try:
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock) and block.text:
                        print(block.text, end="", flush=True)
                    elif isinstance(block, ToolUseBlock):
                        # Show tool name + short summary instead of full args
                        summary = _summarize_tool(block.name, block.input)
                        print(f"\n  ⚙ {block.name} {summary}", flush=True)

            elif isinstance(msg, ResultMessage):
                SESSION_ID = msg.session_id
                break

        print(f"\n{'─' * 50}")
    except Exception as e:
        print(f"\nError: {e}")


def _summarize_tool(name: str, args: dict | None) -> str:
    """Return a short one-line summary of a tool call instead of dumping full args."""
    if not args:
        return ""

    if "file_path" in args:
        return f"→ {args['file_path']}"

    if "command" in args:
        cmd = args["command"]
        return f"→ {cmd[:80]}{'…' if len(cmd) > 80 else ''}"

    if "pattern" in args:
        return f"→ {args['pattern']}"

    if "query" in args:
        q = args["query"]
        return f"→ {q[:80]}{'…' if len(q) > 80 else ''}"
    if "name" in args:
        return f"→ {args['name']}"

    keys = ", ".join(args.keys())
    return f"({keys})"


async def main():
    os.makedirs(CWD, exist_ok=True)
    print("Claude Chat (type 'exit' to quit)")
    print("  /new-project <name> — Create a new Supabase project")
    print("  /deploy             — Deploy current project to VPS")
    print("-" * 50)

    while True:
        try:
            sys.stdout.flush()
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Bye!")
            break

        # Handle /deploy command
        if user_input.strip() == "/deploy":
            handle_deploy()
            continue

        # Handle /new-project command
        if user_input.startswith("/new-project"):
            parts = user_input.split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                print("\nUsage: /new-project <project_name>")
                continue
            handle_new_project(parts[1].strip())
            continue

        print("\nClaude: ", end="", flush=True)
        await chat(user_input)


if __name__ == "__main__":
    asyncio.run(main())
