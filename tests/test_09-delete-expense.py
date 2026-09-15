"""Tests for Step 9 — Delete Expense.

Spec: .claude/specs/09-delete-expense.md

These tests target the *behavior* described in the spec's Routes, Rules for
implementation, and Definition of done sections — not the implementation in
`app.py`:
  - `POST /expenses/<id>/delete` deletes the expense only if it belongs to
    the signed-in user, then redirects to `/profile`.
  - `GET /expenses/<id>/delete` must not be a valid way to delete (the route
    only accepts POST).
  - Unauthenticated requests redirect to `/login` and never touch the row.
  - Deleting an expense removes it from the profile page's transaction list
    and updates the total-spent / category-breakdown figures immediately.
  - Deleting an id owned by a different user, or an id that doesn't exist,
    is a silent no-op that still redirects to `/profile` (no leaking of
    whether the id existed / who owns it).

Out of scope for these backend tests: the client-side `window.confirm(...)`
prompt in `static/js/main.js` — that is a browser/JS behavior not
observable through the Flask test client, per the task instructions.

Follows the fixture/helper conventions established in
`tests/test_07-add-expense.py`: the app is pointed at a throwaway SQLite
file *before* `app` is imported (so the module-level `init_db()` /
`seed_db()` call in app.py never touches the real dev database), and each
test registers its own uniquely-emailed user(s) so tests never share
mutable state.
"""

import os
import tempfile
import uuid

import pytest

import database.db as db_module

# Point the app at a throwaway SQLite file before importing `app`, so the
# module-level `init_db()` / `seed_db()` call in app.py never touches the
# real dev database (expense_tracker.db). Mirrors tests/test_07-add-expense.py.
db_module.DB_PATH = os.path.join(tempfile.mkdtemp(), "test_09_delete_expense.db")

import app as app_module  # noqa: E402

app_module.app.config["TESTING"] = True


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #


def unique_email(prefix):
    return f"{prefix}.{uuid.uuid4().hex[:8]}@example.com"


def register(client, name, email, password="testpass123"):
    return client.post(
        "/register",
        data={"name": name, "email": email, "password": password},
        follow_redirects=False,
    )


def login(client, email, password="testpass123"):
    return client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=True
    )


def register_and_login(client, prefix="user"):
    """Registers a fresh, uniquely-named user and logs them in.

    Returns (email, user_id) so tests can scope DB assertions to this user
    without any risk of collision with other tests sharing the same DB file.
    """
    email = unique_email(prefix)
    register(client, f"{prefix.title()} Tester", email)
    login(client, email)
    user_id = get_user_id(email)
    return email, user_id


def get_user_id(email):
    db = db_module.get_db()
    row = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    db.close()
    return row["id"] if row else None


def insert_expense(
    user_id,
    amount=42.00,
    category="Food",
    date="2026-03-01",
    description="Test expense",
):
    """Inserts an expense directly via raw parameterised SQL and returns its id."""
    db = db_module.get_db()
    cursor = db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    db.commit()
    expense_id = cursor.lastrowid
    db.close()
    return expense_id


def expense_exists(expense_id):
    db = db_module.get_db()
    row = db.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    db.close()
    return row is not None


def expense_count_for_user(user_id):
    db = db_module.get_db()
    row = db.execute(
        "SELECT COUNT(*) AS c FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    db.close()
    return row["c"]


# ------------------------------------------------------------------ #
# GET is not a valid way to delete (method not allowed)               #
# ------------------------------------------------------------------ #


def test_get_delete_expense_is_method_not_allowed_and_does_not_delete():
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="getguard")
        expense_id = insert_expense(user_id)

        response = client.get(f"/expenses/{expense_id}/delete")

        assert (
            response.status_code == 405
        ), "GET on the delete route should be rejected as method not allowed"
        assert expense_exists(expense_id), "A GET request must never delete the expense"


