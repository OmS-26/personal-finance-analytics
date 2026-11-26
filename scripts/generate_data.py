"""
Generate a realistic, reproducible synthetic dataset for the finance_analytics database.

Writes:
  sql/02_seed_data.sql            INSERT statements for every table
  exports/injected_anomalies.csv  ground truth for the anomaly-detection query

Usage:
  python3 scripts/generate_data.py [--users 30] [--seed 42]

Uses only the Python standard library.
"""

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START = date(2025, 11, 1)
END = date(2026, 10, 31)

FIRST_NAMES = ["Aisha", "Ben", "Chloe", "Daniel", "Emma", "Farhan", "Grace", "Harjot", "Isabel",
               "Jason", "Kavya", "Liam", "Maya", "Noah", "Olivia", "Priya", "Quinn", "Ravi",
               "Sofia", "Tyler", "Uma", "Victor", "Wen", "Xavier", "Yara", "Zain"]
LAST_NAMES = ["Ahmed", "Brown", "Chen", "Dhillon", "Evans", "Fernandes", "Gill", "Huang", "Iyer",
              "Johnson", "Khan", "Lee", "Martin", "Nguyen", "Patel", "Singh", "Tremblay", "Wong"]
CITIES = ["Toronto", "Mississauga", "Guelph", "Brampton", "Markham", "Hamilton", "Waterloo"]

# category name -> type
CATEGORIES = {
    "Salary": "Income",
    "Rent": "Expense",
    "Groceries": "Expense",
    "Dining": "Expense",
    "Transportation": "Expense",
    "Utilities": "Expense",
    "Phone & Internet": "Expense",
    "Subscriptions": "Expense",
    "Shopping": "Expense",
    "Entertainment": "Expense",
    "Health": "Expense",
    "Transfer": "Transfer",
}

# merchant name -> default category
MERCHANTS = {
    "Payroll Deposit": "Salary",
    "Property Management Co.": "Rent",
    "Loblaws": "Groceries", "Metro": "Groceries", "No Frills": "Groceries", "Costco": "Groceries",
    "Tim Hortons": "Dining", "Starbucks": "Dining", "Local Restaurant": "Dining", "DoorDash": "Dining",
    "Uber": "Transportation", "PRESTO": "Transportation", "Esso": "Transportation",
    "Toronto Hydro": "Utilities", "Enbridge Gas": "Utilities",
    "Rogers": "Phone & Internet", "Bell": "Phone & Internet",
    "Netflix": "Subscriptions", "Spotify": "Subscriptions", "Disney+": "Subscriptions",
    "Amazon.ca": "Shopping", "Best Buy": "Shopping", "Winners": "Shopping",
    "Cineplex": "Entertainment", "Steam": "Entertainment",
    "Shoppers Drug Mart": "Health",
    "Internal Transfer": "Transfer",
}

SUBSCRIPTION_PRICES = {"Netflix": 18.99, "Spotify": 11.99, "Disney+": 14.99}

# (merchants, transactions per month range, amount range) for variable spending
VARIABLE_SPEND = {
    "Groceries":      (["Loblaws", "Metro", "No Frills", "Costco"], (3, 6), (25, 180)),
    "Dining":         (["Tim Hortons", "Starbucks", "Local Restaurant", "DoorDash"], (3, 10), (4, 65)),
    "Transportation": (["Uber", "PRESTO", "Esso"], (3, 9), (8, 70)),
    "Shopping":       (["Amazon.ca", "Best Buy", "Winners"], (1, 4), (15, 160)),
    "Entertainment":  (["Cineplex", "Steam"], (0, 3), (12, 60)),
    "Health":         (["Shoppers Drug Mart"], (0, 2), (8, 55)),
}
CARD_CATEGORIES = {"Dining", "Shopping", "Entertainment"}  # charged to credit card when user has one


def months(start, end):
    d = start
    while d <= end:
        yield d
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)


def random_day(rng, month_start):
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return month_start + timedelta(days=rng.randrange((next_month - month_start).days))


