import os
import tempfile

import database.db as db_module

# Point the app at a throwaway SQLite file before importing `app`, so the
# module-level `init_db()` / `seed_db()` call in app.py never touches the
# real dev database (expense_tracker.db).
db_module.DB_PATH = os.path.join(tempfile.mkdtemp(), "test_backend_connection.db")

import app as app_module  # noqa: E402

app_module.app.config["TESTING"] = True


def login(client, email="demo@spendly.com", password="demo123"):
    return client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=True
    )


def register(client, name, email, password="testpass123"):
    return client.post(
        "/register",
        data={"name": name, "email": email, "password": password},
        follow_redirects=False,
    )


def test_profile_redirects_when_logged_out():
    with app_module.app.test_client() as client:
        response = client.get("/profile")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_profile_authenticated_returns_200():
    with app_module.app.test_client() as client:
        login(client)
        response = client.get("/profile")
        assert response.status_code == 200


def test_profile_shows_seed_user_identity():
    with app_module.app.test_client() as client:
        login(client)
        html = client.get("/profile").get_data(as_text=True)
        assert "Demo User" in html
        assert "demo@spendly.com" in html


def test_profile_summary_stats_for_seed_user():
    with app_module.app.test_client() as client:
        login(client)
        html = client.get("/profile").get_data(as_text=True)
        # Sum of database/db.py's seed_db() sample_expenses: 45.50 + 12.00 +
        # 89.99 + 32.00 + 25.00 + 60.75 + 15.00 + 22.30 = 302.54
        assert "₹302.54" in html
        assert "8" in html
        assert "Bills" in html  # highest single-category total (89.99)


def test_profile_transactions_are_newest_first():
    with app_module.app.test_client() as client:
        login(client)
        html = client.get("/profile").get_data(as_text=True)
        assert html.index("Dinner out") < html.index("Weekly grocery run")


def test_profile_shows_all_seed_categories():
    with app_module.app.test_client() as client:
        login(client)
        html = client.get("/profile").get_data(as_text=True)
        for category in [
            "Food",
            "Transport",
            "Bills",
            "Health",
            "Entertainment",
            "Shopping",
            "Other",
        ]:
            assert category in html


def test_profile_uses_rupee_symbol():
    with app_module.app.test_client() as client:
        login(client)
        html = client.get("/profile").get_data(as_text=True)
        assert "₹" in html


def test_profile_empty_state_for_new_user():
    with app_module.app.test_client() as client:
        register(client, "Fresh User", "fresh.user@example.com")
        login(client, email="fresh.user@example.com", password="testpass123")
        response = client.get("/profile")
        html = response.get_data(as_text=True)

        assert response.status_code == 200
        assert "₹0.00" in html
        assert "—" in html  # top category placeholder when there are no expenses
