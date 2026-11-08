"""The two example tools, as plain functions.

Each tool is written as a normal Python function first, then registered on
the real MCP server in server.py. That keeps the tools easy to test on their
own, and easy to reuse outside MCP.
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

# Folders the file search never walks into.
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".idea"}
MAX_FILE_BYTES = 200_000
SNIPPET_CHARS = 120


def search_files(query: str, root: str = ".", max_results: int = 5) -> str:
    """Search file names and file contents under root for query.

    Returns one line per match: the relative path, and the first matching
    line of the file when the match is in the contents. Only files under
    root are ever read, hidden folders and virtual environments are skipped,
    and files larger than 200 KB are skipped.
    """
    query = (query or "").strip()
    if not query:
        return "No matches: the search query was empty."
    root_path = Path(root).resolve()
    needle = query.lower()
    matches: list[str] = []
    for path in sorted(root_path.rglob("*")):
        if len(matches) >= max_results:
            break
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS or part.startswith(".") for part in path.parts[len(root_path.parts):-1]):
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        rel = str(path.relative_to(root_path))
        if needle in path.name.lower():
            matches.append(f"{rel} (matched file name)")
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            if needle in line.lower():
                snippet = line.strip()[:SNIPPET_CHARS]
                matches.append(f"{rel}: {snippet}")
                break
    if not matches:
        return f"No matches for '{query}' under {root_path}."
    return "\n".join(matches)


def fetch_url(url: str, timeout_seconds: int = 10, max_chars: int = 4000) -> str:
    """Fetch a plain URL and return its readable text.

    Only http and https URLs are allowed. No API key is used. The response
    is cut to max_chars so a huge page cannot flood the agent.
    """
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return "Error: only http:// and https:// URLs are allowed."
    request = urllib.request.Request(url, headers={"User-Agent": "mcp-agent-starter/0.1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read(200_000)
            content_type = response.headers.get("Content-Type", "unknown")
            status = response.status
    except Exception as exc:  # noqa: BLE001 - the caller needs the reason
        return f"Error fetching {url}: {exc}"
    text = raw.decode("utf-8", errors="ignore")
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return f"[{status}] {content_type}\n{text[:max_chars]}"
