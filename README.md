# Task API

A small in-memory CRUD API for managing a to-do list, built with **FastAPI** as part of FlyRank's W2·A1 assignment.

- Data lives in a Python list in memory — nothing is saved to disk, so it resets when the server restarts.
- Interactive API docs (Swagger UI) are generated automatically by FastAPI.

## How to run it

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

The server starts at `http://localhost:8000`.

- API root: http://localhost:8000/
- Swagger UI: http://localhost:8000/docs

## Endpoints

| Method | Path              | Description                                  | Success | Errors        |
|--------|-------------------|-----------------------------------------------|---------|---------------|
| GET    | `/`               | API info                                      | 200     | —             |
| GET    | `/health`         | Health check                                  | 200     | —             |
| GET    | `/tasks`          | List all tasks (supports `?done=`, `?search=`, `?limit=`, `?offset=`) | 200 | — |
| GET    | `/tasks/{id}`     | Get a single task                             | 200     | 404 unknown id |
| POST   | `/tasks`          | Create a task (`{"title": "..."}`)            | 201     | 400 missing/empty title |
| PUT    | `/tasks/{id}`     | Update a task's title and/or done status      | 200     | 400 empty title · 404 unknown id |
| DELETE | `/tasks/{id}`     | Delete a task                                 | 204     | 404 unknown id |
| GET    | `/stats`          | Task counts: total / done / open (bonus)      | 200     | —             |
| POST   | `/reset`          | Restore the 3 example tasks (bonus)           | 200     | —             |

## Example: full CRUD cycle with curl

```bash
# Create
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Buy milk"}'
```

```
HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

```bash
# Update (mark done)
curl -i -X PUT http://localhost:8000/tasks/4 -H "Content-Type: application/json" -d '{"done":true}'

# Delete
curl -i -X DELETE http://localhost:8000/tasks/4

# Invalid create (empty title) -> 400
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":""}'

# Unknown id -> 404
curl -i http://localhost:8000/tasks/99
```

## Swagger UI

Open http://localhost:8000/docs after starting the server. Every endpoint above is listed with a
"Try it out" button that lets you run the full CRUD cycle (create → list → update → delete) without curl.

*(Add your own screenshot here after trying it out.)*

## The mortality experiment

Create a task, restart the server (`Ctrl+C` then `uvicorn main:app --reload` again), then `GET /tasks`.

*Your two sentences here: what happened, and why (hint — it's the "in-memory" part of "in-memory storage").*

## Notes

- Validation: `POST` and `PUT` reject a missing or empty (or whitespace-only) `title` with `400`.
- Pagination/filtering (`?done=`, `?search=`, `?limit=`, `?offset=`) is included as a bonus extra.
