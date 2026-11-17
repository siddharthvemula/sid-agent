"""Tool registry for SidAgent.

An agent is only as good as its tools. Each tool is a small function with a
declared schema (used by LLM providers in Stage 2 to offer function calls).
Stage 1 tools are action-first: they *do* things in the store, look up live
course data, and read the profile - they never send or submit anything.
"""
import json
import re
import urllib.request

_COURSE_CODE_RE = re.compile(r"\b[A-Z]{4}\d{3}[A-Z]?\b")


def parse_prereqs(prereq_text):
    """Extract course codes from a free-text prerequisite string."""
    if not prereq_text:
        return []
    seen, out = set(), []
    for code in _COURSE_CODE_RE.findall(prereq_text):
        if code not in seen:
            seen.add(code)
            out.append(code)
    return out


def course_lookup(course_id):
    """Live lookup against the public umd.io API."""
    url = f"https://api.umd.io/v1/courses/{course_id.upper()}"
    req = urllib.request.Request(url, headers={"User-Agent": "sid-agent/0.1"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data:
        return {"course_id": course_id.upper(), "found": False}
    c = data[0]
    prereq_text = (c.get("relationships") or {}).get("prereqs")
    return {
        "course_id": c["course_id"],
        "found": True,
        "name": c.get("name"),
        "credits": c.get("credits"),
        "prereqs_text": prereq_text,
        "prereq_courses": parse_prereqs(prereq_text),
    }


# -- tool functions (signature: fn(ctx, **args) -> dict) --------------------

def _create_task(ctx, title, due=None):
    return ctx["store"].create_task(title, due)


def _list_tasks(ctx, status="open"):
    return {"tasks": ctx["store"].list_tasks(status)}


def _complete_task(ctx, task_id):
    return ctx["store"].complete_task(int(task_id))


def _log_application(ctx, company, role, notes=None):
    return ctx["store"].log_application(company, role, notes=notes)


def _list_applications(ctx):
    return {"applications": ctx["store"].list_applications()}


def _update_application(ctx, company, status):
    return ctx["store"].update_application(company, status)


def _course_lookup(ctx, course_id):
    return course_lookup(course_id)


def _get_profile(ctx, field=None):
    profile = ctx["profile"]
    if field:
        return {"field": field, "value": profile.get(field)}
    return {"profile": profile.to_dict()}


def _add_memory(ctx, key, value):
    return ctx["store"].add_memory(key, value)


def _recall_memory(ctx, key):
    return ctx["store"].recall_memory(key)


REGISTRY = {
    "create_task": {
        "fn": _create_task,
        "description": "Create a task/reminder, optionally with a due date (YYYY-MM-DD).",
        "params": {"title": "string", "due": "string|null"},
    },
    "list_tasks": {
        "fn": _list_tasks,
        "description": "List tasks by status (default: open).",
        "params": {"status": "string"},
    },
    "complete_task": {
        "fn": _complete_task,
        "description": "Mark a task done by its id.",
        "params": {"task_id": "integer"},
    },
    "log_application": {
        "fn": _log_application,
        "description": "Log an internship application (company, role).",
        "params": {"company": "string", "role": "string"},
    },
    "list_applications": {
        "fn": _list_applications,
        "description": "List all logged internship applications.",
        "params": {},
    },
    "update_application": {
        "fn": _update_application,
        "description": "Update an application's status by company name.",
        "params": {"company": "string", "status": "string"},
    },
    "course_lookup": {
        "fn": _course_lookup,
        "description": "Look up a UMD course and its prerequisites (live, umd.io).",
        "params": {"course_id": "string"},
    },
    "get_profile": {
        "fn": _get_profile,
        "description": "Read a field from Sid's public profile (or the whole profile).",
        "params": {"field": "string|null"},
    },
    "add_memory": {
        "fn": _add_memory,
        "description": "Remember a fact under a key.",
        "params": {"key": "string", "value": "string"},
    },
    "recall_memory": {
        "fn": _recall_memory,
        "description": "Recall a remembered fact by key.",
        "params": {"key": "string"},
    },
}


def call_tool(ctx, name, args):
    if name not in REGISTRY:
        return {"error": f"unknown tool: {name}"}
    return REGISTRY[name]["fn"](ctx, **(args or {}))
