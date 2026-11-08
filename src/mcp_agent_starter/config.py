"""Configuration for mcp-agent-starter.

Config lives in a small TOML file so it can be read with the standard
library, no extra dependency. See config.toml at the repo root.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass
class Config:
    """Everything the agent needs, with safe defaults."""

    workspace: str = "."
    max_steps: int = 6
    max_results: int = 5
    fetch_timeout_seconds: int = 10
    fetch_max_chars: int = 4000
    user_agent: str = "mcp-agent-starter/0.1.0"
    # Optional LLM hook. Off by default. If set, it must be a callable that
    # takes (task, tool_names) and returns a list of {"tool": ..., "args": ...}.
    llm_callable: Callable[[str, list[str]], list[dict[str, Any]]] | None = field(
        default=None, repr=False
    )

    @classmethod
    def from_file(cls, path: str | Path) -> "Config":
        """Load config from a TOML file. Missing keys fall back to defaults."""
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        agent = data.get("agent", {})
        tools = data.get("tools", {})
        return cls(
            workspace=tools.get("workspace", "."),
            max_steps=agent.get("max_steps", 6),
            max_results=tools.get("max_results", 5),
            fetch_timeout_seconds=tools.get("fetch_timeout_seconds", 10),
            fetch_max_chars=tools.get("fetch_max_chars", 4000),
            user_agent=tools.get("user_agent", "mcp-agent-starter/0.1.0"),
        )

    @classmethod
    def default(cls) -> "Config":
        """The built-in defaults, no file needed."""
        return cls()
