"""
Task API — same CRUD API as before, now backed by a real SQLite database.

Run with:
    uvicorn main:app --reload

Then visit:
    http://localhost:8000/         -> API info
    http://localhost:8000/docs     -> Swagger UI

The database file tasks.db is created automatically in this same folder
the first time the app runs. Nothing about the API itself changed from
the in-memory version — only where the data lives.
"""

import sqlite3
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Task API",
    version="2.0",
    description="A CRUD API for managing a to-do list, backed by SQLite.",
)

DB_FILE = "tasks.db"


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def get_connection():
    """Opens a new connection to the SQLite database file."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """
    Creates the tasks table if it doesn't exist, and seeds it with
    3 example tasks — but ONLY if the table is currently empty, so
    restarting the app never duplicates the seed data.
    """
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            done BOOLEAN NOT NULL DEFAULT 0
        )
        """
    )
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            [
                ("Buy groceries", False),
                ("Finish CRUD assignment", False),
                ("Read FastAPI docs", True),
            ],
        )
        conn.commit()

    conn.close()


@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class Task(BaseModel):
    id: int
    title: str
    done: bool


class TaskCreate(BaseModel):
    title: str = Field(..., description="Title of the new task")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, description="New title (optional)")
    done: Optional[bool] = Field(None, description="New done status (optional)")


def row_to_task(row: sqlite3.Row) -> Task:
    return Task(id=row["id"], title=row["title"], done=bool(row["done"]))


# ---------------------------------------------------------------------------
# Stage 1 (from A1) — root & health
# ---------------------------------------------------------------------------

@app.get("/", summary="API info")
def read_root():
    return {
        "name": "Task API",
        "version": "2.0",
        "storage": "SQLite (tasks.db)",
        "endpoints": ["/tasks", "/tasks/{id}", "/health", "/stats"],
    }


@app.get("/health", summary="Health check")
def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

@app.get("/tasks", response_model=List[Task], summary="List tasks (optionally filter/search)")
def list_tasks(
    done: Optional[bool] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
):
    """
    Returns all tasks from the database.

    Optional query parameters:
    - done: filter by completion status (true/false) -> SQL WHERE
    - search: only tasks whose title contains this text -> SQL LIKE
    - limit / offset: simple pagination
    """
    conn = get_connection()

    query = "SELECT * FROM tasks WHERE 1=1"
    params: list = []

    if done is not None:
        query += " AND done = ?"
        params.append(int(done))

    if search is not None:
        query += " AND title LIKE ?"
        params.append(f"%{search}%")

    query += " ORDER BY id"

    if limit is not None:
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
    elif offset:
        query += " LIMIT -1 OFFSET ?"
        params.append(offset)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [row_to_task(r) for r in rows]


@app.get("/tasks/{task_id}", response_model=Task, summary="Get a single task")
def get_task(task_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return row_to_task(row)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@app.post("/tasks", response_model=Task, status_code=201, summary="Create a new task")
def create_task(payload: TaskCreate):
    title = payload.title.strip() if payload.title else ""
    if not title:
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")

    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)", (title, False)
    )
    conn.commit()
    new_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return row_to_task(row)


# ---------------------------------------------------------------------------
# Update & Delete
# ---------------------------------------------------------------------------

@app.put("/tasks/{task_id}", response_model=Task, summary="Update a task")
def update_task(task_id: int, payload: TaskUpdate):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    new_title = row["title"]
    if payload.title is not None:
        new_title = payload.title.strip()
        if not new_title:
            conn.close()
            raise HTTPException(status_code=400, detail="title cannot be empty")

    new_done = row["done"] if payload.done is None else payload.done

    conn.execute(
        "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
        (new_title, bool(new_done), task_id),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return row_to_task(updated)


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return JSONResponse(status_code=204, content=None)


# ---------------------------------------------------------------------------
# Extras
# ---------------------------------------------------------------------------

@app.get("/stats", summary="Task statistics (computed with SQL)")
def get_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    done_count = conn.execute("SELECT COUNT(*) FROM tasks WHERE done = 1").fetchone()[0]
    conn.close()
    return {"total": total, "done": done_count, "open": total - done_count}
