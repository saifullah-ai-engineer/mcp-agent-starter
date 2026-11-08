"""The real MCP server.

The two tools are registered on a genuine MCP server from the official MCP
Python SDK (mcp 2.x, MCPServer). The agent talks to its tools through this
server, never by calling the tool functions directly, so the MCP boundary
is real: tools are listed, described, and called through the protocol.

Add a new tool here and in registry.py, and the agent can use it.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.server.mcpserver import MCPServer

from .config import Config
from .tools import fetch_url, search_files


def build_server(config: Config | None = None) -> MCPServer:
    """Build the MCP server with the built-in tools registered."""
    config = config or Config.default()
    server = MCPServer("mcp-agent-starter")

    @server.tool()
    def search_files_tool(query: str) -> str:
        """Search file names and file contents under the workspace for a query. Returns matching paths with a snippet line."""
        return search_files(query, root=config.workspace, max_results=config.max_results)

    @server.tool()
    def fetch_url_tool(url: str) -> str:
        """Fetch a plain http or https URL and return its readable text. No API key needed."""
        return fetch_url(
            url,
            timeout_seconds=config.fetch_timeout_seconds,
            max_chars=config.fetch_max_chars,
        )

    return server


async def list_tool_names(server: MCPServer) -> list[str]:
    """List the tool names the server exposes, through MCP."""
    tools = await server.list_tools()
    return [tool.name for tool in tools]


def call_tool(server: MCPServer, name: str, args: dict[str, Any]) -> str:
    """Call a tool through the MCP server and return its text result."""
    result = asyncio.run(server.call_tool(name, args))
    texts = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            texts.append(text)
    return "\n".join(texts) if texts else "(no text returned)"
