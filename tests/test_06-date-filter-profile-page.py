"""Tests for Step 6 — Date Filter for Profile Page.

Spec: .claude/specs/06-date-filter-profile-page.md

These tests target the *behavior* described in the spec's Routes, Rules for
implementation, and Definition of done sections:
  - `GET /profile` with no `start`/`end` params behaves exactly as before
    (all-time totals) and is still auth-guarded.
  - A valid `start`+`end` range scopes the summary stats, transaction list,
    and category breakdown to `date BETWEEN start AND end` (inclusive).
  - The "This Month" and "Last 30 Days" presets scope to the current
    calendar month / trailing 30-day window (computed from "now", not
    hardcoded), and mark themselves active in the filter bar.
  - Missing one of start/end, malformed dates, or start-after-end must never
    500 — the first two fall back to all-time, the last must return an
    *empty* result set (not all-time, not an error).

Each test gets its own isolated, freshly-initialized SQLite file (via
monkeypatching `database.db.DB_PATH` + calling `init_db()`), so tests never
depend on shared/global state or on the import order of other test modules.
"""

import html
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta

import pytest

import database.db as db_module

# Guard the very first import of `app` (which runs `init_db()` / `seed_db()`
# at module scope) so it never touches the real dev database, but don't
# clobber DB_PATH if some other test module already imported `app` first.
if "app" not in sys.modules:
    db_module.DB_PATH = os.path.join(
        tempfile.mkdtemp(), "test_date_filter_profile_page_import.db"
    )

import app as app_module  # noqa: E402

app_module.app.config["TESTING"] = True


# ------------------------------------------------------------------ #
# Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def client(monkeypatch):
    """A test client backed by a fresh, isolated, empty SQLite database."""
    tmp_path = os.path.join(tempfile.mkdtemp(), "profile_filter_test.db")
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path)
    db_module.init_db()
    return app_module.app.test_client()


@pytest.fixture
def demo_client(client):
    """A logged-in client for the seeded demo user (from seed_db())."""
    db_module.seed_db()
    login(client, email="demo@spendly.com", password="demo123")
    return client


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def register(client, name, email, password="testpass123"):
    return client.post(
        "/register",
        data={"name": name, "email": email, "password": password},
        follow_redirects=False,
    )


def login(client, email, password):
    return client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=True
    )


def register_and_login(client, name, email, password="testpass123"):
    register(client, name=name, email=email, password=password)
    login(client, email=email, password=password)


def insert_expense(email, amount, category, date, description):
    """Insert an expense row directly for the user with the given email."""
    db = db_module.get_db()
    user = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    assert user is not None, f"No such user: {email}"
    db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user["id"], amount, category, date, description),
    )
    db.commit()
    db.close()


def stat_value_present(html_text, value):
    """Whether a `.stat-value` element renders exactly `value`."""
    return f'<span class="stat-value">{value}</span>' in html_text


def get_input_value(html_text, input_name):
    """The `value="..."` of the `<input name="input_name">` field, if any."""
    match = re.search(r'name="' + re.escape(input_name) + r'"[^>]*value="([^"]*)"', html_text)
    return match.group(1) if match else None


def get_link_href(html_text, link_text):
    """The `href` of the `<a ...>link_text</a>` element."""
    marker = f">{link_text}<"
    for piece in html_text.split("<a "):
        if marker in piece:
            match = re.search(r'href="([^"]*)"', piece)
            if match:
                return html.unescape(match.group(1))
    raise AssertionError(f"Could not find a link with text {link_text!r} in the page")


def is_link_active(html_text, link_text):
    """Whether the `<a ...>link_text</a>` element carries the is-active class."""
    marker = f">{link_text}<"
    for piece in html_text.split("<a "):
        if marker in piece:
            opening_tag = piece.split(marker)[0]
            return "is-active" in opening_tag
    raise AssertionError(f"Could not find a link with text {link_text!r} in the page")


# Ground truth for database/db.py's seed_db() sample_expenses:
# 45.50 + 12.00 + 89.99 + 32.00 + 25.00 + 60.75 + 15.00 + 22.30 = 302.54
SEED_ALL_TIME_TOTAL = "₹302.54"
SEED_DESCRIPTIONS = [
    "Weekly grocery run",
    "Metro card top-up",
    "Electricity bill",
    "Pharmacy purchase",
    "Movie tickets",
    "New shoes",
    "Miscellaneous supplies",
    "Dinner out",
]


# ------------------------------------------------------------------ #
# Auth guard                                                          #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "query_string",
    [
        "",
        "?start=2026-09-01&end=2026-09-08",
        "?start=not-a-date&end=2026-09-01",
        "?start=2026-09-30&end=2026-09-01",
    ],
)
def test_profile_redirects_to_login_when_unauthenticated(client, query_string):
    response = client.get("/profile" + query_string)
    assert response.status_code == 302, "Unauthenticated /profile must redirect, not 200"
    assert "/login" in response.headers["Location"], "Must redirect to the login page"


