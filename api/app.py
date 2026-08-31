"""The whole API. Nothing is hidden.

Every endpoint comes in two versions. The /slow one is what actually shipped.
The /fast one does the same job. Both report how many queries they issued and
how long they took, because that is the entire lesson.
"""
import os, time
import psycopg
from flask import Flask, jsonify, request

DSN = os.environ.get("DSN", "postgresql://lab:lab@db:5432/collab")
WORKSPACE = 1          # the controlled demo workspace: 40 projects

# On this laptop the API and the database share a Docker network, so a round
# trip costs about 0.04 ms -- perhaps thirty times faster than an app talking to
# a database over a real network. That makes the bug look far milder than it is.
# Set LATENCY_MS in docker-compose.yml to something honest (0.4 is typical) and
# the wait becomes the one your users would actually sit through.
LATENCY_MS = float(os.environ.get("LATENCY_MS", "0"))
app = Flask(__name__)


class Counted:
    """A connection that keeps score. One .q() call = one round trip."""
    def __init__(self, conn):
        self.conn, self.n = conn, 0

    def q(self, sql, args=()):
        self.n += 1
        if LATENCY_MS:
            # time.sleep() cannot do sub-millisecond waits -- ask it for 0.4 ms
            # and you get about 3. Spin instead, so the number on the label is
            # the number you actually pay.
            end = time.perf_counter() + LATENCY_MS / 1000.0
            while time.perf_counter() < end:
                pass
        with self.conn.cursor() as c:
            c.execute(sql, args)
            return c.fetchall() if c.description else []


def timed(fn, n=None):
    with psycopg.connect(DSN) as conn:
        db = Counted(conn)
        t0 = time.perf_counter()
        result = fn(db, n) if n is not None else fn(db)
        ms = (time.perf_counter() - t0) * 1000
    return jsonify(queries=db.n, ms=round(ms, 1), result=result)


# ---------------------------------------------------------------- side nav
def sidenav_slow(db, n=None):
    """What shipped. A query in a loop, inside a query in a loop."""
    projects = db.q("SELECT id, name FROM projects WHERE workspace_id = %s", (WORKSPACE,))
    out = []
    for pid, pname in projects:
        collabs = db.q("SELECT user_id FROM collaborators WHERE project_id = %s", (pid,))
        for (uid,) in collabs:
            db.q("SELECT id, name FROM users WHERE id = %s", (uid,))      # only needed a count
        tasks = db.q("SELECT id, assignee_id FROM tasks WHERE project_id = %s", (pid,))
        for (_tid, aid) in tasks:
            if aid:
                db.q("SELECT id, name FROM users WHERE id = %s", (aid,))  # only needed a count
        out.append({"project": pname, "collaborators": len(collabs), "tasks": len(tasks)})
    return out[:5]


def sidenav_fast(db, n=None):
    rows = db.q("""
        SELECT p.name,
               count(DISTINCT c.user_id) AS collaborators,
               count(DISTINCT t.id)      AS tasks
        FROM projects p
        LEFT JOIN collaborators c ON c.project_id = p.id
        LEFT JOIN tasks         t ON t.project_id = p.id
        WHERE p.workspace_id = %s
        GROUP BY p.id, p.name
        ORDER BY p.id
    """, (WORKSPACE,))
    return [{"project": r[0], "collaborators": r[1], "tasks": r[2]} for r in rows][:5]


# ------------------------------------------------------------ top projects
def top_projects_slow(db, n=None):
    """Fetches the counts, throws them away, then sorts by asking again. Twice."""
    projects = [list(r) for r in
                db.q("SELECT id, name FROM projects WHERE workspace_id = %s", (WORKSPACE,))]
    if n:
        projects = projects[:n]
    for p in projects:
        p.append(db.q("SELECT count(*) FROM tasks WHERE project_id = %s", (p[0],))[0][0])

    for _i in range(len(projects)):
        for j in range(len(projects) - 1):
            a = db.q("SELECT count(*) FROM tasks WHERE project_id = %s", (projects[j][0],))[0][0]
            b = db.q("SELECT count(*) FROM tasks WHERE project_id = %s", (projects[j + 1][0],))[0][0]
            if a < b:
                projects[j], projects[j + 1] = projects[j + 1], projects[j]
    return [{"project": p[1], "tasks": p[2]} for p in projects[:3]]


def top_projects_fast(db, n=None):
    rows = db.q("""
        SELECT p.name, count(t.id) AS tasks
        FROM projects p
        LEFT JOIN tasks t ON t.project_id = p.id
        WHERE p.workspace_id = %s
        GROUP BY p.id, p.name
        ORDER BY tasks DESC
        LIMIT 3
    """, (WORKSPACE,))
    return [{"project": r[0], "tasks": r[1]} for r in rows]


ROUTES = {"sidenav": (sidenav_slow, sidenav_fast),
          "top-projects": (top_projects_slow, top_projects_fast)}


@app.get("/api/<name>/<speed>")
def run(name, speed):
    if name not in ROUTES or speed not in ("slow", "fast"):
        return jsonify(error="try /api/sidenav/slow"), 404
    n = request.args.get("n", type=int)
    return timed(ROUTES[name][0 if speed == "slow" else 1], n)


@app.get("/api/stats")
def stats():
    def go(db, _n=None):
        return {t: db.q(f"SELECT count(*) FROM {t}")[0][0]
                for t in ("users", "workspaces", "projects", "collaborators", "tasks")}
    return timed(go)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
