# Spec: Delete Expense

## Overview
Step 9 replaces the `/expenses/<id>/delete` placeholder with a working
feature that lets a logged-in user permanently remove an expense they own.
It is the third and final step of the expense-CRUD trio (add → edit →
delete) and, like edit, must respect ownership and reflect the change back
on the profile page immediately. Because deletion is destructive and
irreversible, the route only accepts `POST` (no `GET`-triggered deletes) and
the UI asks for confirmation before submitting.

## Depends on
- Step 1: Database setup (`expenses` table, `get_db()`)
- Step 2: Registration (users exist to own expenses)
- Step 3: Login / Logout (`session["user_id"]` identifies the owner)
- Step 5: Profile backend routes (profile page reads from `expenses`, so
  deletions show up there immediately)
- Step 7: Add Expense (introduces `EXPENSE_CATEGORIES` styling patterns the
  transaction row reuses)
- Step 8: Edit Expense (introduces the per-row action cell in
  `profile.html` — `.profile-table-actions` / `.table-edit-link` — that the
  delete button is added next to)

## Routes
- `POST /expenses/<id>/delete` — delete the expense if it belongs to the
  signed-in user, then redirect to `/profile` — logged-in only, owner only

The existing route is decorated with no `methods`, so it currently only
accepts `GET`. Change it to `methods=["POST"]` — deleting must never happen
as a side effect of a `GET` request (link prefetching, crawlers, etc.). If
the expense does not exist, or exists but belongs to a different user,
respond the same way (redirect to `/profile`) so ownership can't be probed
by id.

## Database changes
No database changes. Deletion is a plain `DELETE FROM expenses WHERE id = ?
AND user_id = ?`.

## Templates
- **Modify:** `templates/profile.html` — add a delete control next to the
  existing edit link in `.profile-table-actions` for each transaction row:
  a small `<form method="post" action="{{ url_for('delete_expense',
  id=tx.id) }}">` containing a submit button styled like `table-edit-link`
  (trash icon via `<i data-lucide="trash-2">`), with a `data-confirm`
  attribute (or similar hook) for the confirmation behavior added in
  `static/js/main.js`.

## Files to change
- `app.py` — replace the `delete_expense` placeholder with the real `POST`
  implementation
- `templates/profile.html` — add a delete form/button per transaction row
- `static/css/style.css` — add a delete-button style alongside the existing
  `.table-edit-link` rules (reuse the same CSS variables, no new hex values)
- `static/js/main.js` — add a small confirm-before-submit handler for
  delete forms (e.g. listen for `submit` on `form[data-confirm]` and call
  `window.confirm(...)`, preventing submission if the user cancels)

## Files to create
No new files.

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
  `/login` (same pattern as `/profile`, `/expenses/add`, and
  `/expenses/<id>/edit`)
- Route only accepts `POST` — no `GET` handler for deletion
- Look up and delete the expense scoped to `WHERE id = ? AND user_id = ?`
  in the same query (never trust the id alone, never do a separate
  existence check followed by an unscoped delete)
- On success (row existed and belonged to the user) or on a no-op (row
  didn't exist / belonged to someone else), redirect to `/profile` either
  way — don't leak whether the id existed
- Confirmation is client-side only (JS `confirm()`); the server still must
  not trust the client and must re-check ownership itself
- Add page behavior in `static/js/main.js`, not inline `<script>` blocks in
  templates, per `CLAUDE.md`

## Definition of done
- [ ] Visiting `/expenses/<id>/delete` with `GET` does not delete anything
      (method not allowed)
- [ ] Submitting the delete form while logged out redirects to `/login` and
      does not delete the row
- [ ] Submitting the delete form for an expense owned by the signed-in user
      removes it and redirects to `/profile`
- [ ] The deleted expense no longer appears in the profile page's
      transaction list, and total spent / category breakdown update
      accordingly without a server restart
- [ ] Submitting a `POST` to `/expenses/<id>/delete` for an expense owned by
      a different user does not delete that row and still redirects to
      `/profile`
- [ ] Submitting a `POST` to `/expenses/<id>/delete` for an id that doesn't
      exist does not error and redirects to `/profile`
- [ ] Clicking the delete button in the UI shows a confirmation prompt
      before the form submits, and cancelling leaves the expense intact
