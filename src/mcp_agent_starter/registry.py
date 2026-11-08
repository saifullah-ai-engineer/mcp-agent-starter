"""The tool registry. One place to add a tool.

To add a tool:
1. Write the function in tools.py.
2. Register it on the MCP server in server.py with @server.tool().
3. Add its name and a one-line description here, so the planner and the
   README stay in sync.

The agent plans from this registry, so a tool that is not listed here will
never be picked.
"""

from __future__ import annotations

TOOLS: dict[str, str] = {
    "search_files_tool": "Search file names and contents under the workspace.",
    "fetch_url_tool": "Fetch a plain http or https URL and return its text.",
}


def tool_names() -> list[str]:
    """The tool names the agent may use, in registry order."""
    return list(TOOLS)
