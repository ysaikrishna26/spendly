# Spec: Login and Logout

## Overview
This step wires up real session-based authentication. `/login` currently only renders the form via GET — there is no POST handler, so submitting it does nothing — and `/logout` is a placeholder that returns a plain string. This feature adds the `POST /login` handler (look up the user by email, verify the password with `werkzeug`, start a Flask session, redirect to the landing page) and implements `/logout` (clear the session, redirect to the login page). It also makes `/login` and `/register` session-aware: a user who already has an active session is redirected away from both rather than being shown the auth forms again. It builds directly on the `users` table and password hashing introduced in registration, and is the step that makes "being logged in" a real, persistent concept in the app for the first time — everything after this (profile, expenses) depends on knowing which user is signed in.

## Depends on
- Step 1 — Database Setup (`database/db.py` fully implemented: `get_db()`, `users` table)
- Step 2 — Registration (users can be created with a hashed `password_hash`, so there is something to log in against)

## Routes
- `GET /login` — if already logged in, redirect to `/`; otherwise render the login form — public
- `POST /login` — validate submitted credentials, verify against `users.password_hash`, start a session, redirect to `/` — public
- `GET /logout` — clear the session and redirect to `/login` — logged-in (also safe to hit while logged out; just redirects)
- `GET /register`, `POST /register` — if already logged in, redirect to `/`; otherwise unchanged behavior from the registration step — public

## Database changes
No database changes. The `users` table (`id`, `name`, `email`, `password_hash`) already has everything needed to authenticate a user.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — re-populate the `email` field value on a validation error (matching the pattern already used in `register.html`), and render the `{{ error }}` message when credentials are invalid.
  - `templates/base.html` — nav becomes session-aware: when logged in, show a "Sign out" link (`{{ url_for('logout') }}`, reuse the existing `nav-cta` class) instead of "Sign in" / "Get started". Use Flask's `session` object, which Jinja can read directly (`{% if session.get('user_id') %}`).

## Files to change
- `app.py` — set `app.secret_key` (required for Flask sessions), change `/login` to accept `GET` and `POST` with credential validation and session creation, implement `/logout` to clear the session and redirect, and add an already-logged-in guard (redirect to `/`) at the top of both `/login` and `/register`.
- `templates/login.html` — repopulate the `email` input on re-render after a validation error.
- `templates/base.html` — conditional nav links based on `session`.

## Files to create
No new files.

## New dependencies
No new dependencies. Uses `werkzeug.security.check_password_hash` (pairs with `generate_password_hash`, already used in `database/db.py` and registration) and Flask's built-in `session`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`check_password_hash` against the stored `password_hash` — never compare plaintext)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `app.secret_key` must come from an environment variable with a hardcoded local-dev fallback (e.g. `os environ.get("SECRET_KEY", "dev-secret-key-change-in-production")`) — do not leave it unset
- On invalid email or invalid password, re-render `login.html` with a single generic error (e.g. "Invalid email or password") and HTTP 200 — do not reveal whether the email exists
- On success: store the minimum needed in `session` (`user_id`, `user_name`), then redirect (302) to `/`
- `/logout` clears the entire session (`session.clear()`) and redirects (302) to `/login`
- `/login` and `/register` both check `session.get('user_id')` first and redirect (302) to `/` before doing anything else (GET or POST) — an already-authenticated user should never see either form
- Do not add `@login_required`-style guards to `/profile` or `/expenses/*` routes in this step — those routes stay as the existing unimplemented placeholders; the only new access-control in scope is keeping already-logged-in users off `/login` and `/register`
- Do not implement the real `/profile` page or any expense routes beyond what already exists

## Definition of done
- [ ] Visiting `/login` while logged out still shows the form (GET unchanged)
- [ ] Visiting `/register` while logged out still shows the form (unchanged)
- [ ] Submitting valid credentials (email + correct password for an existing user) starts a session and redirects to `/`
- [ ] Submitting an email that doesn't exist re-renders `login.html` with a generic "Invalid email or password" error and does not start a session
- [ ] Submitting a correct email with the wrong password re-renders `login.html` with the same generic error and does not start a session
- [ ] Re-rendered form after an error keeps the previously typed email in the input
- [ ] After logging in, the nav bar shows "Sign out" instead of "Sign in" / "Get started"
- [ ] While logged in, visiting `/login` redirects to `/` instead of showing the form
- [ ] While logged in, visiting `/register` redirects to `/` instead of showing the form
- [ ] Visiting `/logout` while logged in clears the session and redirects to `/login`, and the nav reverts to "Sign in" / "Get started"
- [ ] Visiting `/logout` while logged out does not error — it just redirects to `/login`
- [ ] App starts and runs without errors via `python3 app.py`
