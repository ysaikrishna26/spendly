import os
from datetime import datetime

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
        return render_template("register.html", error="Full name is required.", name=name, email=email)

    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return render_template("register.html", error="Enter a valid email address.", name=name, email=email)

    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.", name=name, email=email)

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
        return render_template("login.html", error="Invalid email or password.", email=email)

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


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    user_id = session["user_id"]

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
        "SELECT SUM(amount) AS total, COUNT(*) AS count FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    total_spent = total_row["total"] or 0
    transaction_count = total_row["count"] or 0

    top_category_row = db.execute(
        """
        SELECT category
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY SUM(amount) DESC
        LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    top_category = top_category_row["category"] if top_category_row else "—"

    stats = [
        {"label": "Total Spent", "value": f"₹{total_spent:.2f}"},
        {"label": "Transactions", "value": str(transaction_count)},
        {"label": "Top Category", "value": top_category},
    ]

    # === SECTION: TRANSACTIONS (owned by Subagent 1) ===
    rows = db.execute(
        "SELECT date, description, category, amount FROM expenses "
        "WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT 10",
        (user_id,),
    ).fetchall()

    transactions = [
        {
            "date": datetime.strptime(row["date"], "%Y-%m-%d").strftime("%b %d, %Y"),
            "description": row["description"],
            "category": row["category"],
            "amount": f"₹{row['amount']:.2f}",
        }
        for row in rows
    ]

    # === SECTION: CATEGORY BREAKDOWN (owned by Subagent 3) ===
    rows = db.execute(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "WHERE user_id = ? GROUP BY category ORDER BY total DESC",
        (user_id,),
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
            categories.append({
                "name": row["category"],
                "amount": f"₹{row['total']:.2f}",
                "modifier": "progress-bar-" + row["category"].lower(),
                "pct": pct,
            })

    db.close()

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
