variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "environment_code" {
  description = "Environment code"
  type        = string
}

variable "workload_name" {
  description = "Workload name"
  type        = string
}

variable "identifier" {
  description = "Optional identifier appended to resource names"
  type        = string
  default     = ""
}

variable "rg_name_override" {
  description = "Optional override for the workload resource group name"
  type        = string
  default     = ""
}

variable "existing_aca_environment_id" {
  description = "Existing ACA environment resource ID to reuse (skip creation when provided)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags"
  type        = map(string)
  default     = {}
}

variable "log_retention_days" {
  description = "Log Analytics retention days (only used when creating a new environment)"
  type        = number
  default     = 30
}

variable "log_analytics_workspace_id" {
  description = "Existing Log Analytics workspace ID (optional; only used when creating a new environment)"
  type        = string
  default     = ""
}

variable "container_image" {
  description = "Container image"
  type        = string
}

variable "container_name" {
  description = "Container name inside the Container App"
  type        = string
  default     = "az-jina-mcp"
}

variable "registry_id" {
  description = "ACR resource ID (optional)"
  type        = string
  default     = ""
}

variable "registry_login_server" {
  description = "Registry login server (required if registry_id not provided)"
  type        = string
  default     = ""
}

variable "registry_username" {
  description = "Registry username (optional when using managed identity)"
  type        = string
  default     = ""
}

variable "registry_password" {
  description = "Registry password (optional when using managed identity)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "target_port" {
  description = "Container port"
  type        = number
  default     = 8080
}

variable "command" {
  description = "Optional container command override"
  type        = list(string)
  default     = null
}

variable "args" {
  description = "Optional container args override"
  type        = list(string)
  default     = null
}

variable "cpu" {
  description = "vCPU"
  type        = number
  default     = 0.5
}

variable "memory" {
  description = "Memory (Gi)"
  type        = string
  default     = "1Gi"
}

variable "min_replicas" {
  description = "Min replicas"
  type        = number
  default     = 1
}

variable "max_replicas" {
  description = "Max replicas"
  type        = number
  default     = 3
}

variable "ingress_external" {
  description = "Expose app publicly"
  type        = bool
  default     = true
}

variable "ingress_allowed_cidrs" {
  description = "Ingress CIDR allowlist"
  type        = list(string)
  default     = []
}

variable "app_settings" {
  description = "Non-secret env vars"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets map"
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "secret_environment_overrides" {
  description = "Env var -> secret name"
  type        = map(string)
  default     = {}
}

variable "inject_identity_client_id" {
  description = "Inject the user-assigned identity client ID as AZURE_CLIENT_ID"
  type        = bool
  default     = true
}

variable "key_vault_name" {
  description = "Key Vault name (required if not creating)"
  type        = string
  default     = ""
}

variable "key_vault_resource_group" {
  description = "Key Vault resource group (required if not creating)"
  type        = string
  default     = ""
}

variable "create_key_vault" {
  description = "Create a Key Vault in the workload resource group"
  type        = bool
  default     = false
}

variable "key_vault_sku" {
  description = "Key Vault SKU (standard or premium)"
  type        = string
  default     = "standard"
}

variable "key_vault_soft_delete_retention_days" {
  description = "Key Vault soft delete retention days"
  type        = number
  default     = 7
}

variable "key_vault_purge_protection_enabled" {
  description = "Enable purge protection for Key Vault"
  type        = bool
  default     = true
}

variable "key_vault_ip_rules" {
  description = "List of IP CIDRs to allow for Key Vault access when using an existing vault (RBAC mode)."
  type        = list(string)
  default     = []
}

variable "dns_zone_name" {
  description = "Public DNS zone name for custom domain (optional)"
  type        = string
  default     = ""
}

variable "dns_zone_resource_group" {
  description = "Resource group of the DNS zone (required if dns_zone_name is set)"
  type        = string
  default     = ""
}

variable "dns_record_name" {
  description = "Record name to create within the DNS zone (e.g., jina-mcp)"
  type        = string
  default     = ""
}

variable "custom_domain" {
  description = "Optional custom domain configuration for the Container App managed certificate"
  type = object({
    hostname         = string
    certificate_name = optional(string)
  })
  default = null
}

variable "managed_certificate_enabled" {
  description = "Whether to create and bind a managed certificate for the custom domain."
  type        = bool
  default     = false
}

# Backend (bootstrap state) inputs
variable "state_resource_group_name" {
  description = "State RG name"
  type        = string
}

variable "state_storage_account_name" {
  description = "State storage account name"
  type        = string
}

variable "state_container_name" {
  description = "State container name"
  type        = string
}

variable "state_blob_key" {
  description = "State blob key for this stack"
  type        = string
}
