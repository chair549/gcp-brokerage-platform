resource "google_bigquery_table" "trading_events" {
  dataset_id          = google_bigquery_dataset.datasets["raw"].dataset_id
  table_id            = "trading_events"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "event_timestamp"
  }

  clustering = ["event_type", "ticker"]

  schema = jsonencode([
    { name = "event_id", type = "STRING", mode = "REQUIRED" },
    { name = "event_type", type = "STRING", mode = "REQUIRED" },
    { name = "event_timestamp", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "order_id", type = "STRING", mode = "NULLABLE" },
    { name = "account_id", type = "STRING", mode = "NULLABLE" },
    { name = "ticker", type = "STRING", mode = "NULLABLE" },
    { name = "side", type = "STRING", mode = "NULLABLE" },
    { name = "quantity", type = "INTEGER", mode = "NULLABLE" },
    { name = "order_type", type = "STRING", mode = "NULLABLE" },
    { name = "limit_price_usd", type = "FLOAT", mode = "NULLABLE" },
    { name = "fill_price_usd", type = "FLOAT", mode = "NULLABLE" },
    { name = "fee_usd", type = "FLOAT", mode = "NULLABLE" },
    { name = "reason", type = "STRING", mode = "NULLABLE" },
    { name = "ingested_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}

resource "google_bigquery_table" "dead_letter" {
  dataset_id          = google_bigquery_dataset.datasets["raw"].dataset_id
  table_id            = "trading_events_dlq"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "ingested_at"
  }

  schema = jsonencode([
    { name = "raw_payload", type = "STRING", mode = "NULLABLE" },
    { name = "error_type", type = "STRING", mode = "NULLABLE" },
    { name = "error_message", type = "STRING", mode = "NULLABLE" },
    { name = "ingested_at", type = "TIMESTAMP", mode = "REQUIRED" },
  ])
}
