"""CLI: python -m mcp_agent_starter "your task" [--workspace DIR] [--config FILE]"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .agent import run_task
from .config import Config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the MCP agent on one task.")
    parser.add_argument("task", help="The task to run, for example: find the word todo in these files")
    parser.add_argument("--workspace", default=".", help="Folder the file search tool may read")
    parser.add_argument("--config", default=None, help="Path to a config.toml file")
    args = parser.parse_args(argv)
    if args.config:
        config = Config.from_file(args.config)
    else:
        config = Config.default()
    config.workspace = args.workspace
    result = asyncio.run(run_task(args.task, config))
    print(result["answer"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
