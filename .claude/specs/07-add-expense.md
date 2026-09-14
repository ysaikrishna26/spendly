# Spec: Add Expense

## Overview
Step 7 replaces the `/expenses/add` placeholder with a working feature that
lets a logged-in user record a new expense. This is the first of the
expense-CRUD steps (add → edit → delete) and is what finally lets the
`expenses` table grow beyond the seeded demo data. It introduces a form page
and a `POST` handler that validates input, inserts a row scoped to the
signed-in user, and sends them back to their profile to see it reflected in
the stats, transaction list, and category breakdown that Step 5 already
wired up.

## Depends on
- Step 1: Database setup (`expenses` table, `get_db()`)
- Step 2: Registration (users exist to own expenses)
- Step 3: Login / Logout (`session["user_id"]` identifies the owner)
- Step 5: Profile backend routes (profile page already reads from `expenses`,
  so newly added rows show up there immediately)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert the new expense, then redirect
  to `/profile` — logged-in only

Both methods are handled on the existing `/expenses/add` route (same pattern
as `register`/`login`: one route, branch on `request.method`).

## Database changes
No database changes. The `expenses` table already has every column needed
(`user_id`, `amount`, `category`, `date`, `description`).

## Templates
- **Create:** `templates/add_expense.html` — form with fields: amount,
  category (select, options matching the categories already seeded/used on
  the profile page: Food, Transport, Bills, Health, Entertainment, Shopping,
  Other), date (defaults to today), description (optional). Extends
  `base.html`, follows the card-based style already used by
  `register.html`/`login.html`, shows inline validation errors the same way
  those pages do.
- **Modify:** none required. (Optional nice-to-have, out of scope unless
  requested: linking to `/expenses/add` from `profile.html`.)

## Files to change
- `app.py` — replace the `add_expense` placeholder with the real `GET`/`POST`
  implementation

## Files to create
- `templates/add_expense.html`

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
  `/login` (same pattern as `/profile` and `/analytics`)
- `amount` must be required, parse as a positive number (reject zero,
  negative, and non-numeric input) — re-render the form with an error and
  the user's entered values on failure, matching the `register.html` error
  pattern
- `category` must be required and one of the fixed set of known categories
- `date` must be required and a valid `YYYY-MM-DD` date
- `description` is optional and stored as-is (empty string or NULL)
- On success, insert the row scoped to `session["user_id"]` and redirect to
  `/profile`

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in shows the add-expense form
- [ ] Submitting the form with a valid amount, category, and date creates a
      new row in `expenses` owned by the signed-in user and redirects to
      `/profile`
- [ ] The newly added expense appears in the profile page's transaction
      list, total spent, and category breakdown without a server restart
- [ ] Submitting with a missing/zero/negative/non-numeric amount re-renders
      the form with an error and does not insert a row
- [ ] Submitting with a missing or invalid date re-renders the form with an
      error and does not insert a row
- [ ] Submitting with no category selected re-renders the form with an error
      and does not insert a row
