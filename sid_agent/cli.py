"""Command-line interface for SidAgent.

Usage:
  python -m sid_agent.cli "remind me to submit the form by 2026-11-20"
  python -m sid_agent.cli            # interactive mode

Provider is chosen with SID_AGENT_PROVIDER (mock | claude | openai);
the database lives at sid_agent/data/agent.db by default.
"""
import os
import sys

from .agent import Agent
from .providers import get_provider
from .store import Store

_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "agent.db")


def build_agent():
    provider = get_provider(os.environ.get("SID_AGENT_PROVIDER", "mock"))
    return Agent(store=Store(_DB_PATH), provider=provider)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    agent = build_agent()
    if argv:
        print(agent.handle(" ".join(argv)))
        return 0
    print("SidAgent (Stage 1, mock provider). Type 'quit' to exit.")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in {"quit", "exit"}:
            break
        if text:
            print(agent.handle(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
