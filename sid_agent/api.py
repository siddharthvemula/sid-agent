"""FastAPI backend for SidAgent.

Run:  uvicorn sid_agent.api:app --reload --port 8000
Provider via SID_AGENT_PROVIDER (mock | claude | openai); DB via
SID_AGENT_DB (default sid_agent/data/agent.db, shared with the CLI).
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import tools as tools_mod
from .agent import Agent
from .profile import Profile
from .providers import get_provider
from .store import Store

_DEFAULT_DB = os.path.join(os.path.dirname(__file__), "data", "agent.db")


class ChatRequest(BaseModel):
    message: str


class TaskRequest(BaseModel):
    title: str
    due: str | None = None


class ApplicationRequest(BaseModel):
    company: str
    role: str


def create_app(store=None, provider=None, profile=None):
    store = store or Store(os.environ.get("SID_AGENT_DB", _DEFAULT_DB))
    provider = provider or get_provider(os.environ.get("SID_AGENT_PROVIDER", "mock"))
    profile = profile or Profile.load()
    agent = Agent(store=store, provider=provider, profile=profile)

    app = FastAPI(title="SidAgent API", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "provider": provider.name}

    @app.get("/profile")
    def get_profile():
        return profile.to_dict()

    @app.get("/tools")
    def list_tools():
        return {
            name: {"description": t["description"], "params": t["params"]}
            for name, t in tools_mod.REGISTRY.items()
        }

    @app.get("/tasks")
    def list_tasks():
        return {"open": store.list_tasks("open"), "done": store.list_tasks("done")}

    @app.post("/tasks")
    def create_task(req: TaskRequest):
        return store.create_task(req.title, req.due)

    @app.get("/applications")
    def list_applications():
        return {"applications": store.list_applications()}

    @app.post("/applications")
    def create_application(req: ApplicationRequest):
        return store.log_application(req.company, req.role)

    @app.post("/chat")
    def chat(req: ChatRequest):
        return {"reply": agent.handle(req.message)}

    return app


app = create_app()