def test_get_delete_expense_method_not_allowed_even_when_logged_out():
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="getguardanon")
        expense_id = insert_expense(user_id)

    with app_module.app.test_client() as anon_client:
        response = anon_client.get(f"/expenses/{expense_id}/delete")

        assert (
            response.status_code == 405
        ), "GET should be rejected as method not allowed regardless of auth state"
        assert expense_exists(expense_id), "GET must never delete the expense"


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #


def test_post_delete_expense_redirects_to_login_when_logged_out_and_does_not_delete():
    with app_module.app.test_client() as owner_client:
        _, user_id = register_and_login(owner_client, prefix="anonowner")
        expense_id = insert_expense(user_id)

    with app_module.app.test_client() as anon_client:
        response = anon_client.post(
            f"/expenses/{expense_id}/delete", follow_redirects=False
        )

        assert response.status_code == 302, "POST while logged out should redirect"
        assert "/login" in response.headers["Location"], "Should redirect to /login"
        assert expense_exists(
            expense_id
        ), "The expense must not be deleted by an unauthenticated request"


# ------------------------------------------------------------------ #
# Happy path — owner deletes their own expense                        #
# ------------------------------------------------------------------ #


def test_post_delete_expense_owned_by_user_removes_row_and_redirects_to_profile():
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="happydelete")
        expense_id = insert_expense(user_id, description="Delete me")

        response = client.post(f"/expenses/{expense_id}/delete", follow_redirects=False)

        assert response.status_code == 302, "A valid delete should redirect"
        assert "/profile" in response.headers["Location"], "Should redirect to /profile"
        assert not expense_exists(
            expense_id
        ), "The expense row should be removed from the database"
        assert (
            expense_count_for_user(user_id) == 0
        ), "The user should have zero expenses left after deleting their only one"


def test_post_delete_expense_only_removes_targeted_row_not_others():
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="partialdelete")
        keep_id = insert_expense(user_id, description="Keep me", category="Food")
        delete_id = insert_expense(user_id, description="Delete me", category="Bills")

        response = client.post(f"/expenses/{delete_id}/delete", follow_redirects=False)

        assert response.status_code == 302
        assert not expense_exists(delete_id), "Targeted expense should be deleted"
        assert expense_exists(
            keep_id
        ), "Other expenses belonging to the user must survive"
        assert expense_count_for_user(user_id) == 1


# ------------------------------------------------------------------ #
# Profile page reflects the deletion immediately                      #
# ------------------------------------------------------------------ #


def test_deleted_expense_no_longer_appears_in_profile_transaction_list():
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="reflectlist")
        expense_id = insert_expense(
            user_id,
            description="Concert tickets",
            category="Entertainment",
            amount=75.00,
            date="2026-02-01",
        )

        before_html = client.get("/profile").get_data(as_text=True)
        assert (
            "Concert tickets" in before_html
        ), "Sanity check: the expense should appear before deletion"

        client.post(f"/expenses/{expense_id}/delete", follow_redirects=False)

        after_html = client.get("/profile").get_data(as_text=True)
        assert (
            "Concert tickets" not in after_html
        ), "Deleted expense's description must not appear in the transaction list"


def test_deleted_expense_updates_total_spent_on_profile_page():
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="reflecttotal")
        keep_id = insert_expense(
            user_id,
            description="Groceries",
            category="Food",
            amount=20.00,
            date="2026-02-01",
        )
        delete_id = insert_expense(
            user_id,
            description="One-off splurge",
            category="Shopping",
            amount=75.00,
            date="2026-02-02",
        )

        before_html = client.get("/profile").get_data(as_text=True)
        assert (
            "₹95.00" in before_html
        ), "Sanity check: total spent should include both expenses before deletion"

        client.post(f"/expenses/{delete_id}/delete", follow_redirects=False)

        after_html = client.get("/profile").get_data(as_text=True)
        assert (
            "₹20.00" in after_html
        ), "Total spent should drop to reflect only the remaining expense"
        assert (
            "₹95.00" not in after_html
        ), "Old total (including the deleted expense) should no longer be shown"
        assert expense_exists(keep_id), "The non-deleted expense should remain"


