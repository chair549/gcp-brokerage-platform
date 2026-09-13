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