/// Stack: 21-workload-mcp
/// Purpose: Deploy az-jina-mcp Container App (optionally reusing existing ACA environment)

locals {
  workload_code    = lower(var.workload_name)
  env_code         = lower(var.environment_code)
  identifier       = var.identifier != "" ? lower(var.identifier) : ""
  reader_state_key = var.reader_state_blob_key != "" ? var.reader_state_blob_key : "${var.environment_code}/reader/terraform.tfstate"

  using_existing_env = var.existing_aca_environment_id != ""
  existing_rg_name = local.using_existing_env ? (
    var.rg_name_override != "" ? var.rg_name_override : error("rg_name_override is required when existing_aca_environment_id is set")
  ) : ""

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

module "naming" {
  source  = "Azure/naming/azurerm"
  version = "0.4.2"

  suffix        = compact([local.workload_code, local.env_code, local.identifier == "" ? null : local.identifier])
  unique-length = 6
}

module "env" {
  count = local.using_existing_env ? 0 : 1

  source = "../../modules/aca/environment"

  environment_code           = var.environment_code
  location                   = var.location
  workload_name              = var.workload_name
  identifier                 = var.identifier
  rg_name_override           = var.rg_name_override
  log_analytics_workspace_id = var.log_analytics_workspace_id
  log_retention_days         = var.log_retention_days
  tags                       = local.common_tags
}

data "azurerm_resource_group" "workload" {
  count = local.using_existing_env ? 1 : 0
  name  = local.existing_rg_name
}

locals {
  rg_name            = local.using_existing_env ? data.azurerm_resource_group.workload[0].name : module.env[0].rg_name
  aca_env_id         = local.using_existing_env ? var.existing_aca_environment_id : module.env[0].aca_env_id
  key_vault_rg       = var.key_vault_resource_group != "" ? var.key_vault_resource_group : local.rg_name
  reader_crawl_fqdn  = data.terraform_remote_state.reader.outputs.crawl_container_app_fqdn
  reader_search_fqdn = data.terraform_remote_state.reader.outputs.search_container_app_fqdn
  reader_crawl_base  = startswith(local.reader_crawl_fqdn, "http") ? local.reader_crawl_fqdn : "https://${local.reader_crawl_fqdn}"
  reader_search_base = startswith(local.reader_search_fqdn, "http") ? local.reader_search_fqdn : "https://${local.reader_search_fqdn}"

  base_app_settings = merge(
    {
      PORT            = tostring(var.target_port)
      MCP_READER_BASE = local.reader_crawl_base
      MCP_SEARCH_BASE = local.reader_search_base
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

data "azurerm_client_config" "current" {}

data "azurerm_key_vault" "existing" {
  count = (!var.create_key_vault && var.key_vault_name != "" && local.key_vault_rg != "") ? 1 : 0

  name                = var.key_vault_name
  resource_group_name = local.key_vault_rg
}

resource "azurerm_key_vault" "this" {
  count = var.create_key_vault ? 1 : 0

  name                          = var.key_vault_name
  location                      = var.location
  resource_group_name           = local.key_vault_rg
  tenant_id                     = var.tenant_id
  sku_name                      = lower(var.key_vault_sku)
  soft_delete_retention_days    = var.key_vault_soft_delete_retention_days
  purge_protection_enabled      = var.key_vault_purge_protection_enabled
  public_network_access_enabled = true

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get",
      "List",
      "Set",
      "Delete",
      "Recover",
      "Backup",
      "Restore",
    ]
  }

  tags = local.common_tags
}

locals {
  key_vault_id_final = var.create_key_vault ? (
    length(azurerm_key_vault.this) > 0 ? azurerm_key_vault.this[0].id : null
    ) : (
    length(data.azurerm_key_vault.existing) > 0 ? data.azurerm_key_vault.existing[0].id : null
  )

  key_vault_uri_final = var.create_key_vault ? (
    length(azurerm_key_vault.this) > 0 ? azurerm_key_vault.this[0].vault_uri : ""
    ) : (
    length(data.azurerm_key_vault.existing) > 0 ? data.azurerm_key_vault.existing[0].vault_uri : ""
  )

  key_vault_parent_id = local.key_vault_rg != "" ? "/subscriptions/${var.subscription_id}/resourceGroups/${local.key_vault_rg}" : ""
}

locals {
  key_vault_seed_values   = var.secrets
  key_vault_secret_names  = toset(values(var.secret_environment_overrides))
  key_vault_seed_names    = toset(nonsensitive(keys(local.key_vault_seed_values)))
  key_vault_existing_names = setsubtract(local.key_vault_secret_names, local.key_vault_seed_names)
  _kv_seed_requires_vault = length(local.key_vault_seed_values) > 0 && local.key_vault_id_final == null ? error("key_vault_name must be set when secrets are provided") : true
  _kv_refs_requires_vault = length(local.key_vault_secret_names) > 0 && local.key_vault_id_final == null ? error("key_vault_name must be set when secret_environment_overrides are configured") : true
}

resource "azurerm_key_vault_secret" "seeded" {
  for_each = local.key_vault_id_final != null ? local.key_vault_seed_names : toset([])

  name         = each.key
  value        = local.key_vault_seed_values[each.key]
  key_vault_id = local.key_vault_id_final
}

data "azurerm_key_vault_secret" "existing" {
  for_each = local.key_vault_id_final != null ? local.key_vault_existing_names : toset([])

  name         = each.key
  key_vault_id = local.key_vault_id_final
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
  tags                         = merge(local.common_tags, { component = "mcp" })
}

resource "azurerm_key_vault_access_policy" "app" {
  for_each = local.key_vault_id_final != null ? { app = module.app.identity_principal_id } : {}

  key_vault_id = local.key_vault_id_final
  tenant_id    = var.tenant_id
  object_id    = each.value

  secret_permissions = [
    "Get",
    "List",
  ]
}

resource "azurerm_role_assignment" "key_vault_secrets_user" {
  for_each = local.key_vault_id_final != null ? { app = module.app.identity_principal_id } : {}

  scope                = local.key_vault_id_final
  role_definition_name = "Key Vault Secrets User"
  principal_id         = each.value
}

resource "azapi_update_resource" "key_vault_network_rules" {
  count = local.key_vault_id_final != null && length(var.key_vault_ip_rules) > 0 && local.key_vault_parent_id != "" ? 1 : 0

  type      = "Microsoft.KeyVault/vaults@2023-07-01"
  name      = var.key_vault_name
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
