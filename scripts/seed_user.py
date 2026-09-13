import random
from datetime import datetime

from werkzeug.security import generate_password_hash

from database.db import get_db

FIRST_NAMES = [
    "Rahul", "Priya", "Amit", "Sneha", "Vikram", "Ananya", "Arjun", "Divya",
    "Karthik", "Meera", "Rohan", "Kavya", "Suresh", "Pooja", "Aditya", "Ishita",
    "Manoj", "Neha", "Siddharth", "Lakshmi", "Farhan", "Zara", "Gurpreet", "Simran",
    "Nikhil", "Ritu", "Harish", "Swati", "Vivek", "Anjali",
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Iyer", "Nair", "Gupta", "Singh",
    "Rao", "Menon", "Kulkarni", "Joshi", "Chatterjee", "Bose", "Mukherjee",
    "Das", "Pillai", "Naidu", "Chowdhury", "Khan", "Bhat", "Desai", "Kapoor",
    "Malhotra", "Agarwal", "Trivedi", "Shetty", "Pandey", "Mehta", "Bansal",
]


def generate_user():
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    name = f"{first} {last}"
    number = random.randint(10, 999)
    email = f"{first.lower()}.{last.lower()}{number}@gmail.com"
    return name, email


def unique_email(db):
    while True:
        name, email = generate_user()
        existing = db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if not existing:
            return name, email


def main():
    db = get_db()

    name, email = unique_email(db)
    password_hash = generate_password_hash("password123")
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor = db.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, created_at),
    )
    db.commit()
    user_id = cursor.lastrowid
    db.close()

    print("Created user:")
    print(f"  id:    {user_id}")
    print(f"  name:  {name}")
    print(f"  email: {email}")


if __name__ == "__main__":
    main()
