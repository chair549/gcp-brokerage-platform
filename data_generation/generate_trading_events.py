import argparse
import json
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from google.cloud import pubsub_v1

TICKERS = ["AAPL", "TSLA", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "NFLX"]
PRICES = {"AAPL": 190, "TSLA": 250, "MSFT": 420, "NVDA": 880,
          "AMZN": 180, "GOOGL": 165, "META": 500, "NFLX": 620}
N_ACCOUNTS = 200
DUP_RATE = 0.02
LATE_RATE = 0.03
BAD_RATE = 0.01


def now():
    return datetime.now(timezone.utc)


def make_order(account_id):
    ticker = random.choice(TICKERS)
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "order_placed",
        "event_timestamp": now().isoformat(),
        "order_id": str(uuid.uuid4()),
        "account_id": account_id,
        "ticker": ticker,
        "side": random.choice(["BUY", "SELL"]),
        "quantity": random.randint(1, 100),
        "order_type": random.choice(["MARKET", "LIMIT"]),
        "limit_price_usd": round(PRICES[ticker] * random.uniform(0.97, 1.03), 2),
    }


def make_fill(order):
    price = PRICES[order["ticker"]] * random.uniform(0.995, 1.005)
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "order_filled",
        "event_timestamp": (now() + timedelta(seconds=random.randint(1, 30))).isoformat(),
        "order_id": order["order_id"],
        "account_id": order["account_id"],
        "ticker": order["ticker"],
        "fill_price_usd": round(price, 2),
        "quantity": order["quantity"],
        "fee_usd": 3.00,
    }


def make_cancel(order):
    return {
        "event_id": str(uuid.uuid4()),
        "event_type": "order_cancelled",
        "event_timestamp": (now() + timedelta(seconds=random.randint(1, 60))).isoformat(),
        "order_id": order["order_id"],
        "account_id": order["account_id"],
        "ticker": order["ticker"],
        "reason": random.choice(["USER_CANCELLED", "INSUFFICIENT_FUNDS", "EXPIRED"]),
    }


def publish(publisher, topic_path, event):
    publisher.publish(topic_path, json.dumps(event).encode("utf-8"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--topic", default="trading-events-dev")
    p.add_argument("--rate", type=float, default=5.0, help="events per second")
    p.add_argument("--duration", type=int, default=60, help="seconds to run")
    args = p.parse_args()

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(args.project, args.topic)

    accounts = [f"ACC{i:05d}" for i in range(1, N_ACCOUNTS + 1)]
    end = time.time() + args.duration
    sent = 0

    while time.time() < end:
        order = make_order(random.choice(accounts))

        if random.random() < BAD_RATE:
            bad = dict(order)
            bad.pop("ticker", None)
            bad["quantity"] = "not_a_number"
            publish(publisher, topic_path, bad)
            sent += 1
            time.sleep(1.0 / args.rate)
            continue

        publish(publisher, topic_path, order)
        sent += 1

        if random.random() < DUP_RATE:
            publish(publisher, topic_path, order)
            sent += 1

        if random.random() < LATE_RATE:
            order["event_timestamp"] = (now() - timedelta(minutes=random.randint(5, 30))).isoformat()

        roll = random.random()
        if roll < 0.75:
            publish(publisher, topic_path, make_fill(order))
            sent += 1
        elif roll < 0.90:
            publish(publisher, topic_path, make_cancel(order))
            sent += 1

        time.sleep(1.0 / args.rate)

    publisher.stop() if hasattr(publisher, "stop") else None
    print(f"Published {sent} events to {topic_path}")


if __name__ == "__main__":
    main()
