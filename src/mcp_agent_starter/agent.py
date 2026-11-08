"""The agent, built as a real LangGraph state graph.

Flow:
  plan -> act -> act -> ... -> answer -> end

  plan:   decide which tools to call, in order. By default a small rule
          based planner does this, no LLM and no paid API. If a config
          carries an llm_callable, the planner asks it instead.
  act:    call the next planned tool through the MCP server, record what
          came back, and loop until the plan is done or max_steps is hit.
  answer: write a short answer from the observations.

State is a plain dict so each node stays small and easy to test.
"""

from __future__ import annotations

import re
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .config import Config
from .registry import TOOLS, tool_names
from .server import build_server, call_tool

URL_PATTERN = re.compile(r"https?://\S+")
SEARCH_WORDS = ("search", "find", "look for", "where is", "which file")


class AgentState(TypedDict, total=False):
    task: str
    plan: list[dict[str, Any]]
    step: int
    observations: list[dict[str, str]]
    answer: str


TRAILING_FILLER = (
    "in these files",
    "in the files",
    "in this folder",
    "in the folder",
    "in these docs",
)


def _clean_search_query(task: str) -> str:
    """Turn a task into a file search query: drop URLs, drop lead-in verbs
    and trailing filler such as "in these files"."""
    text = URL_PATTERN.sub("", task).strip()
    lowered = text.lower()
    for lead in ("search for", "look for", "find in files", "find", "search"):
        if lowered.startswith(lead):
            text = text[len(lead):].strip(" :")
            lowered = text.lower()
            break
    for filler in TRAILING_FILLER:
        if lowered.endswith(filler):
            text = text[: -len(filler)].strip(" :")
            break
    text = text.strip(" .?\"'")
    return text or task


def _rule_plan(task: str) -> list[dict[str, Any]]:
    """The default planner. No LLM, no cost, fully deterministic."""
    plan: list[dict[str, Any]] = []
    lowered = task.lower()
    for url in URL_PATTERN.findall(task):
        plan.append({"tool": "fetch_url_tool", "args": {"url": url.rstrip(".,)")}})
    if any(word in lowered for word in SEARCH_WORDS):
        query = _clean_search_query(task)
        plan.append({"tool": "search_files_tool", "args": {"query": query}})
    if not plan:
        plan.append({"tool": "search_files_tool", "args": {"query": task.strip()}})
    return plan


def build_graph(config: Config | None = None):
    """Compile the agent graph. The MCP server is built once, per run."""
    config = config or Config.default()
    server = build_server(config)

    def plan_node(state: AgentState) -> AgentState:
        task = state["task"]
        if config.llm_callable is not None:
            try:
                raw = config.llm_callable(task, tool_names())
                plan = [
                    {"tool": item["tool"], "args": item.get("args", {})}
                    for item in raw
                    if item.get("tool") in TOOLS
                ]
            except Exception:  # noqa: BLE001 - a broken hook falls back
                plan = _rule_plan(task)
        else:
            plan = _rule_plan(task)
        return {"plan": plan, "step": 0, "observations": []}

    def act_node(state: AgentState) -> AgentState:
        step = state["step"]
        call = state["plan"][step]
        result = call_tool(server, call["tool"], call["args"])
        observation = {
            "tool": call["tool"],
            "args": str(call["args"]),
            "result": result,
        }
        return {
            "step": step + 1,
            "observations": [*state["observations"], observation],
        }

    def answer_node(state: AgentState) -> AgentState:
        lines = [f"Task: {state['task']}"]
        if not state["observations"]:
            lines.append("No tool was called, so there is nothing to report.")
        for obs in state["observations"]:
            flat = " ".join(obs["result"].split()) if obs["result"] else "(empty)"
            lines.append(f"- {obs['tool']}: {flat[:160]}")
        return {"answer": "\n".join(lines)}

    def more_steps(state: AgentState) -> str:
        if state["step"] < len(state["plan"]) and state["step"] < config.max_steps:
            return "act"
        return "answer"

    graph = StateGraph(AgentState)
    graph.add_node("plan", plan_node)
    graph.add_node("act", act_node)
    graph.add_node("answer", answer_node)
    graph.set_entry_point("plan")
    graph.add_edge("plan", "act")
    graph.add_conditional_edges("act", more_steps, {"act": "act", "answer": "answer"})
    graph.add_edge("answer", END)
    return graph.compile()


async def run_task(task: str, config: Config | None = None) -> dict[str, Any]:
    """Run one task end to end and return the plan, observations, and answer."""
    config = config or Config.default()
    graph = build_graph(config)
    result = await graph.ainvoke({"task": task})
    return {
        "task": task,
        "plan": result.get("plan", []),
        "observations": result.get("observations", []),
        "answer": result.get("answer", ""),
    }
