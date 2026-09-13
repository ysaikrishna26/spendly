import random
import sys
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from database.db import get_db

# (category, weight, min_amount, max_amount, descriptions)
CATEGORIES = [
    ("Food", 30, 50, 800, [
        "Lunch at Saravana Bhavan", "Zomato order", "Swiggy dinner delivery",
        "Grocery run at DMart", "Tea and snacks", "Weekend biryani",
        "Vegetable market shopping", "Office cafeteria", "Street food",
        "Bakery items",
    ]),
    ("Transport", 22, 20, 500, [
        "Ola cab ride", "Uber to office", "Metro card recharge",
        "Auto rickshaw fare", "Petrol top-up", "Bus pass renewal",
        "Parking fee", "Rapido bike ride",
    ]),
    ("Bills", 16, 200, 3000, [
        "Electricity bill", "Mobile recharge", "Broadband bill",
        "Water bill", "Gas cylinder booking", "DTH recharge",
        "Society maintenance",
    ]),
    ("Shopping", 16, 200, 5000, [
        "Myntra order", "Amazon purchase", "New clothes",
        "Footwear purchase", "Home decor items", "Flipkart order",
    ]),
    ("Other", 8, 50, 1000, [
        "Miscellaneous expense", "Gift for a friend", "Donation",
        "Courier charges", "Stationery purchase",
    ]),
    ("Entertainment", 5, 100, 1500, [
        "Movie tickets at PVR", "Netflix subscription", "Concert tickets",
        "Bowling with friends", "Spotify Premium",
    ]),
    ("Health", 3, 100, 2000, [
        "Pharmacy purchase", "Doctor consultation", "Gym membership",
        "Health checkup", "Dental appointment",
    ]),
]


def parse_args():
    if len(sys.argv) != 4:
        print("Usage: python -m scripts.seed_expenses <user_id> <count> <months>")
        print("Example: python -m scripts.seed_expenses 1 50 6")
        sys.exit(1)
    try:
        user_id = int(sys.argv[1])
        count = int(sys.argv[2])
        months = int(sys.argv[3])
    except ValueError:
        print("Usage: python -m scripts.seed_expenses <user_id> <count> <months>")
        print("Example: python -m scripts.seed_expenses 1 50 6")
        sys.exit(1)
    return user_id, count, months


def pick_category():
    names = [c[0] for c in CATEGORIES]
    weights = [c[1] for c in CATEGORIES]
    return random.choices(names, weights=weights, k=1)[0]


def category_info(name):
    for cat_name, _, lo, hi, descriptions in CATEGORIES:
        if cat_name == name:
            return lo, hi, descriptions
    raise ValueError(name)


def random_date(months):
    today = datetime.now()
    earliest = today - timedelta(days=months * 30)
    delta_days = (today - earliest).days
    offset = random.randint(0, delta_days)
    return (earliest + timedelta(days=offset)).strftime("%Y-%m-%d")


def generate_expenses(user_id, count, months):
    expenses = []
    for _ in range(count):
        category = pick_category()
        lo, hi, descriptions = category_info(category)
        amount = round(random.uniform(lo, hi), 2)
        description = random.choice(descriptions)
        date = random_date(months)
        expenses.append((user_id, amount, category, date, description))
    return expenses


def main():
    user_id, count, months = parse_args()

    db = get_db()

    user = db.execute("SELECT id, name FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        print(f"No user found with id {user_id}.")
        db.close()
        sys.exit(1)

    expenses = generate_expenses(user_id, count, months)

    try:
        db.execute("BEGIN")
        db.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            expenses,
        )
        db.commit()
    except Exception:
        db.rollback()
        db.close()
        raise

    dates = sorted(e[3] for e in expenses)

    print(f"Inserted {len(expenses)} expenses for user_id {user_id} ({user['name']}).")
    print(f"Date range: {dates[0]} to {dates[-1]}")
    print("\nSample of 5 inserted records:")
    for row in random.sample(expenses, min(5, len(expenses))):
        _, amount, category, date, description = row
        print(f"  {date}  ₹{amount:>8.2f}  {category:<14} {description}")

    db.close()


if __name__ == "__main__":
    main()
