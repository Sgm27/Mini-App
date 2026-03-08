# Mini-App

> AI-powered full-stack web application builder — describe what you want in natural language, get a deployed app on AWS Lambda.

## Overview

Mini-App is a CLI tool that lets you build and deploy full-stack web applications through conversation. It combines the **Claude Agent SDK** with an automated **AWS Lambda deployment pipeline** to go from idea to production URL in minutes.

**What it does:**
1. You describe the app you want in plain language
2. Claude autonomously writes the backend (FastAPI), frontend (HTML/CSS/JS), and database schema (MySQL)
3. The app is automatically deployed to AWS Lambda with a public URL

## Architecture

```
                          ┌─────────────────────────────┐
                          │         main.py              │
                          │     (Terminal Chat CLI)       │
                          └──────────┬──────────────────┘
                                     │
                 ┌───────────────────┼───────────────────┐
                 │                   │                   │
                 ▼                   ▼                   ▼
        /new-project <name>    Chat with Claude       /deploy
                 │                   │                   │
                 ▼                   ▼                   ▼
       ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
       │ create_project   │  │ Claude Agent SDK  │  │ deploy           │
       │                  │  │                   │  │                  │
       │ • Create MySQL   │  │ • System prompt   │  │ • Docker build   │
       │   database (RDS) │  │   (prompts.py)    │  │ • ECR push       │
       │ • Scaffold from  │  │ • MCP MySQL tools │  │ • Lambda update  │
       │   template       │  │   (mcp_server.py) │  │ • Function URL   │
       │ • Write .env     │  │ • Writes code in  │  │ • Merge frontend │
       └─────────────────┘  │   workspace/      │  └──────────────────┘
                             └──────────────────┘
                                     │
                                     ▼
                          workspace/<project-name>/
                          ├── backend/   (FastAPI)
                          ├── frontend/  (HTML/CSS/JS)
                          └── database/  (SQL migrations)
```

## Prerequisites

- Python 3.10+
- Docker (for Lambda container builds)
- AWS account with programmatic access
- Claude API access (OAuth token)

## Getting Started

```bash
# Clone and install dependencies
git clone <repo-url> && cd Mini-App
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env → fill in AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, CLAUDE_CODE_OAUTH_TOKEN

# Provision AWS infrastructure (one-time)
python setup_infra.py

# Start building
python main.py
```

## Usage

```
$ python main.py

Claude Chat (type 'exit' to quit)
  /new-project <name> — Create a new project (MySQL DB + template)
  /deploy             — Deploy current project to VPS
--------------------------------------------------

You: /new-project my-store
  [1/3] Creating MySQL database 'my_store'...
  [2/3] Copying template to workspace/my-store/...
  [3/3] Configuring backend .env...
  Done! Project 'my-store' is ready.

You: Build me an e-commerce store with product catalog, cart, and checkout
Claude: (autonomously writes backend routes, models, schemas, frontend UI, database migrations...)

  Auto-deploying...
  Deploy successful!
  URL: https://xxxxxxx.lambda-url.ap-southeast-1.on.aws/
```

### Commands

| Command | Description |
|---|---|
| `/new-project <name>` | Create a new MySQL database and scaffold project from template |
| `/deploy` | Build Docker image, push to ECR, deploy/update Lambda function |
| Any text | Send to Claude — AI autonomously builds and modifies the app |
| `exit` | Quit the CLI |

> After each AI response, the project is **auto-deployed** to AWS Lambda.

## Project Structure

```
Mini-App/
│
├── main.py                       # CLI entrypoint — chat loop, session management, auto-deploy
├── setup_infra.py                # One-time AWS provisioning (VPC, RDS, EFS, IAM, Security Groups)
├── requirements.txt
├── .env.example
│
├── utils/
│   ├── __init__.py
│   ├── prompts.py                # System prompt — defines how Claude builds full-stack apps
│   ├── create_project.py         # Project scaffolding — MySQL DB creation + template copy
│   ├── deploy.py                 # AWS Lambda deployment — Docker → ECR → Lambda + Function URL
│   ├── merge_frontend.py         # Bundles frontend/ into a single self-contained HTML file
│   └── mcp_server.py             # MySQL MCP server — gives Claude direct DB access (list, describe, execute)
│
├── full_stack_template_html/     # Base template copied for each new project
│   ├── backend/                  #   FastAPI app skeleton (routes, models, schemas, config)
│   ├── frontend/                 #   HTML + CSS + JS starter files
│   └── database/                 #   Initial SQL migration
│
├── workspace/                    # Generated projects (one subdirectory per project)
├── merged_index/                 # Single-file HTML outputs for distribution
├── project-config/               # Project metadata (JSON)
└── logs/                         # Conversation logs (JSON, timestamped)
```

