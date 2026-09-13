# Students will write this file in Step 1 — Database Setup
# This file should contain:
#   get_db()   — returns a SQLite connection with row_factory and foreign keys enabled
#   init_db()  — creates all tables using CREATE TABLE IF NOT EXISTS
#   seed_db()  — inserts sample data for development

import os
import sqlite3

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "expense_tracker.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    """)
    conn.commit()
    conn.close()


def seed_db():
    conn = get_db()

    if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone():
        conn.close()
        return

    user_id = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
    ).lastrowid

    sample_expenses = [
        (user_id, 45.50, "Food", "2026-09-01", "Weekly grocery run"),
        (user_id, 12.00, "Transport", "2026-09-03", "Metro card top-up"),
        (user_id, 89.99, "Bills", "2026-09-05", "Electricity bill"),
        (user_id, 32.00, "Health", "2026-09-07", "Pharmacy purchase"),
        (user_id, 25.00, "Entertainment", "2026-09-08", "Movie tickets"),
        (user_id, 60.75, "Shopping", "2026-09-11", "New shoes"),
        (user_id, 15.00, "Other", "2026-09-13", "Miscellaneous supplies"),
        (user_id, 22.30, "Food", "2026-09-15", "Dinner out"),
    ]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        sample_expenses,
    )

    conn.commit()
    conn.close()
