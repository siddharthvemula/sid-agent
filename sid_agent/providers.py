"""LLM provider interface for SidAgent (provider-flexible by design).

Architecture: plan -> execute -> compose.
  1. plan(user_text, tool_schemas) -> ProviderPlan: the provider either
     requests tool calls or answers directly (text).
  2. The agent executes the tools itself (providers never touch the store).
  3. compose(user_text, results) -> optional natural-language reply built
     ONLY from the tool results (fact-lock). Providers that return None
     fall back to the agent's deterministic formatter.

The mock provider is deterministic (dev/tests/demos, no key, no cost).
Claude and OpenAI adapters speak raw HTTPS via an injectable transport, so
they are unit-testable without a key and need no vendor SDK.
"""
import json
import os
import re
import urllib.request
from dataclasses import dataclass, field as dc_field

SYSTEM_PROMPT = (
    "You are SidAgent, a personal assistant for Sid Vemula. You act through "
    "tools: prefer calling a tool over answering from memory. Never invent "
    "facts about Sid - use get_profile or the other tools. When composing a "
    "reply from tool results, use ONLY those results."
)


@dataclass
class ToolCall:
    name: str
    arguments: dict = dc_field(default_factory=dict)


@dataclass
class ProviderPlan:
    tool_calls: list = dc_field(default_factory=list)
    text: str = None


def urllib_post(url, headers, payload):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def to_json_schema(params):
    """Convert the registry's loose param types to a JSON schema object."""
    props = {}
    for key, t in (params or {}).items():
        if t == "integer":
            props[key] = {"type": "integer"}
        elif t == "string|null":
            props[key] = {"type": ["string", "null"]}
        else:
            props[key] = {"type": "string"}
    return {"type": "object", "properties": props}


class LLMProvider:
    name = "base"

    def plan(self, user_text, tool_schemas):
        raise NotImplementedError

    def compose(self, user_text, results):
        return None


class MockProvider(LLMProvider):
    """Deterministic intent patterns - for development, demos, and tests.

    Understands single intents plus compound requests joined by " and "
    (planned as multiple tool calls, executed in order by the agent).
    """

    name = "mock"

    # (substring triggers, profile field) checked in order.
    _PROFILE_TRIGGERS = [
        (("what courses", "my courses"), "fall_2026_courses"),
        (("my major", "what degree"), "degree"),
        (("when do i graduate", "graduation"), "graduation"),
        (("what school", "where do i go"), "school"),
        (("my goals", "what are my goals"), "goals"),
        (("my projects", "what projects"), "projects"),
        (("my skills", "what skills"), "skills"),
        (("my experience", "work experience"), "experience"),
        (("my name", "who am i"), "name"),
        (("internship targets", "targeting"), "internship_targets"),
        (("ap credits", "ap credit"), "ap_credits"),
    ]

    def plan(self, user_text, tool_schemas):
        # Compound first: greedy single patterns would otherwise swallow a
        # second clause into an argument (e.g. the role in "log application
        # to Acme for SWE Intern and remind me to ..."). The split is only
        # used when EVERY clause parses as an intent, so a title that merely
        # contains "and" ("buy milk and eggs") still falls through to the
        # single-intent match below.
        if " and " in user_text.lower():
            clauses = re.split(r"\s+and\s+", user_text.strip(), flags=re.IGNORECASE)
            if len(clauses) > 1:
                calls = []
                for clause in clauses:
                    sub = self._plan_single(clause)
                    if not sub.tool_calls:
                        calls = None
                        break
                    calls.extend(sub.tool_calls)
                if calls:
                    return ProviderPlan(calls)
        return self._plan_single(user_text)

    def _plan_single(self, user_text):
        text = user_text.strip()
        low = text.lower()

        m = re.match(r"remind me to (.+?)(?:\s+by\s+(\d{4}-\d{2}-\d{2}))?$", low)
        if m:
            return ProviderPlan([ToolCall("create_task", {"title": m.group(1), "due": m.group(2)})])

        m = re.match(r"log application to (.+?) for (.+)$", text, re.IGNORECASE)
        if m:
            return ProviderPlan([ToolCall("log_application", {"company": m.group(1), "role": m.group(2)})])

        m = re.match(r"(?:mark|complete) task (\d+)(?: as)? done$", low)
        if m:
            return ProviderPlan([ToolCall("complete_task", {"task_id": int(m.group(1))})])

        m = re.match(r"mark (.+?) as (.+)$", text, re.IGNORECASE)
        if m:
            return ProviderPlan([ToolCall(
                "update_application", {"company": m.group(1), "status": m.group(2)}
            )])

        for triggers, field in self._PROFILE_TRIGGERS:
            if any(t in low for t in triggers):
                return ProviderPlan([ToolCall("get_profile", {"field": field})])

        if low.startswith("remember that"):
            body = text[len("remember that"):].strip()
            if " is " in body:
                key, value = body.split(" is ", 1)
                return ProviderPlan([ToolCall("add_memory", {"key": key.strip(), "value": value.strip()})])
        m = re.match(r"what is my (.+?)\?$", low)
        if m:
            return ProviderPlan([ToolCall("recall_memory", {"key": m.group(1)})])
        if "list" in low and "task" in low:
            return ProviderPlan([ToolCall("list_tasks", {})])
        if "list" in low and "application" in low:
            return ProviderPlan([ToolCall("list_applications", {})])
        m = re.search(r"\b([A-Z]{4}\d{3}[A-Z]?)\b", text)
        if m and ("prereq" in low or "look up" in low or "lookup" in low):
            return ProviderPlan([ToolCall("course_lookup", {"course_id": m.group(1)})])
        return ProviderPlan()


