# mcp-agent-starter

A production-shaped LangGraph plus MCP agent template. Fork it, add your own tools, and you have a working agent instead of a blank file.

Built by Saif Ullah, Agentic AI Engineer at TechAurah.

## What it does

You give the agent one task in plain words. It plans which tools to call, calls them through a real MCP server, and answers from what the tools returned.

The graph has three steps:

```
plan -> act -> act -> ... -> answer
```

1. **Plan**: decide which tools to call, in order. The built-in planner is a small rule based planner, no LLM and no paid API. If you plug in an LLM, the planner asks it instead.
2. **Act**: call the next planned tool through the MCP server and record the result. It loops until the plan is done or `max_steps` is hit.
3. **Answer**: write a short answer from the observations.

## The two built-in tools

| Tool | What it does |
| --- | --- |
| `search_files_tool` | Searches file names and file contents under the workspace. Never reads outside the workspace, skips hidden folders and virtual environments, and skips files over 200 KB. |
| `fetch_url_tool` | Fetches a plain http or https URL and returns its readable text. No API key needed. |

Both tools are real MCP tools, registered on a genuine MCP server from the official MCP Python SDK (mcp 2.3.0, `MCPServer`). The agent calls them through `server.call_tool`, never by calling the functions directly, so the MCP boundary is real.

## 30 second demo

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python examples/demo.py
```

That runs with no API key and no cost. It builds a small workspace, searches it for the word "launch", and fetches https://example.com. You will see something like this:

```text
Task 1: search the files for launch
Task: find launch in these files
- search_files_tool: notes.txt: Launch plan plan.md: - Write the launch notes.

Task 2: fetch a plain web page
Task: fetch https://example.com and tell me what it says
- fetch_url_tool: [200] text/html; charset=utf-8 Example Domain This domain is for use in documentation examples without needing permission.
```

Run it on your own task from the command line:

```bash
python -m mcp_agent_starter "find launch in these files" --workspace .
python -m mcp_agent_starter "fetch https://example.com and tell me what it says"
```

Or use it from your own code:

```python
import asyncio
from mcp_agent_starter import Config, run_task

result = asyncio.run(run_task("find launch in these files", Config(workspace=".")))
print(result["answer"])
```

## How to add a tool

Three steps, in three files:

1. Write the function in `src/mcp_agent_starter/tools.py`.
2. Register it on the MCP server in `src/mcp_agent_starter/server.py` with `@server.tool()`.
3. Add its name and a one-line description to `TOOLS` in `src/mcp_agent_starter/registry.py`.

The agent plans from the registry, so a tool that is not listed there will never be picked. That is deliberate: one place controls what the agent may use.

## Config

Copy `config.toml` and change the values, then pass `--config config.toml` to the CLI. Every key has a safe default, so the file is optional.

```toml
[agent]
max_steps = 6

[tools]
workspace = "."
max_results = 5
fetch_timeout_seconds = 10
fetch_max_chars = 4000
```

## Plug in an LLM (optional, off by default)

The agent works with no LLM at all. If you want one, pass a callable in the config that takes `(task, tool_names)` and returns a list of `{"tool": ..., "args": ...}`. If the callable raises, the agent falls back to the rule based planner.

```python
from mcp_agent_starter import Config, run_task

def my_llm(task, tool_names):
    return [{"tool": "search_files_tool", "args": {"query": task}}]

config = Config(workspace=".", llm_callable=my_llm)
```

## Tests

```bash
pip install pytest
PYTHONPATH=src python -m pytest -q
```

The 15 tests cover the tool registry, the MCP server listing, file search inside and outside the workspace, web fetch against a local test server, end to end runs for search, fetch, and both tools together, the LLM hook, config loading, the step limit, and the fallback when a broken LLM hook raises.

## Honest limits

- The default planner is rule based, not an LLM. It understands tasks that mention a URL or a search word. A vague task gets a file search with the whole task as the query, which is a reasonable guess, not intelligence.
- The file search reads plain text files. It does not parse PDFs, images, or binary files.
- The web fetch returns the readable text of a page. It does not run JavaScript, so pages that need a browser will come back thin.
- There are no measured results behind this project. No stars, users, client results, or revenue are claimed here, because none have been measured.
