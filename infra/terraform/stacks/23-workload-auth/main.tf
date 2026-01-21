/// Stack: 23-workload-auth
/// Purpose: Deploy auth service Container App using reader stack outputs

locals {
  workload_code    = lower(var.workload_name)
  env_code         = lower(var.environment_code)
  identifier       = var.identifier != "" ? lower(var.identifier) : ""
  reader_state_key = var.reader_state_blob_key != "" ? var.reader_state_blob_key : "${var.environment_code}/reader/terraform.tfstate"

  common_tags = merge({
    project     = local.workload_code
    environment = local.env_code
    location    = var.location
    managed_by  = "terraform"
  }, var.tags)
}

data "terraform_remote_state" "bootstrap" {
  backend = "azurerm"
  config = {
    use_azuread_auth     = true
    tenant_id            = var.tenant_id
    resource_group_name  = var.state_resource_group_name
    storage_account_name = var.state_storage_account_name
    container_name       = var.state_container_name
    key                  = var.state_blob_key
  }
}

data "terraform_remote_state" "reader" {
  backend = "azurerm"
  config = {
    use_azuread_auth     = true
    tenant_id            = var.tenant_id
    resource_group_name  = var.state_resource_group_name
    storage_account_name = var.state_storage_account_name
    container_name       = var.state_container_name
    key                  = local.reader_state_key
  }
}

locals {
  rg_name   = data.terraform_remote_state.reader.outputs.resource_group_name
  aca_env_id = data.terraform_remote_state.reader.outputs.aca_environment_id

  reader_kv_name = try(data.terraform_remote_state.reader.outputs.key_vault_name, "")
  reader_kv_rg   = try(data.terraform_remote_state.reader.outputs.key_vault_resource_group, "")

  key_vault_name = var.key_vault_name != "" ? var.key_vault_name : local.reader_kv_name
  key_vault_rg   = var.key_vault_resource_group != "" ? var.key_vault_resource_group : local.reader_kv_rg

  _kv_name_validation = local.key_vault_name != "" ? true : error("key_vault_name is required (set in reader stack or override).")
  _kv_rg_validation   = local.key_vault_rg != "" ? true : error("key_vault_resource_group is required (set in reader stack or override).")
}

data "azurerm_key_vault" "auth" {
  name                = local.key_vault_name
  resource_group_name = local.key_vault_rg
}

locals {
  key_vault_uri      = data.azurerm_key_vault.auth.vault_uri
  key_vault_parent_id = "/subscriptions/${var.subscription_id}/resourceGroups/${local.key_vault_rg}"

  base_app_settings = merge(
    {
      PORT         = tostring(var.target_port)
      KEY_VAULT_URI = local.key_vault_uri
    },
    { for key, value in var.app_settings : key => value if key != "PORT" }
  )

  custom_domain     = var.custom_domain
  use_dns_record    = var.dns_zone_name != "" && var.dns_zone_resource_group != "" && var.dns_record_name != ""
  use_custom_domain = local.custom_domain != null

  managed_certificate_enabled  = local.use_custom_domain && var.managed_certificate_enabled
  custom_domain_certificate_id = local.managed_certificate_enabled ? azapi_resource.managed_certificate[0].id : null
  custom_domain_binding_type   = local.managed_certificate_enabled ? "SniEnabled" : "Disabled"
}

locals {
  key_vault_seed_values   = var.secrets
  key_vault_secret_names  = toset(values(var.secret_environment_overrides))
  key_vault_seed_names    = toset(nonsensitive(keys(local.key_vault_seed_values)))
  key_vault_existing_names = setsubtract(local.key_vault_secret_names, local.key_vault_seed_names)
  _kv_seed_requires_vault = length(local.key_vault_seed_values) > 0 && data.azurerm_key_vault.auth.id == "" ? error("key_vault_name must be set when secrets are provided") : true
  _kv_refs_requires_vault = length(local.key_vault_secret_names) > 0 && data.azurerm_key_vault.auth.id == "" ? error("key_vault_name must be set when secret_environment_overrides are configured") : true
}

resource "azurerm_key_vault_secret" "seeded" {
  for_each = local.key_vault_seed_names

  name         = each.key
  value        = local.key_vault_seed_values[each.key]
  key_vault_id = data.azurerm_key_vault.auth.id
}

