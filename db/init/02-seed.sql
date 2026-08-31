SET synchronous_commit = off;

INSERT INTO users (email, name, country, created_at)
SELECT
  'user' || g || (ARRAY['@gmail.com','@outlook.com','@example.com','@work.co'])[1 + (g % 4)],
  'User ' || g,
  (ARRAY['United States','Philippines','United Kingdom','New Zealand','Netherlands','South Korea'])[1 + (g % 6)],
  timestamptz '2025-01-01' + (g % 600) * interval '1 day'
FROM generate_series(1, 200000) g;

INSERT INTO workspaces (name) SELECT 'Workspace ' || g FROM generate_series(1, 5000) g;

-- the bulk: workspaces 2..5000
INSERT INTO projects (workspace_id, name, created_at)
SELECT 2 + (g % 4999), 'Project ' || g,
       timestamptz '2025-06-01' + (g % 400) * interval '1 day'
FROM generate_series(1, 39960) g;

-- the demo workspace (id 1) is controlled, so lab IV's counts are exact
INSERT INTO projects (workspace_id, name, created_at)
SELECT 1, 'Demo Project ' || g, timestamptz '2026-01-01' + g * interval '1 day'
FROM generate_series(1, 40) g;

INSERT INTO collaborators (project_id, user_id)
SELECT p.id, 1 + ((p.id * 7 + s) % 200000)
FROM projects p, generate_series(1, 8) s
WHERE p.workspace_id = 1;

INSERT INTO collaborators (project_id, user_id)
SELECT 1 + (g % 39960), 1 + (g % 200000)
FROM generate_series(1, 280000) g;

INSERT INTO tasks (project_id, assignee_id, title, estimate_hours, status, created_at)
SELECT p.id, 1 + ((p.id * 13 + s) % 200000), 'Task ' || s,
       1 + (s % 40), (ARRAY['open','done','blocked'])[1 + (s % 3)],
       timestamptz '2026-01-01' + (s % 180) * interval '1 day'
FROM projects p, generate_series(1, 120) s
WHERE p.workspace_id = 1;

-- Assignees are drawn from the first 180,000 users.
INSERT INTO tasks (project_id, assignee_id, title, estimate_hours, status, created_at)
SELECT 1 + (g % 39960), 1 + (g % 180000), 'Task ' || g,
       1 + (g % 40), (ARRAY['open','done','blocked'])[1 + (g % 3)],
       timestamptz '2025-07-01' + (g % 400) * interval '1 day'
FROM generate_series(1, 1995200) g;

ANALYZE;
