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

variable "instance_name" {
  description = "Nom de la VM"
  type        = string
  default     = "ecoarch-demo-instance"
}

variable "machine_type" {
  description = "Type d'instance (détermine le coût)"
  type        = string
  default     = "e2-medium" # Valeur actuelle générant ~99 USD
}

variable "boot_disk_image" {
  type    = string
  default = "debian-cloud/debian-11"
}

variable "boot_disk_size" {
  type    = number
  default = 50
}

# Les autres variables (instance_name, machine_type, zone) 
# doivent aussi être présentes ici.