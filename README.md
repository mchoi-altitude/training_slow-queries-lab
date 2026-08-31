# Slow Queries Lab

A project collaboration app with two hundred thousand users and two million
tasks, and two endpoints that shipped to production in a state no one should be
proud of.

Companion to two worksheets: **Why Production Is Slow** and **Death by a
Thousand Queries**. Do the worksheets first. Predict the numbers on paper, then
come here and find out whether you were right.

## Start it

```bash
docker compose up -d --build
```

First start seeds the database and takes about a minute. The API is on
`http://localhost:5002`, Postgres on `localhost:5436` (`lab` / `lab`).

```bash
curl -s localhost:5002/api/stats
```

| table | rows |
|---|---|
| `users` | 200,000 |
| `workspaces` | 5,000 |
| `projects` | 40,000 |
| `collaborators` | 280,320 |
| `tasks` | 2,000,000 |

Workspace **1** is the one the endpoints use. It has exactly 40 projects, each
with 8 collaborators and 120 tasks, so the query counts below are exact rather
than approximate.

## The two endpoints

Each comes in two versions that do the same job. Both report how many queries
they issued and how long they took.

```bash
curl -s localhost:5002/api/sidenav/slow | jq '{queries, ms}'
curl -s localhost:5002/api/sidenav/fast | jq '{queries, ms}'
```

Both report `queries` and `ms`. **Write down what you expect before you run
them.** The worksheet asks you to predict, and being wrong on paper is free.

**Every query in the slow versions is fast.** They are all indexed primary-key
lookups, well under a millisecond. `EXPLAIN` has nothing to say about any of
them. That is the entire point: this is a bug a query plan cannot show you.

## The sort is quadratic

`/api/top-projects/slow` sorts by asking the database for the same counts over
and over. Pass `?n=` to sort fewer projects and watch what happens.

```bash
for n in 5 10 20 40; do
  curl -s "localhost:5002/api/top-projects/slow?n=$n" | jq -c '{n:'"$n"', queries, ms}'
done
```

Fill the table in on the worksheet as you go.

Double the projects, quadruple the work. That is what quadratic means, and it is
why it was fine on the developer's laptop with three projects.

## About the latency knob

```yaml
LATENCY_MS: "0.4"
```

On this machine the API and the database share a Docker network, so a round trip
really costs about **0.04 ms** — perhaps thirty times faster than an app talking
to a database across a real network. Left alone, the lab would understate the
bug by an order of magnitude.

`LATENCY_MS` adds a spin-wait of the given length to every query so the wait is
the one your users would actually sit through. Set it to `0` to see the raw
machine numbers; the **query counts never change**, which is why they, not the
milliseconds, are the number to argue about.

## What is where

```
api/app.py           the whole API. ~120 lines. Nothing is hidden.
db/init/01-schema.sql  tables, and a deliberate choice about which columns
                       are indexed and which are not
db/init/02-seed.sql    the data
docker-compose.yml     ports, and the latency knob
```

Some foreign keys are indexed and some are not, **on purpose**. `tasks.project_id`
and `collaborators.project_id` are indexed so that the thousand-queries lab is
about the number of queries rather than the cost of each one.
`tasks.assignee_id` and `projects.workspace_id` are not, because the other
worksheet needs them that way.
