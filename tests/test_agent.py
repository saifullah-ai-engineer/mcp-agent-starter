"""Tests for mcp-agent-starter. Run with: PYTHONPATH=src python -m pytest -q"""

from __future__ import annotations

import asyncio
import functools
import http.server
import threading
from pathlib import Path

from mcp_agent_starter import Config, build_server, list_tool_names, run_task, tool_names
from mcp_agent_starter.tools import fetch_url, search_files


def run(coro):
    return asyncio.run(coro)


def test_registry_lists_both_tools():
    names = tool_names()
    assert "search_files_tool" in names
    assert "fetch_url_tool" in names
    assert len(names) == 2


def test_server_lists_both_tools_through_mcp():
    server = build_server(Config.default())
    names = run(list_tool_names(server))
    assert names == ["search_files_tool", "fetch_url_tool"]


def test_search_finds_by_content(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("The launch is on Monday.\n", encoding="utf-8")
    result = search_files("launch", root=str(tmp_path))
    assert "notes.txt" in result
    assert "launch" in result.lower()


def test_search_finds_by_file_name(tmp_path: Path):
    (tmp_path / "launch-plan.md").write_text("Nothing relevant here.\n", encoding="utf-8")
    result = search_files("launch-plan", root=str(tmp_path))
    assert "launch-plan.md" in result


def test_search_reports_no_matches(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("Hello world.\n", encoding="utf-8")
    result = search_files("zebra", root=str(tmp_path))
    assert "No matches" in result


def test_search_stays_inside_the_workspace(tmp_path: Path):
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("quokka-secret-word\n", encoding="utf-8")
    workspace = tmp_path / "work"
    workspace.mkdir()
    (workspace / "notes.txt").write_text("Nothing here.\n", encoding="utf-8")
    result = search_files("quokka-secret-word", root=str(workspace))
    assert "No matches" in result
    outside.unlink()


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b"<html><body><h1>Test Page</h1><p>quokka test content</p></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # noqa: D102
        pass


def _local_url() -> tuple[str, http.server.HTTPServer]:
    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{server.server_address[1]}/page", server


def test_fetch_url_returns_page_text():
    url, server = _local_url()
    try:
        result = fetch_url(url)
        assert "[200]" in result
        assert "Test Page" in result
        assert "quokka test content" in result
        assert "<h1>" not in result
    finally:
        server.shutdown()


def test_fetch_url_rejects_non_http():
    result = fetch_url("ftp://example.com/file")
    assert result.startswith("Error")


def test_agent_search_task_end_to_end(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("The launch is on Monday.\n", encoding="utf-8")
    config = Config(workspace=str(tmp_path))
    result = run(run_task("find launch in these files", config))
    assert result["plan"][0]["tool"] == "search_files_tool"
    assert "notes.txt" in result["answer"]


def test_agent_fetch_task_end_to_end():
    url, server = _local_url()
    try:
        result = run(run_task(f"fetch {url} and tell me what it says", Config.default()))
        assert result["plan"][0]["tool"] == "fetch_url_tool"
        assert "Test Page" in result["answer"]
    finally:
        server.shutdown()


def test_agent_plans_both_tools_when_task_needs_both(tmp_path: Path):
    url, server = _local_url()
    try:
        (tmp_path / "notes.txt").write_text("The launch is on Monday.\n", encoding="utf-8")
        config = Config(workspace=str(tmp_path))
        result = run(run_task(f"search for launch and fetch {url}", config))
        tools = [call["tool"] for call in result["plan"]]
        assert "fetch_url_tool" in tools
        assert "search_files_tool" in tools
        assert len(result["observations"]) == 2
    finally:
        server.shutdown()


def test_llm_hook_overrides_the_planner(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("The launch is on Monday.\n", encoding="utf-8")

    def fake_llm(task: str, names: list[str]):
        return [{"tool": "search_files_tool", "args": {"query": "Monday"}}]

    config = Config(workspace=str(tmp_path), llm_callable=fake_llm)
    result = run(run_task("anything at all", config))
    assert result["plan"][0]["args"]["query"] == "Monday"
    assert "notes.txt" in result["answer"]


def test_config_loads_from_toml(tmp_path: Path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        "[agent]\nmax_steps = 3\n\n[tools]\nworkspace = \"somewhere\"\nmax_results = 2\n",
        encoding="utf-8",
    )
    config = Config.from_file(config_file)
    assert config.max_steps == 3
    assert config.workspace == "somewhere"
    assert config.max_results == 2
    assert config.fetch_timeout_seconds == 10


def test_agent_stops_at_max_steps(tmp_path: Path):
    url, server = _local_url()
    try:
        (tmp_path / "notes.txt").write_text("The launch is on Monday.\n", encoding="utf-8")
        config = Config(workspace=str(tmp_path), max_steps=1)
        result = run(run_task(f"search for launch and fetch {url}", config))
        assert len(result["observations"]) == 1
    finally:
        server.shutdown()


def test_broken_llm_hook_falls_back_to_rule_planner(tmp_path: Path):
    (tmp_path / "notes.txt").write_text("The launch is on Monday.\n", encoding="utf-8")

    def broken_llm(task: str, names: list[str]):
        raise RuntimeError("boom")

    config = Config(workspace=str(tmp_path), llm_callable=broken_llm)
    result = run(run_task("find launch in these files", config))
    assert result["plan"][0]["tool"] == "search_files_tool"
    assert "notes.txt" in result["answer"]
