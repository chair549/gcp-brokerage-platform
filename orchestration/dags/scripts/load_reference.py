import argparse
import os
from datetime import date

from google.cloud import storage, bigquery

SCHEMAS = {
    "customers": [
        bigquery.SchemaField("account_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("first_name", "STRING"),
        bigquery.SchemaField("last_name", "STRING"),
        bigquery.SchemaField("email", "STRING"),
        bigquery.SchemaField("country", "STRING"),
        bigquery.SchemaField("signup_date", "DATE"),
        bigquery.SchemaField("account_status", "STRING"),
    ],
    "instruments": [
        bigquery.SchemaField("ticker", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("company_name", "STRING"),
        bigquery.SchemaField("sector", "STRING"),
        bigquery.SchemaField("exchange", "STRING"),
    ],
    "fx_rates": [
        bigquery.SchemaField("rate_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("base_currency", "STRING"),
        bigquery.SchemaField("quote_currency", "STRING"),
        bigquery.SchemaField("rate", "FLOAT"),
    ],
}


def upload_to_landing(gcs, bucket_name, local_path, blob_path):
    gcs.bucket(bucket_name).blob(blob_path).upload_from_filename(local_path)
    uri = f"gs://{bucket_name}/{blob_path}"
    print(f"uploaded {uri}")
    return uri


def load_to_bigquery(bq, project, dataset, table, uri, schema):
    config = bigquery.LoadJobConfig(
        schema=schema,
        skip_leading_rows=1,
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    ref = f"{project}.{dataset}.{table}"
    bq.load_table_from_uri(uri, ref, job_config=config).result()
    print(f"loaded {ref}: {bq.get_table(ref).num_rows} rows")


def main():
    p = argparse.ArgumentParser(description="Loads reference CSVs into the GCS landing zone and BigQuery raw layer")
    p.add_argument("--project", required=True)
    p.add_argument("--bucket", required=True)
    p.add_argument("--source-dir", required=True, help="Directory containing the reference CSVs")
    p.add_argument("--dataset", default="raw_dev")
    p.add_argument("--load-date", default=date.today().isoformat())
    args = p.parse_args()

    gcs = storage.Client(project=args.project)
    bq = bigquery.Client(project=args.project)

    for table, schema in SCHEMAS.items():
        local_path = os.path.join(args.source_dir, f"{table}.csv")
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"expected {local_path}")

        blob_path = f"reference/{table}/load_date={args.load_date}/{table}.csv"
        uri = upload_to_landing(gcs, args.bucket, local_path, blob_path)
        load_to_bigquery(bq, args.project, args.dataset, table, uri, schema)


if __name__ == "__main__":
    main()