## Core Components

### `main.py` — Chat Interface

The main entry point. Runs an async chat loop that:

- Manages Claude Agent SDK sessions with conversation continuity
- Spawns the MySQL MCP server as a subprocess (per-project database context)
- Streams AI responses in real-time with tool call summaries
- Handles `/new-project` and `/deploy` commands
- Auto-deploys after every AI turn
- Logs full conversations (prompts, tool calls, results) to `logs/`

### `utils/create_project.py` — Project Scaffolding

Creates a new project with a single function call:

1. **Database** — Connects to RDS MySQL and creates a new database (`CREATE DATABASE IF NOT EXISTS`)
2. **Files** — Copies `full_stack_template_html/` into `workspace/<name>/`
3. **Config** — Writes `backend/.env` with MySQL credentials, EFS upload path, and project settings

### `utils/deploy.py` — Lambda Deployment Pipeline

Deploys `workspace/<name>/backend/` to AWS Lambda as a container:

1. Generates `Dockerfile` and `handler.py` (Mangum ASGI wrapper) if missing
2. Creates/reuses an ECR repository
3. Authenticates Docker with ECR
4. Builds a `linux/amd64` Docker image and pushes to ECR
5. Creates or updates the Lambda function (VPC, EFS mount, environment variables)
6. Creates a public Function URL (no auth) for immediate access

### `utils/merge_frontend.py` — Frontend Bundler

Merges `frontend/index.html` + local CSS/JS into a **single self-contained HTML file**:

- Inlines `<link rel="stylesheet" href="css/...">` as `<style>` blocks
- Inlines `<script src="js/...">` as inline `<script>` blocks
- Preserves external CDN links (Google Fonts, libraries) unchanged
- Outputs to `merged_index/<project-name>.html`

### `utils/mcp_server.py` — MySQL MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io/) server that gives Claude direct database access:

| Tool | Description |
|---|---|
| `list_tables` | List all tables in the project database |
| `describe` | Show column info (type, null, key, default, extra) for a table |
| `execute` | Run any SQL statement — returns rows for SELECT, affected count for writes |

Runs as a stdio subprocess, isolated per project with its own database connection.

### `utils/prompts.py` — AI System Prompt

Defines Claude's behavior as a full-stack developer:

- **Stack**: FastAPI + SQLAlchemy 2 + PyMySQL (backend), pure HTML/CSS/JS (frontend)
- **Conventions**: Project structure, naming, layered architecture (routers → services → models)
- **Constraints**: MySQL via MCP only, EFS for file storage, fixed ports (2701/8386)
- **Design**: Typography, color, layout, animation guidelines for distinctive UI
- **Workflow**: Analyze → gather context → plan → implement → validate → run

### `setup_infra.py` — AWS Infrastructure

One-time provisioning script that creates:

| Resource | Details |
|---|---|
| **IAM Role** | Lambda execution role with VPC + EFS permissions |
| **VPC** | `10.0.0.0/16` with 2 public subnets across 2 AZs, Internet Gateway, route table |
| **Security Groups** | Lambda (outbound all), EFS (NFS from Lambda SG), RDS (MySQL from Lambda SG + external) |
| **EFS** | Encrypted file system with access point at `/data`, mount targets in both subnets |
| **RDS MySQL** | `db.t3.micro`, publicly accessible, in project VPC |

All resource IDs are written to `.env` automatically. Idempotent — safe to re-run.

## Tech Stack

| Layer | Technology |
|---|---|
| AI Engine | Claude Agent SDK + Claude Sonnet |
| Database Tools | MCP (Model Context Protocol) server |
| Backend | FastAPI, SQLAlchemy 2, Pydantic v2, Mangum |
| Frontend | Vanilla HTML5, CSS3, JavaScript (ES6+) |
| Database | MySQL 8.0 (AWS RDS) |
| File Storage | AWS EFS (mounted at `/mnt/efs`) |
| Compute | AWS Lambda (container image) |
| Registry | AWS ECR |
| Networking | AWS VPC, public subnets, Security Groups |

## License

MIT
