import argparse
import csv
import os
import random
from datetime import date, timedelta

INSTRUMENTS = [
    ("AAPL", "Apple Inc.", "Technology", "NASDAQ"),
    ("TSLA", "Tesla Inc.", "Consumer Discretionary", "NASDAQ"),
    ("MSFT", "Microsoft Corporation", "Technology", "NASDAQ"),
    ("NVDA", "NVIDIA Corporation", "Technology", "NASDAQ"),
    ("AMZN", "Amazon.com Inc.", "Consumer Discretionary", "NASDAQ"),
    ("GOOGL", "Alphabet Inc.", "Communication Services", "NASDAQ"),
    ("META", "Meta Platforms Inc.", "Communication Services", "NASDAQ"),
    ("NFLX", "Netflix Inc.", "Communication Services", "NASDAQ"),
]

COUNTRIES = ["AU", "NZ", "AU", "AU", "GB"]
FIRST = ["James", "Sarah", "Wei", "Priya", "Tom", "Aisha", "Daniel", "Mia", "Raj", "Chloe"]
LAST = ["Nguyen", "Smith", "Chen", "Patel", "Brown", "Khan", "Wilson", "Lee", "Singh", "Taylor"]


def build_customers(n=200):
    rows = [["account_id", "first_name", "last_name", "email", "country", "signup_date", "account_status"]]
    start = date.today() - timedelta(days=730)
    for i in range(1, n + 1):
        first = random.choice(FIRST)
        last = random.choice(LAST)
        signup = start + timedelta(days=random.randint(0, 730))
        rows.append([
            f"ACC{i:05d}", first, last,
            f"{first.lower()}.{last.lower()}{i}@example.com",
            random.choice(COUNTRIES),
            signup.isoformat(),
            random.choices(["ACTIVE", "DORMANT", "CLOSED"], weights=[80, 15, 5])[0],
        ])
    return rows


def build_instruments():
    return [["ticker", "company_name", "sector", "exchange"]] + [list(r) for r in INSTRUMENTS]


def build_fx_rates(days=90):
    rows = [["rate_date", "base_currency", "quote_currency", "rate"]]
    rate = 0.66
    for i in range(days, -1, -1):
        d = date.today() - timedelta(days=i)
        rate = round(max(0.55, min(0.75, rate + random.uniform(-0.004, 0.004))), 5)
        rows.append([d.isoformat(), "AUD", "USD", rate])
    return rows


def write_csv(out_dir, name, rows):
    path = os.path.join(out_dir, f"{name}.csv")
    with open(path, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"wrote {path} ({len(rows) - 1} rows)")


def main():
    p = argparse.ArgumentParser(description="Simulates reference data that would come from production systems")
    p.add_argument("--out-dir", default="./data/reference")
    p.add_argument("--customers", type=int, default=200)
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    write_csv(args.out_dir, "customers", build_customers(args.customers))
    write_csv(args.out_dir, "instruments", build_instruments())
    write_csv(args.out_dir, "fx_rates", build_fx_rates())


if __name__ == "__main__":
    main()