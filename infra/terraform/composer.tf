resource "google_service_account" "composer" {
  account_id   = "composer-${var.environment}"
  display_name = "Cloud Composer service account"
}

resource "google_project_iam_member" "composer_worker" {
  project = var.project_id
  role    = "roles/composer.worker"
  member  = "serviceAccount:${google_service_account.composer.email}"
}

resource "google_project_iam_member" "composer_bq" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.composer.email}"
}

resource "google_project_iam_member" "composer_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.composer.email}"
}

resource "google_composer_environment" "main" {
  name   = "brokerage-${var.environment}"
  region = var.region

  config {
    software_config {
      image_version = "composer-3-airflow-2"

    }

    node_config {
      service_account = google_service_account.composer.email
    }
  }
}

output "composer_dag_bucket" {
  value = google_composer_environment.main.config[0].dag_gcs_prefix
}

output "composer_airflow_uri" {
  value = google_composer_environment.main.config[0].airflow_uri
}
