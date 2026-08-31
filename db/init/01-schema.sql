-- A project collaboration app. Deliberately under-indexed: primary keys only,
-- plus two indexes that the worksheet's queries manage to defeat.
CREATE TABLE users (
  id         serial PRIMARY KEY,
  email      text        NOT NULL,
  name       text        NOT NULL,
  country    text        NOT NULL,
  created_at timestamptz NOT NULL
);
CREATE TABLE workspaces (
  id   serial PRIMARY KEY,
  name text NOT NULL
);
CREATE TABLE projects (
  id           serial PRIMARY KEY,
  workspace_id int  NOT NULL,
  name         text NOT NULL,
  created_at   timestamptz NOT NULL
);
CREATE TABLE collaborators (
  id         serial PRIMARY KEY,
  project_id int NOT NULL,
  user_id    int NOT NULL
);
CREATE TABLE tasks (
  id             serial PRIMARY KEY,
  project_id     int  NOT NULL,
  assignee_id    int,
  title          text NOT NULL,
  estimate_hours int  NOT NULL,
  status         text NOT NULL,
  created_at     timestamptz NOT NULL
);

-- These two exist so that queries 2 and 3 on the worksheet have an index
-- available and still fail to use it. That is the lesson, not an oversight.
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_users_email      ON users(email);

-- Indexed, so that lab IV's point holds: every query its loops issue really is
-- fast. The bug there is the NUMBER of queries, not the cost of any one of them.
CREATE INDEX idx_tasks_project_id        ON tasks(project_id);
CREATE INDEX idx_collaborators_project   ON collaborators(project_id);

-- Left unindexed on purpose, for lab III:
--   tasks.assignee_id      -- a join with no index on the key
--   projects.workspace_id  -- a filter with no index
--   tasks.estimate_hours   -- a sort with no index
