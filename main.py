"""
Terminal chat interface for Claude Agent SDK.
Run: python main.py
Commands:
  /new-project <name>  — Create a new MySQL database and scaffold workspace
  /deploy              — Deploy current project to VPS (random subdomain on sonktx.online)
  exit / quit          — Exit the chat
"""

import asyncio
import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ToolResultBlock,
)

from utils import APP_BUILDER_SYSTEM_PROMPT, create_project, deploy_project

load_dotenv()

# Allow running inside a Claude Code session (e.g. VSCode terminal)
os.environ.pop("CLAUDECODE", None)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.getenv("WORKSPACE_DIR", "workspace")
LOG_DIR = os.path.join(BASE_DIR, os.getenv("LOG_DIR", "logs"))
CWD = os.path.join(BASE_DIR, WORKSPACE)
SESSION_ID = None
CURRENT_DB = ""
CURRENT_PROJECT = ""

PYTHON_BIN = sys.executable
MCP_SERVER = os.path.join(BASE_DIR, "utils", "mcp_server.py")


def _serialize_block(block) -> dict:
    """Serialize a content block to a JSON-compatible dict with full detail."""
    if isinstance(block, TextBlock):
        return {"type": "text", "text": block.text}
    elif isinstance(block, ToolUseBlock):
        return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
    elif isinstance(block, ToolResultBlock):
        return {
            "type": "tool_result",
            "tool_use_id": block.tool_use_id,
            "content": block.content,
            "is_error": block.is_error,
        }
    elif isinstance(block, ThinkingBlock):
        return {"type": "thinking", "thinking": block.thinking, "signature": block.signature}
    else:
        return {"type": "unknown", "repr": repr(block)}


def _serialize_message(msg) -> dict:
    """Serialize any SDK message to a JSON-compatible dict with full detail."""
    if isinstance(msg, AssistantMessage):
        entry = {
            "type": "assistant",
            "model": msg.model,
            "content": [_serialize_block(b) for b in msg.content],
        }
        if msg.parent_tool_use_id:
            entry["parent_tool_use_id"] = msg.parent_tool_use_id
        if msg.error:
            entry["error"] = str(msg.error)
        return entry
    elif isinstance(msg, SystemMessage):
        return {"type": "system", "subtype": msg.subtype, "data": msg.data}
    elif isinstance(msg, ResultMessage):
        return {
            "type": "result",
            "subtype": msg.subtype,
            "duration_ms": msg.duration_ms,
            "duration_api_ms": msg.duration_api_ms,
            "is_error": msg.is_error,
            "num_turns": msg.num_turns,
            "session_id": msg.session_id,
            "total_cost_usd": msg.total_cost_usd,
            "usage": msg.usage,
            "result": msg.result,
        }
    else:
        return {"type": type(msg).__name__, "repr": repr(msg)}