# ------------------------------------------------------------------ #
# No filter params -> unchanged all-time behavior                     #
# ------------------------------------------------------------------ #

def test_profile_no_query_params_shows_all_time_totals(demo_client):
    response = demo_client.get("/profile")
    html_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert stat_value_present(html_text, SEED_ALL_TIME_TOTAL)
    assert stat_value_present(html_text, "8")
    assert stat_value_present(html_text, "Bills")  # highest single-category total
    for description in SEED_DESCRIPTIONS:
        assert description in html_text

    assert is_link_active(html_text, "All Time"), "'All Time' should be active with no params"
    assert not is_link_active(html_text, "This Month")
    assert not is_link_active(html_text, "Last 30 Days")


def test_profile_all_time_link_has_no_date_params(demo_client):
    html_text = demo_client.get("/profile").get_data(as_text=True)
    assert get_link_href(html_text, "All Time") == "/profile"


# ------------------------------------------------------------------ #
# Custom range narrows results                                        #
# ------------------------------------------------------------------ #

def test_profile_custom_range_narrows_all_three_sections(demo_client):
    response = demo_client.get("/profile?start=2026-09-01&end=2026-09-08")
    html_text = response.get_data(as_text=True)

    assert response.status_code == 200

    # Included: Food 45.50 + Transport 12.00 + Bills 89.99 + Health 32.00
    #           + Entertainment 25.00 = 204.49, 5 transactions.
    assert stat_value_present(html_text, "₹204.49")
    assert stat_value_present(html_text, "5")
    assert stat_value_present(html_text, "Bills")

    included = [
        "Weekly grocery run",
        "Metro card top-up",
        "Electricity bill",
        "Pharmacy purchase",
        "Movie tickets",
    ]
    excluded = ["New shoes", "Miscellaneous supplies", "Dinner out"]

    for description in included:
        assert description in html_text
    for description in excluded:
        assert description not in html_text

    # Category breakdown should only contain in-range categories.
    assert '<span class="progress-amount">₹45.50</span>' in html_text  # Food
    assert '<span class="progress-amount">₹12.00</span>' in html_text  # Transport
    assert '<span class="progress-amount">₹89.99</span>' in html_text  # Bills
    assert '<span class="progress-amount">₹32.00</span>' in html_text  # Health
    assert '<span class="progress-amount">₹25.00</span>' in html_text  # Entertainment
    assert '<span class="progress-amount">₹60.75</span>' not in html_text  # Shopping
    assert '<span class="progress-amount">₹15.00</span>' not in html_text  # Other

    assert get_input_value(html_text, "start") == "2026-09-01"
    assert get_input_value(html_text, "end") == "2026-09-08"


def test_profile_custom_range_is_inclusive_of_both_boundaries(demo_client):
    """A single-day range should match an expense dated on exactly that day."""
    response = demo_client.get("/profile?start=2026-09-05&end=2026-09-05")
    html_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert stat_value_present(html_text, "₹89.99")
    assert stat_value_present(html_text, "1")
    assert "Electricity bill" in html_text
    for description in SEED_DESCRIPTIONS:
        if description != "Electricity bill":
            assert description not in html_text


def test_profile_custom_range_prefills_inputs_and_marks_custom_active(demo_client):
    response = demo_client.get("/profile?start=2020-01-01&end=2020-01-31")
    html_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert get_input_value(html_text, "start") == "2020-01-01"
    assert get_input_value(html_text, "end") == "2020-01-31"
    assert "profile-filter-custom is-active" in html_text
    # No seed expenses fall in this range -> empty, but no error.
    assert stat_value_present(html_text, "₹0.00")
    assert stat_value_present(html_text, "0")


# ------------------------------------------------------------------ #
# Preset ranges: "This Month" and "Last 30 Days"                      #
# ------------------------------------------------------------------ #

def test_profile_this_month_preset_filters_to_current_calendar_month(client):
    email = "month.user@example.com"
    register_and_login(client, name="Month User", email=email)

    today = datetime.now().date()
    month_start = today.replace(day=1)
    prev_month_last_day = month_start - timedelta(days=1)

    insert_expense(email, 10.00, "Food", month_start.isoformat(), "InMonthStart")
    insert_expense(email, 20.00, "Food", today.isoformat(), "InMonthToday")
    insert_expense(email, 30.00, "Food", prev_month_last_day.isoformat(), "PrevMonthExpense")

    baseline_html = client.get("/profile").get_data(as_text=True)
    href = get_link_href(baseline_html, "This Month")

    response = client.get(href)
    html_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "InMonthStart" in html_text
    assert "InMonthToday" in html_text
    assert "PrevMonthExpense" not in html_text, "Previous month's expense must be excluded"
    assert is_link_active(html_text, "This Month")
    assert not is_link_active(html_text, "All Time")
    assert not is_link_active(html_text, "Last 30 Days")


