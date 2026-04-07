"""
CodeReviewEnv — FastAPI Server
Exposes OpenEnv API: /reset, /step, /state, /tasks
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional
import uvicorn
import sys
from pathlib import Path

# Add parent directory to path to import environment and tasks
sys.path.insert(0, str(Path(__file__).parent.parent))

from environment import CodeReviewEnv, Action
from tasks import TASKS

app = FastAPI(
    title="CodeReviewEnv",
    description="An OpenEnv environment where AI agents review code snippets for bugs and issues.",
    version="1.0.0"
)

# Store active environments per session (simple in-memory)
_envs: Dict[str, CodeReviewEnv] = {}


def get_env(task_name: str) -> CodeReviewEnv:
    if task_name not in _envs:
        _envs[task_name] = CodeReviewEnv(task_name)
    return _envs[task_name]


# ── Request Models ────────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_name: Optional[str] = "easy_bug"


class StepRequest(BaseModel):
    task_name: Optional[str] = "easy_bug"
    review: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "CodeReviewEnv",
        "description": "OpenEnv environment for AI code review agents",
        "tasks": list(TASKS.keys()),
        "endpoints": ["/reset", "/step", "/state", "/tasks", "/health"]
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
def reset(request: Optional[ResetRequest] = Body(None)):
    """Reset the environment for a given task."""
    task_name = request.task_name if request else "easy_bug"
    if task_name not in TASKS:
        raise HTTPException(status_code=400, detail=f"Unknown task: {task_name}")
    env = CodeReviewEnv(task_name)
    _envs[task_name] = env
    obs = env.reset()
    return obs.model_dump()


@app.post("/step")
def step(request: Optional[StepRequest] = Body(None)):
    """Submit a code review action."""
    if not request:
        raise HTTPException(status_code=400, detail="request body required with review field")
    if request.task_name not in TASKS:
        raise HTTPException(status_code=400, detail=f"Unknown task: {request.task_name}")

    env = get_env(request.task_name)
    action = Action(review=request.review)
    obs, reward, done, info = env.step(action)

    return {
        "observation": obs.model_dump(),
        "reward": reward.model_dump(),
        "done": done,
        "info": info
    }


@app.get("/state")
def state(task_name: str = "easy_bug"):
    """Get current environment state."""
    env = get_env(task_name)
    return env.state().model_dump()


@app.get("/tasks")
def list_tasks():
    """List all available tasks with descriptions."""
    return {
        name: {
            "difficulty": task["difficulty"],
            "description": task["description"],
            "max_steps": task["max_steps"]
        }
        for name, task in TASKS.items()
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)
