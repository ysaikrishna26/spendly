import os
import tempfile
import uuid

import pytest

import database.db as db_module

# Point the app at a throwaway SQLite file before importing `app`, so the
# module-level `init_db()` / `seed_db()` call in app.py never touches the
# real dev database (expense_tracker.db). Mirrors tests/test_backend_connection.py.
db_module.DB_PATH = os.path.join(tempfile.mkdtemp(), "test_07_add_expense.db")

import app as app_module  # noqa: E402

app_module.app.config["TESTING"] = True

EXPENSE_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


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


def expense_count_for_user(user_id):
    db = db_module.get_db()
    row = db.execute(
        "SELECT COUNT(*) AS c FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    db.close()
    return row["c"]


def fetch_expenses_for_user(user_id):
    db = db_module.get_db()
    rows = db.execute(
        "SELECT user_id, amount, category, date, description FROM expenses "
        "WHERE user_id = ? ORDER BY id",
        (user_id,),
    ).fetchall()
    db.close()
    return rows


def valid_expense_form(**overrides):
    form = {
        "amount": "50.25",
        "category": "Food",
        "date": "2026-01-15",
        "description": "Weekly lunch",
    }
    form.update(overrides)
    return form


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #

def test_get_add_expense_redirects_when_logged_out():
    with app_module.app.test_client() as client:
        response = client.get("/expenses/add")
        assert response.status_code == 302, "GET while logged out should redirect"
        assert "/login" in response.headers["Location"], "Should redirect to /login"


def test_post_add_expense_redirects_when_logged_out_and_inserts_nothing():
    with app_module.app.test_client() as client:
        db = db_module.get_db()
        before = db.execute("SELECT COUNT(*) AS c FROM expenses").fetchone()["c"]
        db.close()

        response = client.post(
            "/expenses/add", data=valid_expense_form(), follow_redirects=False
        )

        assert response.status_code == 302, "POST while logged out should redirect"
        assert "/login" in response.headers["Location"], "Should redirect to /login"

        db = db_module.get_db()
        after = db.execute("SELECT COUNT(*) AS c FROM expenses").fetchone()["c"]
        db.close()
        assert after == before, "No expense row should be inserted for an anonymous request"


# ------------------------------------------------------------------ #
# Happy path                                                          #
# ------------------------------------------------------------------ #

def test_get_add_expense_renders_form_when_logged_in():
    with app_module.app.test_client() as client:
        register_and_login(client, prefix="formview")

        response = client.get("/expenses/add")
        html = response.get_data(as_text=True)
        lowered = html.lower()

        assert response.status_code == 200, "Logged-in GET should render the form, not redirect"
        assert "amount" in lowered, "Form should mention an amount field"
        assert "category" in lowered, "Form should mention a category field"
        assert "date" in lowered, "Form should mention a date field"
        assert "description" in lowered, "Form should mention a description field"
        for category in EXPENSE_CATEGORIES:
            assert category in html, f"Category '{category}' should be offered as an option"


def test_post_add_expense_valid_data_inserts_row_scoped_to_user_and_redirects_to_profile():
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="happypath")

        response = client.post(
            "/expenses/add",
            data=valid_expense_form(
                amount="50.25", category="Food", date="2026-01-15", description="Weekly lunch"
            ),
            follow_redirects=False,
        )

        assert response.status_code == 302, "Valid submission should redirect"
        assert "/profile" in response.headers["Location"], "Should redirect to /profile"

        rows = fetch_expenses_for_user(user_id)
        assert len(rows) == 1, "Exactly one expense row should be inserted for this user"
        row = rows[0]
        assert row["user_id"] == user_id, "Expense must be scoped to the logged-in user"
        assert row["amount"] == pytest.approx(50.25), "Amount should be stored as submitted"
        assert row["category"] == "Food", "Category should be stored as submitted"
        assert row["date"] == "2026-01-15", "Date should be stored as submitted"
        assert row["description"] == "Weekly lunch", "Description should be stored as submitted"


def test_new_expense_appears_on_profile_page_immediately():
    with app_module.app.test_client() as client:
        register_and_login(client, prefix="reflect")

        client.post(
            "/expenses/add",
            data=valid_expense_form(
                amount="75.00", category="Entertainment", date="2026-02-01",
                description="Concert tickets",
            ),
            follow_redirects=False,
        )

        html = client.get("/profile").get_data(as_text=True)

        assert "Concert tickets" in html, "New expense description should show in the transaction list"
        assert "Entertainment" in html, "New expense category should show on the profile page"
        assert "₹75.00" in html, "Total spent / amount should reflect the newly added expense"


# ------------------------------------------------------------------ #
# Validation — amount                                                 #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "amount_value",
    ["", "0", "-10", "abc"],
    ids=["missing", "zero", "negative", "non_numeric"],
)
def test_post_add_expense_invalid_amount_rerenders_form_without_inserting(amount_value):
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="amt")

        response = client.post(
            "/expenses/add",
            data=valid_expense_form(amount=amount_value),
            follow_redirects=False,
        )
        html = response.get_data(as_text=True)

        assert response.status_code == 200, "Invalid amount should re-render the form, not redirect"
        assert "amount" in html.lower(), "Form should be shown again on validation failure"
        assert expense_count_for_user(user_id) == 0, "No row should be inserted for an invalid amount"


# ------------------------------------------------------------------ #
# Validation — category                                               #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "category_value",
    ["", "NotARealCategory"],
    ids=["missing", "invalid"],
)
def test_post_add_expense_invalid_category_rerenders_form_without_inserting(category_value):
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="cat")

        response = client.post(
            "/expenses/add",
            data=valid_expense_form(category=category_value),
            follow_redirects=False,
        )
        html = response.get_data(as_text=True)

        assert response.status_code == 200, "Invalid category should re-render the form, not redirect"
        assert "category" in html.lower(), "Form should be shown again on validation failure"
        assert expense_count_for_user(user_id) == 0, "No row should be inserted for an invalid category"


# ------------------------------------------------------------------ #
# Validation — date                                                   #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "date_value",
    ["", "not-a-date", "2026-13-40"],
    ids=["missing", "non_date_string", "invalid_calendar_date"],
)
def test_post_add_expense_invalid_date_rerenders_form_without_inserting(date_value):
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="date")

        response = client.post(
            "/expenses/add",
            data=valid_expense_form(date=date_value),
            follow_redirects=False,
        )
        html = response.get_data(as_text=True)

        assert response.status_code == 200, "Invalid date should re-render the form, not redirect"
        assert "date" in html.lower(), "Form should be shown again on validation failure"
        assert expense_count_for_user(user_id) == 0, "No row should be inserted for an invalid date"


# ------------------------------------------------------------------ #
# Description is optional                                             #
# ------------------------------------------------------------------ #

def test_post_add_expense_without_description_still_succeeds():
    with app_module.app.test_client() as client:
        _, user_id = register_and_login(client, prefix="nodesc")

        form = valid_expense_form()
        del form["description"]

        response = client.post("/expenses/add", data=form, follow_redirects=False)

        assert response.status_code == 302, "A missing description should not block a valid submission"
        assert "/profile" in response.headers["Location"], "Should redirect to /profile"

        rows = fetch_expenses_for_user(user_id)
        assert len(rows) == 1, "Expense should be inserted even without a description"
        assert rows[0]["description"] in (None, ""), "Description should be stored empty/NULL when omitted"
