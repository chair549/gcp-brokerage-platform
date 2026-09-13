locals {
  bucket_prefix = "${var.project_id}-${var.environment}"
}

resource "google_storage_bucket" "landing" {
  name     = "${local.bucket_prefix}-landing"
  location = var.region

  uniform_bucket_level_access = true
  force_destroy               = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    zone        = "landing"
    environment = var.environment
  }
}

resource "google_storage_bucket" "staging" {
  name     = "${local.bucket_prefix}-staging"
  location = var.region

  uniform_bucket_level_access = true
  force_destroy               = true

  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    zone        = "staging"
    environment = var.environment
  }
}

resource "google_storage_bucket" "artifacts" {
  name     = "${local.bucket_prefix}-artifacts"
  location = var.region

  uniform_bucket_level_access = true
  force_destroy               = true

  labels = {
    zone        = "artifacts"
    environment = var.environment
  }
}
