output "landing_bucket" {
  description = "Landing zone bucket name"
  value       = google_storage_bucket.landing.name
}

output "staging_bucket" {
  description = "Staging bucket name"
  value       = google_storage_bucket.staging.name
}

output "artifacts_bucket" {
  description = "Artifacts bucket name"
  value       = google_storage_bucket.artifacts.name
}

output "bigquery_datasets" {
  description = "Created BigQuery dataset IDs"
  value       = { for k, v in google_bigquery_dataset.datasets : k => v.dataset_id }
}

output "pubsub_topic" {
  description = "Trading events topic name"
  value       = google_pubsub_topic.trading_events.name
}

output "pubsub_subscription" {
  description = "Dataflow subscription name"
  value       = google_pubsub_subscription.dataflow.name
}
