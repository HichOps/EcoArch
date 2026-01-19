terraform {
  backend "gcs" {
    bucket  = "ecoarch-tfstate-514436528658"
    prefix  = "terraform/state"
  }
}