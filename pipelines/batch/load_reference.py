import argparse
import csv
import io
import random
from datetime import date, timedelta

from google.cloud import storage, bigquery

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
            f"ACC{i:05d}",
            first,
            last,
            f"{first.lower()}.{last.lower()}{i}@example.com",
            random.choice(COUNTRIES),
            signup.isoformat(),
            random.choices(["ACTIVE", "DORMANT", "CLOSED"], weights=[80, 15, 5])[0],
        ])
    return rows


def build_instruments():
    rows = [["ticker", "company_name", "sector", "exchange"]]
    rows.extend([list(r) for r in INSTRUMENTS])
    return rows


def build_fx_rates(days=90):
    rows = [["rate_date", "base_currency", "quote_currency", "rate"]]
    rate = 0.66
    for i in range(days, -1, -1):
        d = date.today() - timedelta(days=i)
        rate = round(max(0.55, min(0.75, rate + random.uniform(-0.004, 0.004))), 5)
        rows.append([d.isoformat(), "AUD", "USD", rate])
    return rows


def to_csv_bytes(rows):
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode("utf-8")


def upload(client, bucket_name, blob_path, data):
    bucket = client.bucket(bucket_name)
    bucket.blob(blob_path).upload_from_string(data, content_type="text/csv")
    print(f"uploaded gs://{bucket_name}/{blob_path}")


def load_to_bq(client, project, dataset, table, uri, schema):
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        skip_leading_rows=1,
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    table_ref = f"{project}.{dataset}.{table}"
    job = client.load_table_from_uri(uri, table_ref, job_config=job_config)
    job.result()
    print(f"loaded {table_ref}: {client.get_table(table_ref).num_rows} rows")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--bucket", required=True)
    p.add_argument("--dataset", default="raw_dev")
    args = p.parse_args()

    gcs = storage.Client(project=args.project)
    bq = bigquery.Client(project=args.project)

    load_date = date.today().isoformat()

    datasets = {
        "customers": (build_customers(), [
            bigquery.SchemaField("account_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("first_name", "STRING"),
            bigquery.SchemaField("last_name", "STRING"),
            bigquery.SchemaField("email", "STRING"),
            bigquery.SchemaField("country", "STRING"),
            bigquery.SchemaField("signup_date", "DATE"),
            bigquery.SchemaField("account_status", "STRING"),
        ]),
        "instruments": (build_instruments(), [
            bigquery.SchemaField("ticker", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("company_name", "STRING"),
            bigquery.SchemaField("sector", "STRING"),
            bigquery.SchemaField("exchange", "STRING"),
        ]),
        "fx_rates": (build_fx_rates(), [
            bigquery.SchemaField("rate_date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("base_currency", "STRING"),
            bigquery.SchemaField("quote_currency", "STRING"),
            bigquery.SchemaField("rate", "FLOAT"),
        ]),
    }

    for name, (rows, schema) in datasets.items():
        blob_path = f"reference/{name}/load_date={load_date}/{name}.csv"
        upload(gcs, args.bucket, blob_path, to_csv_bytes(rows))
        load_to_bq(bq, args.project, args.dataset, name,
                   f"gs://{args.bucket}/{blob_path}", schema)


if __name__ == "__main__":
    main()