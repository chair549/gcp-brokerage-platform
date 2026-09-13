# GCP Brokerage Data Platform

An end-to-end data platform on Google Cloud simulating a retail brokerage: streaming order events, batch reference data, a dimensional warehouse with SCD2 history, orchestration, and automated data quality testing.

Built to demonstrate the GCP data engineering stack end to end: Terraform, Pub/Sub, Dataflow, Cloud Storage, BigQuery, dbt, and Cloud Composer.

## Architecture

| Layer | Technology | Purpose |
|---|---|---|
| Infrastructure | Terraform | All GCP resources defined as code |
| Streaming ingestion | Pub/Sub → Apache Beam on Dataflow | Order lifecycle events, validated and deduplicated |
| Batch ingestion | Python → Cloud Storage → BigQuery | Customer, instrument and FX reference data |
| Warehouse | BigQuery | Partitioned and clustered, layered raw → staging → marts |
| Transformation | dbt | Star schema, SCD2 snapshots, 14 data quality tests |
| Orchestration | Cloud Composer (Airflow) | Daily DAG with retries and a test gate |
| CI | GitHub Actions | Linting and validation on every PR |

## Repository structure

```
data_generation/      Simulated source systems
infra/terraform/      All GCP infrastructure as code
pipelines/streaming/  Apache Beam pipeline for Pub/Sub → BigQuery
pipelines/batch/      Reference data ingestion to GCS and BigQuery
transform/brokerage/  dbt project: staging, snapshots, star schema, tests
orchestration/dags/   Airflow DAG
```

`data_generation/` exists only because this project has no real source systems. Everything in `pipelines/` is source-agnostic and would be unchanged if the data came from a production database or vendor API.

## Data flow

**Streaming path.** A Python event generator publishes `order_placed`, `order_filled` and `order_cancelled` events to Pub/Sub, deliberately injecting duplicates, late-arriving events and malformed records. An Apache Beam pipeline running on Cloud Dataflow reads the subscription, applies 60-second fixed windows, validates each record against a schema, deduplicates on `event_id`, and writes to a date-partitioned BigQuery table clustered on `event_type` and `ticker`. Records that fail parsing or validation are routed to a dead-letter table with the original payload and an error classification, rather than crashing the pipeline or being silently dropped.

**Batch path.** Reference data (customers, instruments, AUD/USD rates) is written to the GCS landing zone as date-partitioned CSVs, then loaded into BigQuery with explicit schemas. Loads use `WRITE_TRUNCATE` so they are idempotent and safe for Airflow to retry.

**Transformation.** dbt builds a layered warehouse:

- Staging models clean and type each source, one model per source table, no joins
- A dbt snapshot captures SCD2 history on the customer dimension
- `dim_customer` exposes one row per customer version with a surrogate key
- `fct_trades` joins fills to their originating orders, converts USD to AUD using the rate for the trade date, and joins to the customer version current at the time of the trade
- `mart_daily_trading` pre-aggregates by date, sector and country

**Orchestration.** A daily Composer DAG runs ingestion, then `dbt snapshot`, `dbt run` and `dbt test` in sequence. `dbt test` acts as a quality gate: downstream tasks do not run if tests fail.

## Data model

```
dim_customer (SCD2)  ──┐
dim_instrument       ──┼──→  fct_trades  ──→  mart_daily_trading
stg_fx_rates         ──┘
```

`fct_trades` is at transaction grain: one row per execution. The join to `dim_customer` is temporal, matching each trade to the customer version that was valid when the trade occurred:

```sql
on f.account_id = c.account_id
and f.event_timestamp >= c.valid_from
and (f.event_timestamp < c.valid_to or c.valid_to is null)
```

Without this, a customer changing country would retroactively rewrite every historical trade they had made, and previously published reports would no longer reproduce.

## Design decisions

**Dead-letter routing over fail-fast.** Malformed records are written to `raw_dev.trading_events_dlq` with the original payload and an error classification, rather than crashing the pipeline or being dropped. One poison message should not halt ingestion, and silently discarding bad data makes reconciliation impossible later. Pub/Sub is also configured with a dead-letter policy after five delivery attempts, covering failures the pipeline never acknowledges.

