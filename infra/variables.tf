variable "project_id" {
  type        = string
  description = "L'ID du projet GCP cible"
}

variable "region" {
  type        = string
  description = "La région GCP (Low-cost region)"
  default     = "us-central1"
}

variable "zone" {
  type        = string
  description = "La zone GCP (Low-cost zone)"
  default     = "us-central1-a"
}