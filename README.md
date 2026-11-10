# my-service service

Async FastAPI service, Python 3.12+, PostgreSQL, SQLAlchemy 2, Alembic.

Copy `.env.example` to `.env` and set local credentials. Start the database with
`docker compose up -d postgres`. From `backend/`, run:

```sh
uv sync
# Export DATABASE_URL from the root .env, or copy .env to backend/.env.
uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --reload
```

`GET /api/v1/health` checks the process, not database readiness.
Item endpoints return 401 until `current_user_id` is replaced with a trusted
identity dependency. Tests override that dependency; no client header grants identity.

Run migrations before starting the API container. For example:
`docker compose run --rm api uv run --no-dev alembic upgrade head`, then
`docker compose up --build api`.

From `backend/`, run `uv run ruff check .`, `uv run ruff format --check .`,
`uv run pyright`, and `uv run pytest -ra`.
Set `TEST_DATABASE_URL` to a disposable PostgreSQL database to run integration tests.
The fixture applies migrations there; tests use real commits and truncate items afterward.
Without that variable, integration tests skip with an explicit message.

Install the Lefthook CLI separately and run `lefthook install` to enable the
pre-commit Ruff and Pyright checks. CI runs the same checks plus migrations, schema
drift detection, PostgreSQL tests,
and a Docker build.

The seed includes `uv.lock`. Commit lockfile changes when updating dependencies.
Docker installs from that lockfile with `uv sync --frozen --no-dev` and runs as UID 10001.

AGENTS.md is pre-rendered in lee-start using `scripts/render_agents_md.py`.
CLAUDE.md imports it. No post-generation task is required.

Before updating, commit or stash all changes. Run
`copier update --defaults --vcs-ref <approved-tag>` from the project root.
Existing `backend/app/main.py`, `backend/app/routers/**`, `backend/app/services/**`,
`backend/app/repositories/**`, `backend/app/schemas/**`, `backend/tests/**`, and
`backend/alembic/versions/**` are preserved by `_skip_if_exists`.
`backend/app/core/**` stays eligible for template fixes through Copier's three-way merge.

Existing `frontend/src/features/**` and `frontend/src/App.tsx` are also preserved;
frontend configuration, shared client, and ErrorBoundary remain updatable.
`frontend/index.html` and generated API types are project-owned and preserved.

Protection applies only to files that exist: deleted examples may be recreated during
update. A committed deletion is not a permanent exclusion. Inspect the update diff;
remove unwanted examples again and adjust imports, tests, and migrations together.
Review new files and configuration changes. Check `git status --short`,
`git diff --check`, conflict markers, and `.rej` files even when Copier exits 0.

Repositories flush writes; `get_session` commits the complete request transaction
on success and rolls it back on failure. Services called outside that dependency
must supply their own transaction boundary.

Offline SQL generation needs only `DATABASE_URL`; it never opens a connection.
After changing ORM models, create and review an Alembic revision, then run
`uv run alembic upgrade head` and `uv run alembic check` against a disposable database.


## Frontend

Use the Node version in `frontend/.nvmrc`. From `frontend/`, run:

```sh
npm ci
npm run dev
```

Relative API URLs use
Vite's development proxy to `127.0.0.1:8000`; start the backend as above.
Production hosting must serve `dist/`, fall back to `index.html` for frontend routes,
and proxy `/api` to the backend on the same origin; cross-origin hosting requires a separate CORS and cookie policy.

Run `npm run lint`, `npm run format:check`, `npm run typecheck`, `npm test`, and
`npm run build`. Run `npm run generate:api` after backend contract changes and commit
`src/api/schema.d.ts`. This exports OpenAPI through the app factory without starting
a server or connecting to a database; uv and the backend Python environment are required.
`npm run check:api` regenerates types and fails if the committed output differs.