**Deduplication at two layers.** The Beam pipeline deduplicates on `event_id` within a 60-second window, which handles the at-least-once redelivery Pub/Sub guarantees. The staging model deduplicates again with `row_number()`, catching anything arriving outside that window, such as a redelivery after a pipeline restart. Unbounded dedup state in the streaming layer would be expensive; a second pass in the warehouse is cheap and runs once per build.

**Partitioning and clustering.** `trading_events` is partitioned by `event_timestamp` (day) and clustered on `event_type` and `ticker`. BigQuery charges by bytes scanned, so partition pruning on date filters is the main cost lever, with clustering reducing scan further within each partition.

**SCD2 on customers only.** Instruments are effectively static and FX rates are already time-series by nature. Applying SCD2 everywhere adds complexity without analytical value.

**First version backdated.** The initial snapshot version of each customer is backdated to 1900-01-01. dbt stamps `valid_from` with the time of the first snapshot run, but customers existed before tracking began, so facts predating that timestamp would find no matching dimension row.

**Tiered storage lifecycle.** Landing zone objects move to Nearline after 30 days and are deleted after 90. Soft delete is disabled on the staging and artifacts buckets, where retaining deleted temp files is pure cost, but retained on landing where raw data recoverability is worth paying for.

**Idempotent loads.** Batch loads use `WRITE_TRUNCATE` and accept a `--load-date` parameter. Airflow retries tasks automatically, so every task must be safe to re-run. The same parameter enables backfilling historical partitions.

## Known limitations

- The dbt project is copied into the Composer DAG bucket and dbt is installed at task runtime. Composer pins Airflow's dependencies tightly, and `dbt-bigquery` conflicts with them when installed via `pypi_packages`. In production this would run as a container via `KubernetesPodOperator`, or use Cosmos to expose each dbt model as its own Airflow task.
- The Composer service account is granted `bigquery.admin`. This should be scoped to specific datasets.
- The Dataflow job was deployed manually for validation. Production deployment would use a Flex Template launched from the DAG.
- Marts are materialised into the same BigQuery dataset as staging models. Separating them requires a `generate_schema_name` macro override.
- The Composer environment and streaming Dataflow job are destroyed after each session for cost reasons; both are recreated from Terraform and the DAG bucket.

## Running it

Requires a GCP project with billing enabled, and the `gcloud` CLI authenticated.

```bash
# 1. Provision infrastructure
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # set your project_id
terraform init
terraform apply

# 2. Streaming path
python pipelines/streaming/pipeline.py \
  --project $PROJECT \
  --subscription projects/$PROJECT/subscriptions/trading-events-dataflow-dev \
  --events_table $PROJECT:raw_dev.trading_events \
  --dlq_table $PROJECT:raw_dev.trading_events_dlq \
  --runner DirectRunner \
  --temp_location gs://$PROJECT-dev-staging/tmp

# in a second terminal
python data_generation/generate_trading_events.py --project $PROJECT --duration 60

# 3. Batch path
python data_generation/generate_reference_data.py --out-dir ./data/reference
python pipelines/batch/load_reference.py \
  --project $PROJECT \
  --bucket $PROJECT-dev-landing \
  --source-dir ./data/reference

# 4. Transform
cd transform/brokerage
dbt snapshot && dbt run && dbt test

# 5. Orchestration (expensive, destroy after use)
gcloud storage cp -r orchestration/dags/* $(terraform output -raw composer_dag_bucket)/
terraform destroy -target=google_composer_environment.main
```

Swap `--runner DirectRunner` for `--runner DataflowRunner --region australia-southeast1` to deploy to managed Dataflow.

## Cost management

Cloud Composer and streaming Dataflow are the only components with meaningful ongoing cost. Both are created for a session and destroyed afterwards. Everything else (Cloud Storage, BigQuery, Pub/Sub) is negligible at this volume. A project budget alert is configured at $50.