import os
from datetime import datetime, timedelta

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not name:
        return render_template(
            "register.html", error="Full name is required.", name=name, email=email
        )

    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return render_template(
            "register.html",
            error="Enter a valid email address.",
            name=name,
            email=email,
        )

    if len(password) < 8:
        return render_template(
            "register.html",
            error="Password must be at least 8 characters.",
            name=name,
            email=email,
        )

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        db.close()
        return render_template(
            "register.html",
            error="An account with this email already exists.",
            name=name,
            email=email,
        )

    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    db.commit()
    db.close()

    return redirect(url_for("login", registered="1"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    db = get_db()
    user = db.execute(
        "SELECT id, name, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    db.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return render_template(
            "login.html", error="Invalid email or password.", email=email
        )

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session["user_email"] = email

    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def _is_valid_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


EXPENSE_CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


def resolve_profile_date_filter(args):
    """Resolve the /profile date-range filter from query args.

    Falls back to "no filter" (all-time) whenever start/end are missing,
    only one is supplied, or either fails to parse as YYYY-MM-DD. An end
    date before a start date is intentionally not special-cased here: it is
    passed through to the SQL BETWEEN clause, which naturally matches zero
    rows when end < start.
    """
    today = datetime.now().date()

    month_start = today.replace(day=1)
    month_range = {"start": month_start.isoformat(), "end": today.isoformat()}

    last30_start = today - timedelta(days=29)
    last30_range = {"start": last30_start.isoformat(), "end": today.isoformat()}

    raw_start = (args.get("start") or "").strip()
    raw_end = (args.get("end") or "").strip()
    start_ok = bool(raw_start) and _is_valid_date(raw_start)
    end_ok = bool(raw_end) and _is_valid_date(raw_end)

    filter_active = start_ok and end_ok

    if filter_active:
        start, end = raw_start, raw_end
        if (start, end) == (month_range["start"], month_range["end"]):
            active_preset = "month"
        elif (start, end) == (last30_range["start"], last30_range["end"]):
            active_preset = "last30"
        else:
            active_preset = "custom"
    else:
        start, end = None, None
        active_preset = "all"

    return {
        "filter_active": filter_active,
        "start": start,
        "end": end,
        "active_preset": active_preset,
        "month_range": month_range,
        "last30_range": last30_range,
        "form_start": raw_start if start_ok else "",
        "form_end": raw_end if end_ok else "",
    }


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    user_id = session["user_id"]

    date_filter = resolve_profile_date_filter(request.args)
    date_clause = " AND date BETWEEN ? AND ?" if date_filter["filter_active"] else ""
    date_params = (
        (date_filter["start"], date_filter["end"])
        if date_filter["filter_active"]
        else ()
    )

    # === SECTION: SUMMARY (owned by Subagent 2) ===
    user_row = db.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    name = user_row["name"] or ""
    name_parts = name.split()
    initials = "".join(part[0].upper() for part in name_parts[:2]) or "?"
    member_since = datetime.strptime(
        user_row["created_at"], "%Y-%m-%d %H:%M:%S"
    ).strftime("%B %Y")

    user = {
        "name": name,
        "email": user_row["email"],
        "initials": initials,
        "member_since": member_since,
    }

    total_row = db.execute(
        f"SELECT SUM(amount) AS total, COUNT(*) AS count FROM expenses "
        f"WHERE user_id = ?{date_clause}",
        (user_id,) + date_params,
    ).fetchone()
    total_spent = total_row["total"] or 0
    transaction_count = total_row["count"] or 0

    top_category_row = db.execute(
        f"""
        SELECT category
        FROM expenses
        WHERE user_id = ?{date_clause}
        GROUP BY category
        ORDER BY SUM(amount) DESC
        LIMIT 1
        """,
        (user_id,) + date_params,
    ).fetchone()
    top_category = top_category_row["category"] if top_category_row else "—"

    stats = [
        {"label": "Total Spent", "value": f"₹{total_spent:.2f}"},
        {"label": "Transactions", "value": str(transaction_count)},
        {"label": "Top Category", "value": top_category},
    ]

    # === SECTION: TRANSACTIONS (owned by Subagent 1) ===
    rows = db.execute(
        f"SELECT id, date, description, category, amount FROM expenses "
        f"WHERE user_id = ?{date_clause} "
        f"ORDER BY date DESC, id DESC LIMIT 10",
        (user_id,) + date_params,
    ).fetchall()

    transactions = [
        {
            "id": row["id"],
            "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%b %d, %Y"),
            "description": row["description"],
            "category": row["category"],
            "amount": f"₹{row['amount']:.2f}",
        }
        for row in rows
    ]

    # === SECTION: CATEGORY BREAKDOWN (owned by Subagent 3) ===
    rows = db.execute(
        f"SELECT category, SUM(amount) AS total FROM expenses "
        f"WHERE user_id = ?{date_clause} "
        f"GROUP BY category ORDER BY total DESC",
        (user_id,) + date_params,
    ).fetchall()

    grand_total = sum(row["total"] for row in rows)

    categories = []
    if grand_total:
        pcts = [round((row["total"] / grand_total) * 100) for row in rows]

        remainder = 100 - sum(pcts)
        if remainder:
            largest_idx = max(range(len(rows)), key=lambda i: rows[i]["total"])
            pcts[largest_idx] += remainder

        for row, pct in zip(rows, pcts):
            categories.append(
                {
                    "name": row["category"],
                    "amount": f"₹{row['total']:.2f}",
                    "modifier": "progress-bar-" + row["category"].lower(),
                    "pct": pct,
                }
            )

    db.close()

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        date_filter=date_filter,
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    today = datetime.now().date().isoformat()

    if request.method == "GET":
        return render_template(
            "add_expense.html", categories=EXPENSE_CATEGORIES, today=today
        )

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    try:
        amount = float(amount_raw)
    except ValueError:
        amount = None

    if amount is None or amount <= 0:
        return render_template(
            "add_expense.html",
            categories=EXPENSE_CATEGORIES,
            today=today,
            error="Enter a valid amount greater than zero.",
            amount=amount_raw,
            category=category,
            date=date,
            description=description,
        )

    if not category or category not in EXPENSE_CATEGORIES:
        return render_template(
            "add_expense.html",
            categories=EXPENSE_CATEGORIES,
            today=today,
            error="Select a valid category.",
            amount=amount_raw,
            category=category,
            date=date,
            description=description,
        )

    if not date or not _is_valid_date(date):
        return render_template(
            "add_expense.html",
            categories=EXPENSE_CATEGORIES,
            today=today,
            error="Enter a valid date.",
            amount=amount_raw,
            category=category,
            date=date,
            description=description,
        )

    db = get_db()
    db.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (session["user_id"], amount, category, date, description or None),
    )
    db.commit()
    db.close()

    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    expense = db.execute(
        "SELECT id, amount, category, date, description FROM expenses WHERE id = ? AND user_id = ?",
        (id, session["user_id"]),
    ).fetchone()

    if expense is None:
        db.close()
        return redirect(url_for("profile"))

    if request.method == "GET":
        db.close()
        return render_template(
            "edit_expense.html",
            categories=EXPENSE_CATEGORIES,
            id=id,
            amount=expense["amount"],
            category=expense["category"],
            date=expense["date"],
            description=expense["description"],
        )

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    try:
        amount = float(amount_raw)
    except ValueError:
        amount = None

    if amount is None or amount <= 0:
        db.close()
        return render_template(
            "edit_expense.html",
            categories=EXPENSE_CATEGORIES,
            id=id,
            error="Enter a valid amount greater than zero.",
            amount=amount_raw,
            category=category,
            date=date,
            description=description,
        )

    if not category or category not in EXPENSE_CATEGORIES:
        db.close()
        return render_template(
            "edit_expense.html",
            categories=EXPENSE_CATEGORIES,
            id=id,
            error="Select a valid category.",
            amount=amount_raw,
            category=category,
            date=date,
            description=description,
        )

    if not date or not _is_valid_date(date):
        db.close()
        return render_template(
            "edit_expense.html",
            categories=EXPENSE_CATEGORIES,
            id=id,
            error="Enter a valid date.",
            amount=amount_raw,
            category=category,
            date=date,
            description=description,
        )

    db.execute(
        "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
        "WHERE id = ? AND user_id = ?",
        (amount, category, date, description or None, id, session["user_id"]),
    )
    db.commit()
    db.close()

    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