class ClaudeProvider(LLMProvider):
    """Anthropic Messages API adapter with tool use (raw HTTPS, no SDK)."""

    name = "claude"
    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key=None, model="claude-sonnet-4-5", http_post=None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.http_post = http_post or urllib_post

    def _headers(self):
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set - cannot use the Claude provider.")
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}

    @staticmethod
    def _tools(tool_schemas):
        return [
            {"name": name, "description": t["description"], "input_schema": to_json_schema(t["params"])}
            for name, t in tool_schemas.items()
        ]

    def plan(self, user_text, tool_schemas):
        payload = {
            "model": self.model,
            "max_tokens": 1024,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_text}],
            "tools": self._tools(tool_schemas),
        }
        resp = self.http_post(self.API_URL, self._headers(), payload)
        calls, texts = [], []
        for block in resp.get("content", []):
            if block.get("type") == "tool_use":
                calls.append(ToolCall(block["name"], block.get("input") or {}))
            elif block.get("type") == "text":
                texts.append(block.get("text", ""))
        return ProviderPlan(calls, "\n".join(texts).strip() or None)

    def compose(self, user_text, results):
        payload = {
            "model": self.model,
            "max_tokens": 512,
            "system": SYSTEM_PROMPT,
            "messages": [{
                "role": "user",
                "content": (
                    f"The user asked: {user_text}\n"
                    f"Tool results (JSON): {json.dumps(results)}\n"
                    "Write the final reply using ONLY these results. Be concise."
                ),
            }],
        }
        resp = self.http_post(self.API_URL, self._headers(), payload)
        texts = [b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text"]
        return "\n".join(texts).strip() or None


class OpenAIProvider(LLMProvider):
    """OpenAI Chat Completions adapter with function calling (raw HTTPS)."""

    name = "openai"
    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key=None, model="gpt-5", http_post=None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.http_post = http_post or urllib_post

    def _headers(self):
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not set - cannot use the OpenAI provider.")
        return {"Authorization": f"Bearer {self.api_key}"}

    @staticmethod
    def _tools(tool_schemas):
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": t["description"],
                    "parameters": to_json_schema(t["params"]),
                },
            }
            for name, t in tool_schemas.items()
        ]

    def plan(self, user_text, tool_schemas):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            "tools": self._tools(tool_schemas),
        }
        resp = self.http_post(self.API_URL, self._headers(), payload)
        message = resp["choices"][0]["message"]
        calls = []
        for tc in message.get("tool_calls") or []:
            fn = tc["function"]
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            calls.append(ToolCall(fn["name"], args))
        return ProviderPlan(calls, (message.get("content") or "").strip() or None)

    def compose(self, user_text, results):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"The user asked: {user_text}\n"
                        f"Tool results (JSON): {json.dumps(results)}\n"
                        "Write the final reply using ONLY these results. Be concise."
                    ),
                },
            ],
        }
        resp = self.http_post(self.API_URL, self._headers(), payload)
        text = resp["choices"][0]["message"].get("content")
        return text.strip() if text else None


def get_provider(name="mock", **kwargs):
    providers = {"mock": MockProvider, "claude": ClaudeProvider, "openai": OpenAIProvider}
    if name not in providers:
        raise ValueError(f"unknown provider: {name} (choose from {sorted(providers)})")
    return providers[name](**kwargs)
