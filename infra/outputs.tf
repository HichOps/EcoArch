# ── Outputs EcoArch ────────────────────────────────────────────

output "vm_names" {
  description = "Noms des VMs créées"
  value       = [for vm in google_compute_instance.vm : vm.name]
}

output "vm_external_ips" {
  description = "Adresses IP externes des VMs"
  value       = [for vm in google_compute_instance.vm : try(vm.network_interface[0].access_config[0].nat_ip, "N/A")]
}

output "sql_instance_names" {
  description = "Noms des instances Cloud SQL"
  value       = [for db in google_sql_database_instance.db : db.name]
}

output "bucket_names" {
  description = "Noms des buckets Cloud Storage"
  value       = [for b in google_storage_bucket.bucket : b.name]
}

output "deployment_id" {
  description = "Identifiant du déploiement"
  value       = var.deployment_id
}
