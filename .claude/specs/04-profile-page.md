# Spec: Profile Page

## Overview
This feature replaces the `/profile` stub with a fully designed profile page. The user info card's name and email are read live from the Flask session (set at login) so the page reflects whoever is actually signed in; the summary stats, transaction history table, and category breakdown remain static, hardcoded data. The goal is to establish the complete UI layout before any real database queries are wired up in Step 5. Building the UI first lets the team validate the design in isolation and ensures the templates are ready for the backend-connection step. As of Step 3's amended behavior, a successful `POST /login` redirects here directly (`/profile`) instead of to the landing page.

## Depends on
- Step 1: Database setup (schema must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login + Logout (session must be set; `/profile` must be a protected route)

## Routes
- GET /profile — render the profile page — logged-in only (redirect to /login if not authenticated)

## Database changes
No database changes. The existing `users` and `expenses` tables are sufficient.

## Templates
- Create: `templates/profile.html` — full profile page extending `base.html`; contains four sections:
  1. **User info card** — avatar initials, name, and email derived from `session['user_name']` / `session['user_email']`; member-since date is a hardcoded placeholder
  2. **Summary stats row** — total spent, number of transactions, top category (hardcoded)
  3. **Transaction history table** — list of recent expenses with date, description, category badge, amount (hardcoded rows)
  4. **Category breakdown** — per-category totals displayed as a simple list or progress-bar rows (hardcoded)

## Files to change
- `app.py` — replace the `/profile` stub with a real view function that:
  - Redirects unauthenticated users to `/login`
  - Builds `user.name` / `user.email` / `user.initials` from `session['user_name']` / `session['user_email']`
  - Passes hardcoded context variables (`stats`, `transactions`, `categories`) to `profile.html`
  - `/login`'s success handler now also stores `session['user_email']` and redirects to `/profile` (see amended Step 3 spec)
- `templates/base.html` — nav shows the signed-in user's name (linking to `/profile`) next to "Sign out"; also loads the Lucide icon CDN script and calls `lucide.createIcons()` globally

## Files to create
- `templates/profile.html`

## New dependencies
No new pip packages. `templates/base.html` now loads the Lucide icon library from its CDN (`https://unpkg.com/lucide@latest`) for icon rendering sitewide.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()` if any DB call is ever needed
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
- The user's `name` and `email` are read from `session` (set at login) — no DB query. All other data (`stats`, `transactions`, `categories`) must remain hardcoded Python dicts/lists in `app.py`
- Category badges must use a CSS class, not inline colour styles

## Definition of done
- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] Submitting valid credentials at `/login` redirects straight to `/profile`
- [ ] The page displays a user info card with the currently signed-in user's actual name and email (verify by registering and logging in as a second user — the profile page must show their details, not the demo user's)
- [ ] The page displays at least three summary stat values (e.g. total spent, transaction count, top category)
- [ ] The page displays a transaction history table with at least three hardcoded rows
- [ ] The page displays a category breakdown section with at least three categories
- [ ] The navbar shows the logged-in state (username + logout link)
- [ ] No hex colour values appear in `profile.html` — only CSS variables