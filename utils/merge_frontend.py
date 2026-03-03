"""
Merge frontend files (index.html, css/style.css, js/api.js, js/app.js)
into a single self-contained HTML file.
"""

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


def merge_frontend(project_dir: str, project_name: str, output_dir: str) -> str | None:
    """
    Merge frontend files into a single {project_name}.html.

    - Replaces <link rel="stylesheet" href="css/..."> with inline <style>
    - Replaces <script src="js/..."></script> with inline <script>
    - Keeps external links (Google Fonts, CDN) unchanged

    Args:
        project_dir: Path to the project directory (contains frontend/)
        project_name: Name of the current project (used for output filename)
        output_dir: Directory to save the merged HTML file

    Returns:
        The output file path, or None if index.html not found.
    """
    frontend_dir = os.path.join(os.path.abspath(project_dir), "frontend")
    index_path = os.path.join(frontend_dir, "index.html")

    if not os.path.isfile(index_path):
        print(f"  Warning: index.html not found in {frontend_dir}", file=sys.stderr)
        return None

    html = read_file(index_path)

    # Inline local CSS: <link rel="stylesheet" href="css/style.css" />
    def replace_css_link(match):
        href = match.group(1)
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
    html = re.sub(
        r'<link\s+[^>]*href=["\']([^"\']+)["\'][^>]*rel=["\']stylesheet["\']\s[^>]*/?>',
        replace_css_link,
        html,
    )

    # Inline local JS: <script src="js/api.js"></script>
    def replace_js_script(match):
        src = match.group(1)
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
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{project_name}.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
