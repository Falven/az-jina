output "resource_group_name" {
  value       = local.rg_name
  description = "Workload resource group name"
}

output "container_app_name" {
  value       = module.app.app_name
  description = "Container App name"
}

output "container_app_fqdn" {
  value       = module.app.app_fqdn
  description = "Container App FQDN"
}

output "container_app_base_fqdn" {
  value       = module.app.app_base_fqdn
  description = "Container App base FQDN (no revision suffix)"
}

output "aca_environment_id" {
  value       = local.aca_env_id
  description = "ACA environment ID in use"
}

output "identity_principal_id" {
  value       = module.app.identity_principal_id
  description = "User-assigned identity principal ID"
}

output "identity_client_id" {
  value       = module.app.identity_client_id
  description = "User-assigned identity client ID"
}

output "managed_certificate_id" {
  value       = length(azapi_resource.managed_certificate) > 0 ? azapi_resource.managed_certificate[0].id : null
  description = "Managed certificate resource ID (if created)"
}
