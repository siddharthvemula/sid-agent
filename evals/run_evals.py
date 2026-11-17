"""Eval runner for SidAgent.

Runs every scenario in eval_questions.json against a fresh in-memory store
with the mock provider, and checks:
  - the exact ordered list of tools the agent called,
  - substrings the final response must / must not contain,
  - final store state (open/done task counts, application count + statuses,
    memory values).

Network items (live umd.io lookups) report SKIP instead of FAIL when the
lookup errors out. Exit code 0 only when nothing FAILs.

Usage (from the project root):
    python -m evals.run_evals
    python evals/run_evals.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sid_agent import tools as tools_mod  # noqa: E402
from sid_agent.agent import Agent  # noqa: E402
from sid_agent.store import Store  # noqa: E402

_EVAL_FILE = os.path.join(os.path.dirname(__file__), "eval_questions.json")


class RecordingAgent(Agent):
    """Agent that records the tools it executes, for assertions."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tools_called = []

    def handle(self, user_text):
        original = tools_mod.call_tool

        def recording(ctx, name, args):
            self.tools_called.append(name)
            return original(ctx, name, args)

        tools_mod.call_tool = recording
        try:
            return super().handle(user_text)
        finally:
            tools_mod.call_tool = original


def check_item(item):
    """Return (status, detail): status in PASS / FAIL / SKIP."""
    expect = item.get("expect", {})
    agent = RecordingAgent(store=Store(":memory:"))
    final_response = ""
    try:
        for step in item["steps"]:
            final_response = agent.handle(step)
    except Exception as exc:
        return ("SKIP" if expect.get("network") else "FAIL"), f"exception: {exc}"

    if expect.get("network") and (
        "failed" in final_response or "can't do that yet" in final_response
    ):
        return "SKIP", "network lookup unavailable"

    problems = []
    if "tools" in expect and agent.tools_called != expect["tools"]:
        problems.append(f"tools {agent.tools_called} != expected {expect['tools']}")
    if "response_contains" in expect and expect["response_contains"] not in final_response:
        problems.append(f"response missing {expect['response_contains']!r}: {final_response!r}")
    if "response_not_contains" in expect and expect["response_not_contains"] in final_response:
        problems.append(f"response must not contain {expect['response_not_contains']!r}")
    store = agent.store
    if "tasks_open" in expect and len(store.list_tasks("open")) != expect["tasks_open"]:
        problems.append(f"open tasks {len(store.list_tasks('open'))} != {expect['tasks_open']}")
    if "tasks_done" in expect and len(store.list_tasks("done")) != expect["tasks_done"]:
        problems.append(f"done tasks {len(store.list_tasks('done'))} != {expect['tasks_done']}")
    if "applications" in expect and len(store.list_applications()) != expect["applications"]:
        problems.append(f"applications {len(store.list_applications())} != {expect['applications']}")
    for company, status in (expect.get("app_status") or {}).items():
        match = [a for a in store.list_applications() if a["company"] == company]
        if not match or match[0]["status"] != status:
            problems.append(f"application {company} status != {status!r}")
    for key, value in (expect.get("memory") or {}).items():
        if store.recall_memory(key)["value"] != value:
            problems.append(f"memory {key!r} != {value!r}")
    return ("FAIL", "; ".join(problems)) if problems else ("PASS", "")


def main():
    with open(_EVAL_FILE, "r", encoding="utf-8") as f:
        suite = json.load(f)
    counts = {"PASS": 0, "FAIL": 0, "SKIP": 0}
    for item in suite["items"]:
        status, detail = check_item(item)
        counts[status] += 1
        line = f"{status}  {item['id']}"
        if detail:
            line += f"  -- {detail}"
        print(line)
    total = sum(counts.values())
    print(
        f"\n{counts['PASS']}/{total} passed, "
        f"{counts['FAIL']} failed, {counts['SKIP']} skipped"
    )
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
