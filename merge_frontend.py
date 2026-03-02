"""
Merge frontend files (index.html, css/style.css, js/api.js, js/app.js)
into a single self-contained index.html file.

Usage:
    python merge_frontend.py <frontend_dir> [--output <output_path>]

Example:
    python merge_frontend.py workspace/ds_save_hehe/frontend
    python merge_frontend.py workspace/ds_save_hehe/frontend --output build/index.html
"""

import argparse
import os
import re
import sys


def read_file(path: str) -> str:
    """Read file content, return empty string if not found."""
    if not os.path.isfile(path):
        print(f"  Warning: File not found: {path}", file=sys.stderr)
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def merge_frontend(frontend_dir: str, output_path: str | None = None) -> str:
    """
    Merge frontend files into a single index.html.

    - Replaces <link rel="stylesheet" href="css/..."> with inline <style>
    - Replaces <script src="js/..."></script> with inline <script>
    - Keeps external links (Google Fonts, CDN) unchanged

    Args:
        frontend_dir: Path to the frontend directory containing index.html
        output_path: Optional output file path. Defaults to frontend_dir/index_merged.html

    Returns:
        The merged HTML content.
    """
    frontend_dir = os.path.abspath(frontend_dir)
    index_path = os.path.join(frontend_dir, "index.html")

    if not os.path.isfile(index_path):
        raise FileNotFoundError(f"index.html not found in {frontend_dir}")

    html = read_file(index_path)

    # Inline local CSS: <link rel="stylesheet" href="css/style.css" />
    def replace_css_link(match):
        href = match.group(1)
        # Skip external URLs (http/https)
        if href.startswith(("http://", "https://", "//")):
            return match.group(0)
        css_path = os.path.join(frontend_dir, href)
        css_content = read_file(css_path)
        if not css_content:
            return match.group(0)
        return f"<style>\n{css_content}\n</style>"

    html = re.sub(
        r'<link\s+[^>]*rel=["\']stylesheet["\']\s+[^>]*href=["\']([^"\']+)["\'][^>]*/?>',
        replace_css_link,
        html,
    )
    # Also match when href comes before rel
    html = re.sub(
        r'<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']stylesheet["\'][^>]*/?>',
        replace_css_link,
        html,
    )

    # Inline local JS: <script src="js/api.js"></script>
    def replace_js_script(match):
        src = match.group(1)
        # Skip external URLs
        if src.startswith(("http://", "https://", "//")):
            return match.group(0)
        js_path = os.path.join(frontend_dir, src)
        js_content = read_file(js_path)
        if not js_content:
            return match.group(0)
        return f"<script>\n{js_content}\n</script>"

    html = re.sub(
        r'<script\s+src=["\']([^"\']+)["\'][^>]*>\s*</script>',
        replace_js_script,
        html,
    )

    # Write output
    if not output_path:
        output_path = os.path.join(frontend_dir, "index_merged.html")

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Merged: {output_path}")
    return html


def main():
    parser = argparse.ArgumentParser(
        description="Merge frontend files into a single index.html"
    )
    parser.add_argument(
        "frontend_dir",
        help="Path to the frontend directory containing index.html",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: <frontend_dir>/index_merged.html)",
    )
    args = parser.parse_args()

    try:
        merge_frontend(args.frontend_dir, args.output)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
