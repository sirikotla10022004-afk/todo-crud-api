"""
Task API — a small in-memory CRUD API built with FastAPI.

Run with:
    uvicorn main:app --reload

Then visit:
    http://localhost:8000/         -> API info
    http://localhost:8000/docs     -> Swagger UI
"""

from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A tiny in-memory CRUD API for managing a to-do list.",
)


# ---------------------------------------------------------------------------
# In-memory "database" — just a Python list. Data is lost on restart.
# ---------------------------------------------------------------------------

class Task(BaseModel):
    id: int
    title: str
    done: bool = False


tasks: List[Task] = [
    Task(id=1, title="Buy groceries", done=False),
    Task(id=2, title="Finish CRUD assignment", done=False),
    Task(id=3, title="Read FastAPI docs", done=True),
]

next_id = 4  # tracks the next free id to hand out


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    title: str = Field(..., description="Title of the new task")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="New title (optional)")
    done: Optional[bool] = Field(None, description="New done status (optional)")


# ---------------------------------------------------------------------------
# Stage 1 — root & health
# ---------------------------------------------------------------------------

@app.get("/", summary="API info")
def read_root():
    """Describes the API and lists its main endpoints."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks", "/tasks/{id}", "/health", "/stats", "/reset"],
    }


@app.get("/health", summary="Health check")
def health_check():
    """Simple health check — used to confirm the server is alive."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Stage 2 — Read
# ---------------------------------------------------------------------------

@app.get("/tasks", summary="List tasks (optionally filter/search)")
def list_tasks(
    done: Optional[bool] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
):
    """
    Returns all tasks.

    Optional query parameters:
    - done: filter by completion status (true/false)
    - search: only return tasks whose title contains this text
    - limit / offset: simple pagination
    """
    result = tasks

    if done is not None:
        result = [t for t in result if t.done == done]

    if search is not None:
        result = [t for t in result if search.lower() in t.title.lower()]

    if offset:
        result = result[offset:]
    if limit is not None:
        result = result[:limit]

    return result


@app.get("/tasks/{task_id}", summary="Get a single task")
def get_task(task_id: int):
    """Returns one task by id, or 404 if it doesn't exist."""
    for t in tasks:
        if t.id == task_id:
            return t
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


# ---------------------------------------------------------------------------
# Stage 3 — Create
# ---------------------------------------------------------------------------

@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(payload: TaskCreate):
    """Creates a new task. Requires a non-empty 'title'."""
    global next_id

    title = payload.title.strip() if payload.title else ""
    if not title:
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")

    new_task = Task(id=next_id, title=title, done=False)
    tasks.append(new_task)
    next_id += 1
    return new_task


# ---------------------------------------------------------------------------
# Stage 4 — Update & Delete
# ---------------------------------------------------------------------------

@app.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, payload: TaskUpdate):
    """
    Updates a task's title and/or done status.
    Unknown id -> 404. Empty/invalid title (if provided) -> 400.
    """
    for t in tasks:
        if t.id == task_id:
            if payload.title is not None:
                new_title = payload.title.strip()
                if not new_title:
                    raise HTTPException(status_code=400, detail="title cannot be empty")
                t.title = new_title
            if payload.done is not None:
                t.done = payload.done
            return t
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    """Deletes a task. Unknown id -> 404. Returns 204 with no body on success."""
    for i, t in enumerate(tasks):
        if t.id == task_id:
            tasks.pop(i)
            return JSONResponse(status_code=204, content=None)
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


# ---------------------------------------------------------------------------
# ★ Extras
# ---------------------------------------------------------------------------

@app.get("/stats", summary="Task statistics")
def get_stats():
    """Returns counts of total/done/open tasks."""
    total = len(tasks)
    done_count = len([t for t in tasks if t.done])
    return {"total": total, "done": done_count, "open": total - done_count}


@app.post("/reset", summary="Reset to example tasks")
def reset_tasks():
    """Restores the 3 example tasks. Handy for demos."""
    global tasks, next_id
    tasks = [
        Task(id=1, title="Buy groceries", done=False),
        Task(id=2, title="Finish CRUD assignment", done=False),
        Task(id=3, title="Read FastAPI docs", done=True),
    ]
    next_id = 4
    return {"message": "Tasks reset to example data", "tasks": tasks}
