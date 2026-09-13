# Spec: Registration

## Overview
This step implements real user registration. Currently `/register` only renders the form via GET — submitting it does nothing, since there is no POST handler. This feature wires the existing `register.html` form up to the `users` table: validating input, checking for duplicate emails, hashing the password with `werkzeug`, inserting the new user. On success the user is shown with success message and then redirected to login page.It is the first step that makes Spendly's auth flow functional, and everything downstream (login, logout, profile, expenses) depends on a user being able to create an account.

## Depends on
- Step 1 — Database Setup (`database/db.py` fully implemented: `get_db()`, `init_db()`, `users` table)

## Routes
- `GET /register` — render the registration form (already implemented, unchanged) — public
- `POST /register` — validate submitted form data, create the user, redirect to `/login` with a success message — public

## Database changes
No database changes. The `users` table (id, name, email, password_hash, created_at) already supports registration as defined in `database/db.py`. The `email` column's existing `UNIQUE NOT NULL` constraint is relied on for duplicate-email detection.

## Templates
- **Create:** none
- **Modify:** `templates/register.html` — no structural changes required; it already posts to `/register` and already renders `{{ error }}`. Only re-populate `name`/`email` field values on validation failure so the user doesn't have to retype them (e.g. `value="{{ name or '' }}"`).

## Files to change
- `app.py` — change `/register` to accept `GET` and `POST`; add validation, duplicate-email check, password hashing, insert, and session creation logic.
- `templates/register.html` — repopulate `name` and `email` inputs on re-render after a validation error.

## Files to create
No new files.

## New dependencies
No new dependencies. Uses `werkzeug.security.generate_password_hash` (already a transitive Flask dependency, already used in `database/db.py`) and Flask's built-in `session`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash`, never store plaintext)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Validate on the server even though the form has HTML5 `required`/`type="email"` attributes (client-side validation is not trustworthy)
- Required fields: `name`, `email`, `password` (min. 8 characters, matching the form's placeholder text)
- On duplicate email, re-render `register.html` with an `error` message and HTTP 200 (no redirect) — do not leak whether the email exists via a different mechanism (e.g. same generic message as other validation errors)
- On success: insert the user, then redirect (302) to `/login?registered=1` so the login page can show a success message
- No `app.secret_key` or Flask `session` usage in this step — session-based login is introduced when `/login` itself is implemented
- Do not implement `/login`, `/logout`, or `/profile` logic beyond what already exists — `/login` remains the existing GET-only route, extended only to display the success banner

## Definition of done
- [ ] Visiting `/register` in a browser still shows the form (GET unchanged)
- [ ] Submitting the form with valid name/email/password (8+ chars) creates a new row in `users` with a hashed (not plaintext) password
- [ ] After successful registration, the browser is redirected to `/login` and a success message is shown
- [ ] Submitting with an email that already exists in `users` re-renders the form with an error message and does not create a duplicate row
- [ ] Submitting with a missing name, missing email, or password under 8 characters re-renders the form with an error message and does not create a row
- [ ] Re-rendered form after an error keeps the previously typed name and email in the inputs
- [ ] No plaintext passwords appear anywhere in `expense_tracker.db`
- [ ] App starts and runs without errors via `python3 app.py`
