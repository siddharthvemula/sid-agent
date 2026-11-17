"""Agent loop for SidAgent: plan tool calls, execute them, report results.

Fact-lock rule: the agent only reports what a tool returned. If no tool
matches a request, it says so plainly instead of improvising.
"""
from . import tools as tools_mod
from .profile import Profile
from .providers import get_provider
from .store import Store


class Agent:
    def __init__(self, store=None, provider=None, profile=None):
        self.store = store or Store()
        self.provider = provider or get_provider("mock")
        self.profile = profile or Profile.load()
        self.ctx = {"store": self.store, "profile": self.profile}

    def handle(self, user_text):
        plan = self.provider.plan(user_text, tools_mod.REGISTRY)
        if not plan.tool_calls:
            if plan.text:
                return plan.text
            return (
                "I can't do that yet - no tool matches that request. "
                "Stage 1 understands: 'remind me to ... by YYYY-MM-DD', "
                "'log application to <Company> for <Role>', 'list tasks', "
                "'list applications', 'what courses am I taking', "
                "'remember that <key> is <value>', 'look up prereqs for <COURSE>'."
            )
        executed = []
        for call in plan.tool_calls:
            try:
                result = tools_mod.call_tool(self.ctx, call.name, call.arguments)
            except Exception as exc:  # e.g. a live lookup failing offline
                result = {"error": f"{call.name} failed: {exc}"}
            executed.append({"tool": call.name, "result": result})
        composed = self.provider.compose(user_text, executed)
        if composed:
            return composed
        return "\n".join(
            self._format(e["tool"], e["result"]) for e in executed
        )

    @staticmethod
    def _format(name, result):
        if "error" in result:
            return f"Error: {result['error']}"
        if name == "create_task":
            due = f" (due {result['due']})" if result.get("due") else ""
            return f"Done - task #{result['id']} created: '{result['title']}'{due}."
        if name == "list_tasks":
            tasks = result["tasks"]
            if not tasks:
                return "No open tasks."
            lines = ["Open tasks:"]
            for t in tasks:
                due = f" - due {t['due']}" if t.get("due") else ""
                lines.append(f"  #{t['id']} {t['title']}{due}")
            return "\n".join(lines)
        if name == "complete_task":
            return f"Task #{result['id']} marked done." if result["updated"] else "No such task."
        if name == "log_application":
            return (
                f"Logged application: {result['company']} - {result['role']} "
                f"(status: {result['status']})."
            )
        if name == "list_applications":
            apps = result["applications"]
            if not apps:
                return "No applications logged yet."
            lines = ["Applications:"]
            for a in apps:
                lines.append(f"  {a['company']} - {a['role']} [{a['status']}]")
            return "\n".join(lines)
        if name == "update_application":
            return f"Updated {result['updated']} application(s) for {result['company']} -> {result['status']}."
        if name == "course_lookup":
            if not result.get("found"):
                return f"No course found for {result['course_id']}."
            prereqs = ", ".join(result["prereq_courses"]) or "none listed"
            return (
                f"{result['course_id']} - {result['name']} ({result['credits']} credits). "
                f"Prerequisites: {prereqs}. Full text: {result['prereqs_text']}"
            )
        if name == "get_profile":
            if "profile" in result:
                return str(result["profile"])
            value = result["value"]
            if isinstance(value, list):
                return "\n".join(f"  - {v}" for v in value)
            return f"{result['field']}: {value}"
        if name == "add_memory":
            return f"Remembered: {result['key']} = {result['value']}."
        if name == "recall_memory":
            if result["value"] is None:
                return f"I don't have anything stored for '{result['key']}'."
            return f"{result['key']}: {result['value']}"
        return str(result)
