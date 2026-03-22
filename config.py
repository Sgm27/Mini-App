"""
Load configuration from .env.json.

Usage:
    from config import cfg

    cfg["mysql_host"]
    cfg.get("workspace_dir", "workspace")
"""

import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.json")

with open(_CONFIG_PATH, "r", encoding="utf-8") as _f:
    cfg: dict = json.load(_f)