def test_deleted_expense_updates_category_breakdown_on_profile_page():
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="reflectcat")
        # Only expense in the "Health" category — deleting it should remove
        # that category from the breakdown entirely.
        expense_id = insert_expense(
            user_id,
            description="Pharmacy run",
            category="Health",
            amount=32.00,
            date="2026-02-03",
        )
        insert_expense(
            user_id,
            description="Weekly lunch",
            category="Food",
            amount=18.00,
            date="2026-02-04",
        )

        before_html = client.get("/profile").get_data(as_text=True)
        assert (
            "Health" in before_html
        ), "Sanity check: category breakdown should include Health before deletion"

        client.post(f"/expenses/{expense_id}/delete", follow_redirects=False)

        after_html = client.get("/profile").get_data(as_text=True)
        assert (
            "Health" not in after_html
        ), "Category breakdown should no longer show a category with zero expenses"
        assert "Food" in after_html, "The remaining category should still be shown"


# ------------------------------------------------------------------ #
# Ownership — can't delete another user's expense                     #
# ------------------------------------------------------------------ #


def test_post_delete_expense_owned_by_different_user_does_not_delete_and_redirects_to_profile():
    with app_module.app.test_client() as owner_client:
        _, owner_id = register_and_login(owner_client, prefix="realowner")
        expense_id = insert_expense(owner_id, description="Not yours")

    with app_module.app.test_client() as attacker_client:
        register_and_login(attacker_client, prefix="attacker")

        response = attacker_client.post(
            f"/expenses/{expense_id}/delete", follow_redirects=False
        )

        assert (
            response.status_code == 302
        ), "Deleting someone else's expense should still redirect, not error"
        assert "/profile" in response.headers["Location"], (
            "Should redirect to /profile even when ownership doesn't match, "
            "so ownership can't be probed by id"
        )
        assert expense_exists(
            expense_id
        ), "An expense owned by a different user must not be deleted"


def test_other_users_expense_still_appears_on_owners_profile_after_attackers_attempt():
    with app_module.app.test_client() as owner_client:
        owner_email, owner_id = register_and_login(owner_client, prefix="ownerpersist")
        expense_id = insert_expense(
            owner_id,
            description="Still mine",
            category="Bills",
            amount=99.99,
        )

    with app_module.app.test_client() as attacker_client:
        register_and_login(attacker_client, prefix="attackerpersist")
        attacker_client.post(f"/expenses/{expense_id}/delete", follow_redirects=False)

    with app_module.app.test_client() as owner_client2:
        login(owner_client2, owner_email)
        html = owner_client2.get("/profile").get_data(as_text=True)
        assert "Still mine" in html, (
            "The rightful owner's expense should be unaffected by another "
            "user's delete attempt"
        )


# ------------------------------------------------------------------ #
# Nonexistent id                                                      #
# ------------------------------------------------------------------ #


def test_post_delete_nonexistent_expense_id_does_not_error_and_redirects_to_profile():
    with app_module.app.test_client() as client:
        register_and_login(client, prefix="ghostid")

        nonexistent_id = 999_999_999

        response = client.post(
            f"/expenses/{nonexistent_id}/delete", follow_redirects=False
        )

        assert (
            response.status_code == 302
        ), "Deleting a nonexistent id should not error out"
        assert (
            "/profile" in response.headers["Location"]
        ), "Should redirect to /profile the same as a successful delete"


def test_post_delete_nonexistent_expense_id_does_not_affect_existing_expenses():
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="ghostidsafety")
        expense_id = insert_expense(user_id, description="Untouched")

        nonexistent_id = 999_999_998
        client.post(f"/expenses/{nonexistent_id}/delete", follow_redirects=False)

        assert expense_exists(
            expense_id
        ), "Deleting an unrelated nonexistent id must not affect real rows"
        assert expense_count_for_user(user_id) == 1
