# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

"Spendly" — a Flask expense tracker built incrementally as a step-by-step learning exercise. Many routes and `database/db.py` are intentionally unimplemented placeholders (see comments like "Step 3", "Step 7", "students will implement these") that get filled in over the course of the project. When asked to implement one of these steps, follow the scope implied by the existing comment rather than jumping ahead to unrelated placeholders.

## Commands

```bash
# Setup (venv/ already exists in repo checkout)
pip install -r requirements.txt

# Run the dev server (port 5001, debug mode)
python app.py

# Run tests
pytest
```

There is no build step, linter, or frontend bundler configured — templates and static assets are served directly by Flask.

## Architecture

- `app.py` — single Flask app with all routes defined directly on it (no blueprints). Routes fall into two groups: implemented pages (`/`, `/register`, `/login`, `/logout`, `/profile`, `/terms`, `/privacy`) that render templates and/or use session-based auth, and placeholder routes (`/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`) that currently return plain strings marking a future step. `/profile` reads the signed-in user's `name`/`email` from the session (set at login) but its stats/transaction/category data is still hardcoded, pending real DB wiring in a future step.
- `database/db.py` — holds `get_db()` (SQLite connection with `row_factory` and foreign keys enabled), `init_db()` (idempotent `CREATE TABLE IF NOT EXISTS` schema), and `seed_db()` (sample dev data). Fully implemented — the SQLite file (`expense_tracker.db`) is gitignored and created at runtime.
- `templates/base.html` — the shared layout (nav, footer, font/CSS includes) that all pages extend via Jinja `{% block %}`s (`title`, `head`, `content`, `scripts`). New pages should extend this base rather than duplicating the shell. Also loads the Lucide icon CDN script and calls `lucide.createIcons()` globally, so any page can render icons via `<i data-lucide="...">`. The nav shows the signed-in user's name (linking to `/profile`) and a "Sign out" link when `session.get('user_id')` is set.
- `static/css/style.css` — single global stylesheet for the whole site (page-specific styles live in the same file, scoped by page-level classes).
- `static/js/main.js` — currently near-empty; add page behavior here rather than inline `<script>` blocks in templates when possible.
