"""
MySQL MCP server with 3 tools: list_tables, describe, execute.

Runs as a stdio subprocess spawned by main.py.

Environment variables (set by main.py):
  MYSQL_HOST     — MySQL host
  MYSQL_PORT     — MySQL port
  MYSQL_USER     — MySQL user
  MYSQL_PASSWORD — MySQL password
  MYSQL_DATABASE — Active project database name
"""

import asyncio
import json
import os

import mysql.connector
from mysql.connector import Error
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool

server = Server("mysql_mcp")


def _get_connection():
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DATABASE", ""),
    )


def _escape_identifier(name: str) -> str:
    if "`" in name:
        raise ValueError("Invalid identifier")
    return f"`{name}`"


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="list_tables",
            description="List all tables in the current MySQL database.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="describe",
            description="Show full column info (Field, Type, Null, Key, Default, Extra, Comment) for a table.",
            inputSchema={
                "type": "object",
                "properties": {
                    "table": {"type": "string", "description": "Table name"},
                },
                "required": ["table"],
            },
        ),
        Tool(
            name="execute",
            description="Execute any SQL statement (SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, etc.). Returns rows for SELECT or affected_rows for write statements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL statement to execute"},
                },
                "required": ["sql"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        conn = _get_connection()
    except Error as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"MySQL connection error: {e}")],
            isError=True,
        )

    try:
        if name == "list_tables":
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(tables, ensure_ascii=False))]
            )

        elif name == "describe":
            table = arguments.get("table", "")
            if not table:
                return CallToolResult(
                    content=[TextContent(type="text", text="Missing required parameter: table")],
                    isError=True,
                )
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"SHOW FULL COLUMNS FROM {_escape_identifier(table)}")
            rows = cursor.fetchall()
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(rows, default=str, ensure_ascii=False))]
            )

        elif name == "execute":
            sql = arguments.get("sql", "").strip()
            if not sql:
                return CallToolResult(
                    content=[TextContent(type="text", text="Missing required parameter: sql")],
                    isError=True,
                )

            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)

            if sql.lower().startswith("select") or sql.lower().startswith("show") or sql.lower().startswith("explain"):
                rows = cursor.fetchall()
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(rows, default=str, ensure_ascii=False))]
                )
            else:
                conn.commit()
                result = {"affected_rows": cursor.rowcount, "last_row_id": cursor.lastrowid}
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result))]
                )

        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            )

    except Error as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"MySQL error: {e}")],
            isError=True,
        )
    finally:
        if conn.is_connected():
            conn.close()


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
