output "app_name" {
  description = "Container App name"
  value       = module.app.name
}

output "app_fqdn" {
  description = "Container App ingress FQDN (stable, no revision suffix)"
  value       = module.app.fqdn_url
}

output "app_base_fqdn" {
  description = "Container App ingress hostname (no scheme, stable)"
  value = trim(
    replace(module.app.fqdn_url, "https://", ""),
    "/"
  )
}

output "identity_id" {
  description = "User-assigned identity resource ID"
  value       = azurerm_user_assigned_identity.app.id
}

output "identity_principal_id" {
  description = "User-assigned identity principal ID"
  value       = azurerm_user_assigned_identity.app.principal_id
}

output "identity_client_id" {
  description = "User-assigned identity client ID"
  value       = azurerm_user_assigned_identity.app.client_id
}
