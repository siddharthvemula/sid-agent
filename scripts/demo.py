"""Scripted end-to-end demo of SidAgent (mock provider, in-memory store).

Run from the project root:  python scripts/demo.py
The course lookup is live (umd.io); everything else is local and free.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sid_agent.agent import Agent
from sid_agent.store import Store

SCRIPT = [
    "what courses am I taking?",
    "remind me to submit the Freddie Mac thank-you by 2026-11-20",
    "log application to Acme for SWE Intern and remind me to follow up by 2026-12-01",
    "mark Acme as interview",
    "list tasks",
    "list applications",
    "look up prereqs for CMSC351",
    "remember that gym is UMD Eppley",
    "what is my gym?",
    "book me a flight to Madison",
]


def main():
    agent = Agent(store=Store(":memory:"))
    print("SidAgent demo (mock provider - no API key, no cost)")
    print("=" * 60)
    for line in SCRIPT:
        print(f"\n> {line}")
        print(agent.handle(line))
    print("\n" + "=" * 60)
    print("Demo complete. Try the CLI or the web UI - see README.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