def test_profile_last_30_days_preset_filters_trailing_window(client):
    email = "last30.user@example.com"
    register_and_login(client, name="Last30 User", email=email)

    today = datetime.now().date()
    recent = today - timedelta(days=10)
    old = today - timedelta(days=45)

    insert_expense(email, 15.00, "Food", today.isoformat(), "TodayExpense")
    insert_expense(email, 25.00, "Food", recent.isoformat(), "RecentExpense")
    insert_expense(email, 35.00, "Food", old.isoformat(), "OldExpense")

    baseline_html = client.get("/profile").get_data(as_text=True)
    href = get_link_href(baseline_html, "Last 30 Days")

    response = client.get(href)
    html_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "TodayExpense" in html_text
    assert "RecentExpense" in html_text
    assert "OldExpense" not in html_text, "An expense 45 days old must fall outside the window"
    assert is_link_active(html_text, "Last 30 Days")
    assert not is_link_active(html_text, "All Time")
    assert not is_link_active(html_text, "This Month")


# ------------------------------------------------------------------ #
# Invalid / partial input -> must never 500                           #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "query_string",
    [
        "start=2026-09-05",
        "end=2026-09-05",
        "start=&end=2026-09-05",
        "start=2026-09-05&end=",
    ],
)
def test_profile_partial_date_params_fall_back_to_all_time(demo_client, query_string):
    response = demo_client.get(f"/profile?{query_string}")
    html_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert stat_value_present(html_text, SEED_ALL_TIME_TOTAL), (
        f"Partial filter params {query_string!r} must fall back to all-time totals"
    )


@pytest.mark.parametrize(
    "start,end",
    [
        ("not-a-date", "2026-09-01"),
        ("2026-13-40", "2026-09-01"),
        ("2026/09/01", "2026-09-05"),
        ("", ""),
    ],
)
def test_profile_malformed_dates_fall_back_to_all_time(demo_client, start, end):
    response = demo_client.get("/profile", query_string={"start": start, "end": end})
    html_text = response.get_data(as_text=True)

    assert response.status_code == 200, "Malformed date input must never cause a 500"
    assert stat_value_present(html_text, SEED_ALL_TIME_TOTAL)


def test_profile_malicious_date_param_does_not_error_and_falls_back(demo_client):
    """A SQL-injection-shaped value is just an invalid date string; must not 500
    or leak data through string-formatted SQL — parameterised queries only."""
    response = demo_client.get(
        "/profile", query_string={"start": "2026-01-01' OR '1'='1", "end": "2026-12-31"}
    )
    html_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert stat_value_present(html_text, SEED_ALL_TIME_TOTAL)


def test_profile_end_before_start_returns_empty_result_not_all_time(demo_client):
    response = demo_client.get("/profile?start=2026-09-30&end=2026-09-01")
    html_text = response.get_data(as_text=True)

    assert response.status_code == 200, "start-after-end must never cause a 500"
    assert stat_value_present(html_text, "₹0.00")
    assert stat_value_present(html_text, "0")
    assert SEED_ALL_TIME_TOTAL not in html_text, "Must not silently fall back to all-time"

    for description in SEED_DESCRIPTIONS:
        assert description not in html_text
    assert 'class="progress-row"' not in html_text, "Category breakdown must be empty"


def test_profile_out_of_range_dates_show_zero_state_without_error(demo_client):
    """DoD: a user with no expenses in the selected range sees ₹0.00 total,
    0 transactions, and an empty category breakdown — no errors."""
    response = demo_client.get("/profile?start=2026-01-01&end=2026-01-31")
    html_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert stat_value_present(html_text, "₹0.00")
    assert stat_value_present(html_text, "0")
    assert stat_value_present(html_text, "—")  # top-category placeholder
    for description in SEED_DESCRIPTIONS:
        assert description not in html_text
    assert 'class="progress-row"' not in html_text


# ------------------------------------------------------------------ #
# Template landmarks                                                  #
# ------------------------------------------------------------------ #

def test_profile_page_renders_filter_bar_controls(demo_client):
    html_text = demo_client.get("/profile").get_data(as_text=True)

    assert "All Time" in html_text
    assert "This Month" in html_text
    assert "Last 30 Days" in html_text
    assert 'method="get"' in html_text
    assert 'name="start"' in html_text
    assert 'name="end"' in html_text
    assert re.search(r'<button[^>]*type="submit"[^>]*>\s*Apply\s*</button>', html_text)
