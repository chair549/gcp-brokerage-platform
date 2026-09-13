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

