locals {
  datasets = {
    raw        = "Raw ingested data, no transformations applied"
    staging    = "Cleaned, typed and standardised source data"
    marts      = "Dimensional models and business-facing datasets"
    monitoring = "Data quality, freshness and cost observability"
  }
}

resource "google_bigquery_dataset" "datasets" {
  for_each = local.datasets

  dataset_id  = "${each.key}_${var.environment}"
  description = each.value
  location    = var.region

  delete_contents_on_destroy = true

  labels = {
    layer       = each.key
    environment = var.environment
  }
}
