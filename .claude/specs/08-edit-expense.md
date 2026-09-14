# Spec: Edit Expense

## Overview
Step 8 replaces the `/expenses/<id>/edit` placeholder with a working feature
that lets a logged-in user update an expense they own. It is the second of
the expense-CRUD steps (add → edit → delete) and reuses the same form shape
introduced in Step 7, pre-filled with the existing row's values. Editing must
respect ownership — a user can only edit their own expenses — so the changes
they make are reflected back on their profile page immediately.

## Depends on
- Step 1: Database setup (`expenses` table, `get_db()`)
- Step 2: Registration (users exist to own expenses)
- Step 3: Login / Logout (`session["user_id"]` identifies the owner)
- Step 5: Profile backend routes (profile page reads from `expenses`, so
  edits show up there immediately)
- Step 7: Add Expense (introduces `EXPENSE_CATEGORIES`, `_is_valid_date`,
  and the add-expense form pattern this feature reuses)

## Routes
- `GET /expenses/<id>/edit` — render the edit form pre-filled with the
  expense's current values — logged-in only, owner only
- `POST /expenses/<id>/edit` — validate and update the expense, then
  redirect to `/profile` — logged-in only, owner only

Both methods are handled on the existing `/expenses/<id>/edit` route (same
pattern as `add_expense`: one route, branch on `request.method`). If the
expense does not exist, or exists but belongs to a different user, respond
the same way (e.g. redirect to `/profile`) so ownership can't be probed by
id.

## Database changes
No database changes. The `expenses` table already has every column needed
(`user_id`, `amount`, `category`, `date`, `description`).

## Templates
- **Create:** `templates/edit_expense.html` — same field set and card-based
  style as `templates/add_expense.html` (amount, category select, date,
  optional description), form fields pre-filled with the expense's current
  values, submits to `/expenses/<id>/edit`. Extends `base.html`, shows
  inline validation errors the same way `add_expense.html` does.
- **Modify:** `templates/profile.html` — link each transaction row to its
  `/expenses/<id>/edit` route so the feature is reachable from the UI.

## Files to change
- `app.py` — replace the `edit_expense` placeholder with the real
  `GET`/`POST` implementation
- `templates/profile.html` — add an edit link/button per transaction row

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (not applicable to this feature, but keep
  existing auth code untouched)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Require `session.get("user_id")`; unauthenticated requests redirect to
  `/login` (same pattern as `/profile`, `/analytics`, and `/expenses/add`)
- Look up the expense by id scoped to `WHERE id = ? AND user_id = ?`
  (never trust the id alone) — if no matching row is found, redirect to
  `/profile` instead of rendering the form or a 404/403 page
- `amount` must be required, parse as a positive number (reject zero,
  negative, and non-numeric input) — re-render the form with an error and
  the user's submitted values on failure, matching the `add_expense.html`
  error pattern
- `category` must be required and one of `EXPENSE_CATEGORIES`
- `date` must be required and a valid `YYYY-MM-DD` date (reuse
  `_is_valid_date`)
- `description` is optional and stored as-is (empty string or NULL)
- On success, update the row (still scoped to `WHERE id = ? AND user_id = ?`)
  and redirect to `/profile`

## Definition of done
- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for an expense owned by the signed-in
      user shows the edit form pre-filled with its current amount, category,
      date, and description
- [ ] Visiting `/expenses/<id>/edit` for an expense that doesn't exist, or
      that belongs to a different user, does not show the form or leak the
      other user's data (redirects to `/profile`)
- [ ] Submitting the form with a valid amount, category, and date updates
      the existing row and redirects to `/profile`
- [ ] The updated expense's new values appear in the profile page's
      transaction list, total spent, and category breakdown without a
      server restart
- [ ] Submitting with a missing/zero/negative/non-numeric amount re-renders
      the form with an error and does not modify the row
- [ ] Submitting with a missing or invalid date re-renders the form with an
      error and does not modify the row
- [ ] Submitting with no category selected re-renders the form with an error
      and does not modify the row
- [ ] Submitting a POST to `/expenses/<id>/edit` for an expense owned by a
      different user does not modify that row
