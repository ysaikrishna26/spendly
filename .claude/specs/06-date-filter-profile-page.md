# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date-range filter to the `/profile` page so users can narrow the
summary stats, recent transactions, and category breakdown to a specific
window of time instead of always seeing all-time totals. The route already
computes these three sections with live SQL queries against `expenses`
(Step 5); this step adds an optional date range to those same queries, plus a
filter control on the page for choosing "All Time", a few common presets, or
a custom start/end date.

## Depends on
- Step 1: Database setup (`expenses.date` column exists)
- Step 2: Registration (users exist)
- Step 3: Login / Logout (`session["user_id"]` is set)
- Step 5: Profile backend routes (`/profile` already queries stats,
  transactions, and category breakdown live from the database)

## Routes
- `GET /profile` — modified (not new) — logged-in only — now accepts optional
  query string params `start` (YYYY-MM-DD) and `end` (YYYY-MM-DD). When both
  are present, all three sections (summary stats, transactions, category
  breakdown) are scoped to `date BETWEEN start AND end` (inclusive). When
  absent, behavior is unchanged (all-time totals).

## Database changes
No database changes. `expenses.date` (TEXT, `YYYY-MM-DD`) already supports
range comparisons via SQLite's lexicographic string ordering.

## Templates
- **Modify:** `templates/profile.html`
  - Add a filter bar above `.profile-stats` with:
    - Preset links/buttons: "All Time", "This Month", "Last 30 Days" (each a
      plain `GET` link to `/profile` with the right `start`/`end` query
      params, or no params for "All Time")
    - A small custom-range form (`<form method="get" action="/profile">`)
      with two `<input type="date">` fields (`start`, `end`) and an "Apply"
      submit button
    - The currently active preset/range should be visually indicated (e.g. an
      `is-active` class on the matching link)
  - No changes to the stats/transactions/category markup itself — they keep
    rendering whatever `app.py` passes in, same as Step 5

## Files to change
- `app.py` — in the `profile()` view:
  - Read `start`/`end` from `request.args`
  - Validate both are present and parse as `YYYY-MM-DD`; if either is missing
    or invalid, fall back to no filter (all-time) rather than erroring
  - Append a `AND date BETWEEN ? AND ?` clause (with the two values as bound
    params) to the existing summary/transactions/category SQL when a valid
    range is present
  - Pass the resolved `start`, `end`, and an `active_preset` label to the
    template so the filter bar can render current state
- `templates/profile.html` — add the filter bar described above
- `static/css/style.css` — add styles for the new filter bar (reuse existing
  CSS variables for colors/spacing; add a `.profile-filter` block plus an
  `is-active` state)

## Files to create
No new files. (Query logic stays inline in `app.py`'s `profile()` view,
consistent with how Step 5 was actually implemented — there is no
`database/queries.py` in this codebase.)

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format `start`/`end` into SQL
- Passwords hashed with werkzeug (unchanged by this step; listed for
  consistency)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Invalid or partial date input (only one of `start`/`end`, malformed dates,
  `start` after `end`) must never raise a 500 — silently fall back to
  all-time results
- Preset date math ("This Month", "Last 30 Days") is computed server-side in
  `app.py`, not in the template

## Definition of done
- [ ] Visiting `/profile` with no query params shows the same all-time
      totals as before this step
- [ ] Clicking "This Month" filters stats, transactions, and category
      breakdown to the current calendar month only, and marks "This Month" as
      active
- [ ] Clicking "Last 30 Days" filters to the trailing 30-day window and marks
      itself active
- [ ] Entering a custom start/end date and clicking "Apply" filters all three
      sections to that inclusive range and pre-fills the date inputs with the
      chosen values
- [ ] A user with no expenses in the selected range sees ₹0.00 total spent, 0
      transactions, and an empty category breakdown — no errors
- [ ] Manually visiting `/profile?start=not-a-date&end=2026-09-01` does not
      error and falls back to all-time results
- [ ] Manually visiting `/profile?start=2026-09-30&end=2026-09-01` (end
      before start) does not error and returns an empty result set rather
      than all-time totals