def generate(n_users, seed):
    rng = random.Random(seed)
    cat_id = {name: i for i, name in enumerate(CATEGORIES, start=1)}
    mer_id = {name: i for i, name in enumerate(MERCHANTS, start=1)}

    users, accounts, txns = [], [], []
    used_names = set()

    for user_id in range(1, n_users + 1):
        while True:
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
            if name not in used_names:
                used_names.add(name)
                break
        email = name.lower().replace(" ", ".") + "@example.com"
        users.append((user_id, name, email, rng.choice(CITIES), START - timedelta(days=rng.randint(30, 900))))

        rent = rng.choice(range(1400, 2600, 50))

        # Accounts
        chq = len(accounts) + 1
        accounts.append((chq, user_id, "Chequing", round(rng.uniform(rent + 500, rent + 6000), 2), START))
        sav = len(accounts) + 1
        accounts.append((sav, user_id, "Savings", round(rng.uniform(0, 20000), 2), START))
        card = None
        if rng.random() < 0.6:
            card = len(accounts) + 1
            accounts.append((card, user_id, "Credit Card", 0.00, START))

        def add(account, merchant, amount, day, category=None):
            txns.append([account, mer_id[merchant], cat_id[category or MERCHANTS[merchant]],
                         round(amount, 2), day])

        # Per-user fixed parameters
        paycheque = rng.uniform(1750, 2900)
        phone = rng.choice(["Rogers", "Bell"])
        phone_bill = rng.choice([65.0, 75.0, 85.0, 95.0])
        subs = rng.sample(list(SUBSCRIPTION_PRICES), k=rng.randint(0, 3))
        monthly_saving = rng.choice([0, 200, 400, 600, 800])
        spend_scale = rng.uniform(0.7, 1.4)

        # Bi-weekly salary
        payday = START + timedelta(days=rng.randint(0, 13))
        while payday <= END:
            add(chq, "Payroll Deposit", paycheque * rng.uniform(0.98, 1.02), payday)
            payday += timedelta(days=14)

        card_balance_by_month = {}
        for m in months(START, END):
            add(chq, "Property Management Co.", -rent, m)
            add(chq, "Toronto Hydro", -rng.uniform(45, 130), m + timedelta(days=rng.randint(10, 20)))
            if m.month in (11, 12, 1, 2, 3):  # heating season
                add(chq, "Enbridge Gas", -rng.uniform(70, 160), m + timedelta(days=rng.randint(10, 20)))
            add(chq, phone, -phone_bill, m + timedelta(days=14))
            for s in subs:
                add(card or chq, s, -SUBSCRIPTION_PRICES[s], m + timedelta(days=4))
                if card:
                    card_balance_by_month[m] = card_balance_by_month.get(m, 0) - SUBSCRIPTION_PRICES[s]

            for category, (merchants, (lo, hi), (amin, amax)) in VARIABLE_SPEND.items():
                for _ in range(rng.randint(lo, hi)):
                    amount = -rng.uniform(amin, amax) * spend_scale
                    account = card if (card and category in CARD_CATEGORIES) else chq
                    add(account, rng.choice(merchants), amount, random_day(rng, m))
                    if account == card:
                        card_balance_by_month[m] = card_balance_by_month.get(m, 0) + amount

            if monthly_saving:
                d = m + timedelta(days=2)
                add(chq, "Internal Transfer", -monthly_saving, d)
                add(sav, "Internal Transfer", monthly_saving, d)

        # Pay off each month's card balance on the 5th of the following month
        if card:
            for m, bal in card_balance_by_month.items():
                pay_day = (m.replace(day=28) + timedelta(days=4)).replace(day=5)
                if pay_day <= END and bal < 0:
                    add(chq, "Internal Transfer", bal, pay_day)
                    add(card, "Internal Transfer", -bal, pay_day)

    # Inject unusually large purchases (ground truth for the anomaly query)
    anomalies = []
    spend_accounts = [a for a in accounts if a[2] != "Savings"]
    for _ in range(15):
        account = rng.choice(spend_accounts)
        category = rng.choice(["Shopping", "Dining", "Entertainment", "Transportation"])
        merchants, _, (amin, amax) = VARIABLE_SPEND[category]
        amount = -rng.uniform(amax * 4, amax * 9)
        txns.append([account[0], mer_id[rng.choice(merchants)], cat_id[category], round(amount, 2),
                     START + timedelta(days=rng.randint(90, (END - START).days))])
        anomalies.append(txns[-1])

    # Order by date and assign stable IDs
    txns.sort(key=lambda t: (t[4], t[0]))
    for i, t in enumerate(txns, start=1):
        t.insert(0, i)

    return cat_id, mer_id, users, accounts, txns, anomalies


def sql_value(v):
    if isinstance(v, str):
        return "'" + v.replace("'", "''") + "'"
    if isinstance(v, date):
        return f"'{v.isoformat()}'"
    return str(v)


def insert_statements(table, columns, rows, batch=500):
    out = []
    for i in range(0, len(rows), batch):
        values = ",\n".join("(" + ", ".join(sql_value(v) for v in r) + ")" for r in rows[i:i + batch])
        out.append(f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n{values};\n")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--users", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    cat_id, mer_id, users, accounts, txns, anomalies = generate(args.users, args.seed)

    parts = ["-- Generated by scripts/generate_data.py -- do not edit by hand\nUSE finance_analytics;\n"]
    parts += insert_statements("categories", ["category_id", "category_name", "category_type"],
                               [(i, n, CATEGORIES[n]) for n, i in cat_id.items()])
    parts += insert_statements("merchants", ["merchant_id", "merchant_name", "default_category_id"],
                               [(i, n, cat_id[MERCHANTS[n]]) for n, i in mer_id.items()])
    parts += insert_statements("users", ["user_id", "full_name", "email", "city", "created_at"], users)
    parts += insert_statements("accounts", ["account_id", "user_id", "account_type", "opening_balance",
                                            "opened_on"], accounts)
    parts += insert_statements("transactions", ["transaction_id", "account_id", "merchant_id", "category_id",
                                                "amount", "transaction_date"], txns)

    (ROOT / "sql" / "02_seed_data.sql").write_text("\n".join(parts))

    (ROOT / "exports").mkdir(exist_ok=True)
    with open(ROOT / "exports" / "injected_anomalies.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["transaction_id", "account_id", "amount", "transaction_date"])
        for t in sorted(anomalies, key=lambda t: t[0]):
            w.writerow([t[0], t[1], t[4], t[5]])

    print(f"{len(users)} users, {len(accounts)} accounts, {len(txns)} transactions, "
          f"{len(anomalies)} injected anomalies")


if __name__ == "__main__":
    main()
