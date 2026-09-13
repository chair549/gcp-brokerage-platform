variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "Primary region for resources"
  type        = string
  default     = "australia-southeast1"
}

variable "environment" {
  description = "Environment name, used as a resource suffix"
  type        = string
  default     = "dev"
}