def _save_log(project: str, prompt: str, messages: list[dict]):
    """Write a full conversation log to LOG_DIR as a JSON file."""
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = project if project else "default"
    filename = f"{name}_{ts}.json"
    filepath = os.path.join(LOG_DIR, filename)

    log = {
        "project": name,
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "messages": messages,
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    print(f"  📝 Log saved: {filepath}")


def handle_new_project(project_name: str):
    """Create a MySQL database, copy template, and configure credentials."""
    global CWD, SESSION_ID, CURRENT_DB, CURRENT_PROJECT

    def on_step(step, total, msg):
        print(f"  [{step}/{total}] {msg}")

    print(f"\nCreating project '{project_name}'...")
    try:
        info = create_project(project_name, on_step=on_step)
    except RuntimeError as e:
        print(f"Error: {e}")
        return

    # Switch CWD, DB, and reset session
    CWD = info.project_dir
    CURRENT_DB = info.db_name
    CURRENT_PROJECT = project_name
    SESSION_ID = None

    # Save project info JSON
    info_file = os.path.join(BASE_DIR, f"{project_name}_project.json")
    with open(info_file, "w") as f:
        json.dump(info.to_dict(), f, indent=2)

    print(f"\nDone! Project '{project_name}' is ready.")
    print(f"  Database   : {info.db_name}")
    print(f"  MySQL Host : {info.mysql_host}:{info.mysql_port}")
    print(f"  Workspace  : {WORKSPACE}/{project_name}/")
    print(f"  Project info : {project_name}_project.json")
    print(f"\nChat is now pointed at the new project. Start building!\n")


def _update_api_js(project_dir: str, function_url: str) -> bool:
    """Find api.js in the project frontend and update API_URL to the Lambda function URL."""
    # Remove trailing slash from function URL
    url = function_url.rstrip("/")

    api_js_path = os.path.join(project_dir, "frontend", "js", "api.js")
    if not os.path.exists(api_js_path):
        return False

    with open(api_js_path, "r", encoding="utf-8") as f:
        content = f.read()

    import re
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


def handle_deploy():
    """Deploy the backend to AWS Lambda and update frontend api.js."""
    def on_step(step, total, msg):
        print(f"  [{step}/{total}] {msg}")

    print(f"\nDeploying backend to AWS Lambda from '{CWD}'...")
    try:
        info = deploy_project(CWD, on_step=on_step)
    except RuntimeError as e:
        print(f"Error: {e}")
        return

    print(f"\nDeploy successful!")
    print(f"  Function : {info.function_name}")
    print(f"  URL      : {info.function_url}")
    print(f"  Region   : {info.region}")

    # Update api.js in the frontend
    if _update_api_js(CWD, info.function_url):
        print(f"  api.js   : Updated API_URL → {info.function_url}")
    else:
        print(f"  api.js   : Not found at {CWD}/frontend/js/api.js (skipped)")

    print()


async def chat(prompt: str):
    """Send a message to Claude and print the streamed response."""
    global SESSION_ID

    mcp_servers = {}
    if CURRENT_DB:
        mcp_servers["mysql"] = {
            "type": "stdio",
            "command": PYTHON_BIN,
            "args": [MCP_SERVER],
            "env": {
                "MYSQL_HOST": os.getenv("MYSQL_HOST", "localhost"),
                "MYSQL_PORT": os.getenv("MYSQL_PORT", "3306"),
                "MYSQL_USER": os.getenv("MYSQL_USER", "root"),
                "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD", ""),
                "MYSQL_DATABASE": CURRENT_DB,
            },
        }

    options = ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": APP_BUILDER_SYSTEM_PROMPT,
        },
        mcp_servers=mcp_servers,
        allowed_tools=["mcp__mysql__*"] if CURRENT_DB else [],
        cwd=CWD,
        permission_mode="bypassPermissions",
        setting_sources=["user", "project", "local"],
        model="sonnet",
        effort="low",
    )

    if SESSION_ID:
        options.resume = SESSION_ID

    log_messages: list[dict] = []

    try:
        async for msg in query(prompt=prompt, options=options):
            # Serialize every message for the log
            log_messages.append(_serialize_message(msg))

            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock) and block.text:
                        print(block.text, end="", flush=True)
                    elif isinstance(block, ToolUseBlock):
                        summary = _summarize_tool(block.name, block.input)
                        print(f"\n  ⚙ {block.name} {summary}", flush=True)
                    elif isinstance(block, ToolResultBlock):
                        content = block.content
                        if isinstance(content, str):
                            preview = content[:120] + ("…" if len(content) > 120 else "")
                        elif content:
                            preview = str(content)[:120] + "…"
                        else:
                            preview = "(empty)"
                        status = "❌" if block.is_error else "✓"
                        print(f"\n  {status} result: {preview}", flush=True)

            elif isinstance(msg, ResultMessage):
                SESSION_ID = msg.session_id

        print(f"\n{'─' * 50}")
    except Exception as e:
        log_messages.append({"type": "error", "error": str(e)})
        print(f"\nError: {e}")
    finally:
        _save_log(CURRENT_PROJECT, prompt, log_messages)


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
    print("  /new-project <name> — Create a new project (MySQL DB + template)")
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
