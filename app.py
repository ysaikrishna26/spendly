import os

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

    name = session.get("user_name", "")
    initials = "".join(part[0].upper() for part in name.split()[:2]) or "?"

    user = {
        "name": name,
        "email": session.get("user_email", ""),
        "initials": initials,
        "member_since": "September 2026",
    }

    stats = [
        {"label": "Total Spent", "value": "$292.54"},
        {"label": "Transactions", "value": "8"},
        {"label": "Top Category", "value": "Food"},
    ]

    transactions = [
        {"date": "Sep 15, 2026", "description": "Dinner out", "category": "Food", "amount": "$22.30"},
        {"date": "Sep 11, 2026", "description": "New shoes", "category": "Shopping", "amount": "$60.75"},
        {"date": "Sep 8, 2026", "description": "Movie tickets", "category": "Entertainment", "amount": "$25.00"},
        {"date": "Sep 5, 2026", "description": "Electricity bill", "category": "Bills", "amount": "$89.99"},
        {"date": "Sep 3, 2026", "description": "Metro card top-up", "category": "Transport", "amount": "$12.00"},
    ]

    categories = [
        {"name": "Food", "amount": "$67.80", "modifier": "progress-bar-food"},
        {"name": "Bills", "amount": "$89.99", "modifier": "progress-bar-bills"},
        {"name": "Transport", "amount": "$12.00", "modifier": "progress-bar-transport"},
        {"name": "Entertainment", "amount": "$25.00", "modifier": "progress-bar-entertainment"},
    ]

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
