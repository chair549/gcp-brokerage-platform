from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "email_on_failure": False,
}

PROJECT_ID = "de-portfolio-508507"
LANDING_BUCKET = f"{PROJECT_ID}-dev-landing"
DBT_DIR = "/home/airflow/gcs/dags/dbt"
DBT_INSTALL = "pip install --quiet --user dbt-bigquery==1.9.0 && export PATH=$PATH:~/.local/bin && "

with DAG(
    dag_id="brokerage_daily_pipeline",
    description="Daily reference data ingestion and dbt transformation",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 9, 1),
    schedule="0 18 * * *",
    catchup=False,
    max_active_runs=1,
    tags=["brokerage", "daily"],
) as dag:

    generate_reference_data = BashOperator(
        task_id="generate_reference_data",
        bash_command=(
            "python /home/airflow/gcs/dags/scripts/generate_reference_data.py "
            "--out-dir /tmp/reference"
        ),
    )

    load_reference_data = BashOperator(
        task_id="load_reference_data",
        bash_command=(
            "python /home/airflow/gcs/dags/scripts/load_reference.py "
            f"--project {PROJECT_ID} "
            f"--bucket {LANDING_BUCKET} "
            "--source-dir /tmp/reference "
            "--load-date {{ ds }}"
        ),
    )

    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=f"{DBT_INSTALL} cd {DBT_DIR} && dbt snapshot --profiles-dir {DBT_DIR}",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"{DBT_INSTALL} cd {DBT_DIR} && dbt run --profiles-dir {DBT_DIR}",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"{DBT_INSTALL} cd {DBT_DIR} && dbt test --profiles-dir {DBT_DIR}",
    )
    generate_reference_data >> load_reference_data >> dbt_snapshot >> dbt_run >> dbt_test
