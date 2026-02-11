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

variable "deployment_id" {
  description = "Identifiant unique du déploiement EcoArch (injecté via TF_VAR_deployment_id)"
  type        = string
  default     = "manual"
}

variable "boot_disk_image" {
  type    = string
  default = "debian-cloud/debian-11"
}

variable "boot_disk_size" {
  type    = number
  default = 50
}

variable "architecture_json" {
  description = "JSON sérialisé du panier EcoArch (injecté via TF_VAR_architecture_json)"
  type        = string
  default     = "[]"
}