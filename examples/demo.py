"""30 second demo. Runs with no API key and no cost.

It builds a small workspace with two sample files, then runs the agent on
two tasks: search the files for a word, and fetch a plain web page.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from mcp_agent_starter import Config, run_task


def make_workspace() -> Path:
    folder = Path(tempfile.mkdtemp(prefix="mcp-agent-demo-"))
    (folder / "notes.txt").write_text(
        "Launch plan\n"
        "We launch the new agent on Monday.\n"
        "The launch checklist is in plan.md.\n",
        encoding="utf-8",
    )
    (folder / "plan.md").write_text(
        "# Plan\n\n- Write the launch notes.\n- Test the agent.\n- Ship it.\n",
        encoding="utf-8",
    )
    return folder


async def main() -> None:
    workspace = make_workspace()
    config = Config(workspace=str(workspace))
    print(f"Workspace: {workspace}\n")

    print("Task 1: search the files for launch")
    result = await run_task("find launch in these files", config)
    print(result["answer"])
    print()

    print("Task 2: fetch a plain web page")
    result = await run_task("fetch https://example.com and tell me what it says", config)
    print(result["answer"])


if __name__ == "__main__":
    asyncio.run(main())
