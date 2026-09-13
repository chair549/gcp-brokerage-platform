resource "google_pubsub_topic" "trading_events" {
  name = "trading-events-${var.environment}"

  message_retention_duration = "86600s"

  labels = {
    environment = var.environment
  }
}

resource "google_pubsub_topic" "dead_letter" {
  name = "trading-events-dlq-${var.environment}"

  message_retention_duration = "604800s"

  labels = {
    environment = var.environment
  }
}

resource "google_pubsub_subscription" "dataflow" {
  name  = "trading-events-dataflow-${var.environment}"
  topic = google_pubsub_topic.trading_events.id

  ack_deadline_seconds       = 60
  message_retention_duration = "86600s"
  retain_acked_messages      = false

  expiration_policy {
    ttl = ""
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }

  labels = {
    environment = var.environment
  }
}
