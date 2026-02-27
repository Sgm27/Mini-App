"""
External MCP server for the submit_project tool.

Runs as a stdio subprocess to avoid the in-process SDK bug
(CLIConnectionError: ProcessTransport is not ready for writing).

Environment variables (set by main.py before each query):
  SUBMIT_CWD      — workspace directory to deploy
  SUBMIT_BASE_DIR — project root (where submit_results.json lives)
"""

import asyncio
import json
import os
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

# Add parent dir so we can import utils.deploy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.deploy import deploy_project

server = Server("submit_answer")

TOOL_DESCRIPTION = (
    "MANDATORY: You MUST call this tool as the FINAL step after completing any of these actions: "
    "(1) Finished building a new app (all code written, build passes, app is functional), "
    "(2) Modified/updated any source code files in the project (bug fixes, new features, refactors, style changes). "
    "This tool builds and deploys the project so the user can preview their app live. "
    "Call it ONCE at the very end of your work, after `npm run build` succeeds. Never skip this step."
)


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="submit_project",
            description=TOOL_DESCRIPTION,
            inputSchema={"type": "object", "properties": {}, "required": []},
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "submit_project":
        return CallToolResult(
            content=[TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True,
        )

    from datetime import datetime, timezone

    cwd = os.environ.get("SUBMIT_CWD", "")
    base_dir = os.environ.get("SUBMIT_BASE_DIR", "")

    if not cwd or not base_dir:
        return CallToolResult(
            content=[TextContent(type="text", text="SUBMIT_CWD or SUBMIT_BASE_DIR not set")],
            isError=True,
        )

    timestamp = datetime.now(timezone.utc).isoformat()
    result_file = os.path.join(base_dir, "submit_results.json")

    if os.path.exists(result_file):
        with open(result_file, "r") as f:
            results = json.load(f)
    else:
        results = []

    try:
        info = deploy_project(cwd)
        entry = {
            "timestamp": timestamp,
            "status": "success",
            "url": info.url,
            "subdomain": info.subdomain,
            "vps_path": info.vps_path,
            "workspace": cwd,
        }
        results.append(entry)
        with open(result_file, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(entry))]
        )
    except RuntimeError as e:
        entry = {
            "timestamp": timestamp,
            "status": "failed",
            "error": str(e),
            "workspace": cwd,
        }
        results.append(entry)
        with open(result_file, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        return CallToolResult(
            content=[TextContent(type="text", text=f"Deploy failed: {e}")],
            isError=True,
        )


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