data "azurerm_key_vault_secret" "existing" {
  for_each = local.key_vault_existing_names

  name         = each.key
  key_vault_id = data.azurerm_key_vault.auth.id
}

locals {
  key_vault_secret_ids = merge(
    { for name, secret in azurerm_key_vault_secret.seeded : name => secret.id },
    { for name, secret in data.azurerm_key_vault_secret.existing : name => secret.id }
  )
  _kv_refs_complete = length(local.key_vault_secret_names) > length(local.key_vault_secret_ids) ? error("missing Key Vault secrets for one or more secret_environment_overrides") : true
}

module "app" {
  source = "../../modules/aca/app"

  rg_name               = local.rg_name
  aca_env_id            = local.aca_env_id
  location              = var.location
  environment_code      = var.environment_code
  workload_name         = var.workload_name
  identifier            = local.identifier
  subscription_id       = var.subscription_id
  container_name        = var.container_name
  container_image       = var.container_image
  registry_id           = var.registry_id
  registry_login_server = var.registry_login_server
  registry_username     = var.registry_username
  registry_password     = var.registry_password
  target_port           = var.target_port
  command               = var.command
  args                  = var.args
  cpu                   = var.cpu
  memory                = var.memory
  min_replicas          = var.min_replicas
  max_replicas          = var.max_replicas
  ingress_external      = var.ingress_external
  ingress_allowed_cidrs = var.ingress_allowed_cidrs
  custom_domains = local.use_custom_domain ? [
    {
      name                     = local.custom_domain.hostname
      certificate_id           = local.custom_domain_certificate_id
      certificate_binding_type = local.custom_domain_binding_type
    }
  ] : []
  app_settings                 = local.base_app_settings
  secrets                      = {}
  key_vault_secret_ids         = local.key_vault_secret_ids
  secret_environment_overrides = var.secret_environment_overrides
  inject_identity_client_id    = var.inject_identity_client_id
  tags                         = merge(local.common_tags, { component = "auth" })
}

resource "azurerm_key_vault_access_policy" "app" {
  key_vault_id = data.azurerm_key_vault.auth.id
  tenant_id    = var.tenant_id
  object_id    = module.app.identity_principal_id

  secret_permissions = [
    "Get",
    "List",
  ]
}

resource "azurerm_role_assignment" "key_vault_secrets_user" {
  scope                = data.azurerm_key_vault.auth.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = module.app.identity_principal_id
}

resource "azapi_update_resource" "key_vault_network_rules" {
  count = length(var.key_vault_ip_rules) > 0 ? 1 : 0

  type      = "Microsoft.KeyVault/vaults@2023-07-01"
  name      = local.key_vault_name
  parent_id = local.key_vault_parent_id

  body = {
    properties = {
      networkAcls = {
        bypass        = "AzureServices"
        defaultAction = "Deny"
        ipRules       = [for ip in var.key_vault_ip_rules : { value = ip }]
      }
    }
  }
}

data "azurerm_dns_zone" "custom_domain" {
  count = local.use_dns_record ? 1 : 0

  name                = var.dns_zone_name
  resource_group_name = var.dns_zone_resource_group
}

resource "azurerm_dns_cname_record" "app" {
  count = local.use_dns_record ? 1 : 0

  name                = var.dns_record_name
  zone_name           = data.azurerm_dns_zone.custom_domain[0].name
  resource_group_name = data.azurerm_dns_zone.custom_domain[0].resource_group_name
  ttl                 = 300
  record              = module.app.app_base_fqdn
}

resource "azapi_resource" "managed_certificate" {
  count = local.managed_certificate_enabled ? 1 : 0

  type      = "Microsoft.App/managedEnvironments/managedCertificates@2024-03-01"
  name      = local.custom_domain.certificate_name != null && local.custom_domain.certificate_name != "" ? local.custom_domain.certificate_name : replace(local.custom_domain.hostname, ".", "-")
  parent_id = local.aca_env_id
  location  = var.location
  body = {
    properties = {
      domainControlValidation = "CNAME"
      subjectName             = local.custom_domain.hostname
    }
  }
}
