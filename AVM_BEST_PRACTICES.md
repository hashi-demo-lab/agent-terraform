# Azure Verified Modules (AVM) Best Practices for Terraform

This document summarizes the best practices from [Azure Verified Modules Terraform Specifications](https://azure.github.io/Azure-Verified-Modules/specs/tf/) and adapts them for generic Terraform module development across all cloud providers.

## Table of Contents

- [Module Classifications](#module-classifications)
- [Code Style Standards](#code-style-standards)
- [Naming and Composition](#naming-and-composition)
- [Inputs and Outputs](#inputs-and-outputs)
- [Validation and Linting](#validation-and-linting)
- [Testing Requirements](#testing-requirements)
- [Documentation Standards](#documentation-standards)
- [Telemetry and Monitoring](#telemetry-and-monitoring)
- [Contribution and Support](#contribution-and-support)
- [Release and Publishing](#release-and-publishing)

## Module Classifications

### Resource Modules
- **Purpose**: Single-purpose modules for specific cloud resources
- **Scope**: One primary resource with supporting configurations
- **Example**: AWS S3 bucket module with encryption, versioning, and access controls

### Pattern Modules
- **Purpose**: Multi-resource modules implementing common architectural patterns
- **Scope**: Multiple resources working together to solve a specific use case
- **Example**: Three-tier web application infrastructure with load balancer, compute, and database

### Utility Modules
- **Purpose**: Helper modules for common operations and transformations
- **Scope**: Data processing, calculations, or reusable logic
- **Example**: Data transformation modules, naming convention generators

## Code Style Standards

Based on [Azure Verified Modules Terraform Resource Module Code Style Specifications](https://azure.github.io/Azure-Verified-Modules/specs/tf/res/#code-style), these standards ensure consistent, maintainable, and professional Terraform code.

### 1. Naming Conventions (MUST)
- **MUST** use `snake_case` for all Terraform constructs:
  - Locals
  - Variables
  - Outputs
  - Resources (symbolic names)
  - Modules (symbolic names)

```hcl
# Good - snake_case examples
variable "storage_account_name" {
  description = "Name of the storage account"
  type        = string
}

resource "azurerm_storage_account" "main_storage" {
  name = var.storage_account_name
}

output "storage_account_id" {
  value = azurerm_storage_account.main_storage.id
}

# Avoid - other naming conventions
variable "storageAccountName" { } # camelCase
variable "StorageAccountName" { } # PascalCase
resource "azurerm_storage_account" "mainStorage" { } # mixed case
```

### 2. Variable Standards (MUST/SHOULD)
- **MUST** define `type` for every variable (avoid `any` unless absolutely necessary)
- **SHOULD** provide comprehensive descriptions for all variables
- **SHOULD** use positive statements for feature toggles (`xxx_enabled` vs `xxx_disabled`)
- **MUST** mark sensitive variables appropriately
- **SHOULD** provide non-nullable defaults for collection values

```hcl
# Good - Complete variable definition
variable "enable_encryption" {
  description = "Enable encryption for the storage account"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups (1-365)"
  type        = number
  default     = 30
  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 365
    error_message = "Backup retention days must be between 1 and 365."
  }
}

variable "tags" {
  description = "A map of tags to assign to resources"
  type        = map(string)
  default     = {}
}

# Object type with detailed description
variable "network_security_group" {
  description = <<-EOT
    Network security group configuration:
    - `id` - (Required) Resource ID of existing NSG
    - `create_new` - (Optional) Create new NSG if none provided
  EOT
  type = object({
    id         = string
    create_new = optional(bool, false)
  })
  default = null
}

# Avoid - Missing type and description
variable "some_setting" {
  default = "value"
}
```

### 3. Resource and Data Block Organization (SHOULD)
Resources and data sources **SHOULD** be organized with the following order:

**Meta-arguments (top of block):**
1. `provider`
2. `count`
3. `for_each`

**Main content (alphabetical order):**
1. Required arguments
2. Optional arguments
3. Required nested blocks
4. Optional nested blocks

**Meta-arguments (bottom of block):**
1. `depends_on`
2. `lifecycle`

```hcl
# Good - Proper resource organization
resource "azurerm_storage_account" "main" {
  # Meta-arguments first
  count = var.create_storage_account ? 1 : 0

  # Required arguments (alphabetical)
  location            = var.location
  name                = local.storage_account_name
  resource_group_name = var.resource_group_name

  # Optional arguments (alphabetical)
  account_kind             = var.account_kind
  account_replication_type = var.replication_type
  account_tier            = var.account_tier
  enable_https_traffic_only = true

  # Nested blocks
  blob_properties {
    delete_retention_policy {
      days = var.blob_retention_days
    }
  }

  # Meta-arguments last
  depends_on = [azurerm_resource_group.main]

  lifecycle {
    ignore_changes = [tags]
  }
}
```

### 4. Count and for_each Usage (MUST)
- **MUST** use `map(xxx)` or `set(xxx)` for `for_each` collections
- Map keys or set elements **MUST** be static literals
- Use `count` for conditional resource creation

```hcl
# Good - Conditional resource creation with count
resource "azurerm_network_security_group" "this" {
  count               = var.create_new_security_group ? 1 : 0
  name                = coalesce(var.new_network_security_group_name, "${var.subnet_name}-nsg")
  resource_group_name = var.resource_group_name
  location            = var.location
}

# Good - for_each with map
resource "azurerm_subnet" "subnets" {
  for_each = var.subnet_map # map(string)
  
  name                 = each.key
  virtual_network_name = azurerm_virtual_network.main.name
  resource_group_name  = var.resource_group_name
  address_prefixes     = [each.value]
}

# Avoid - for_each with computed values
resource "azurerm_subnet" "bad_example" {
  for_each = toset([azurerm_subnet.computed.name]) # Computed value
}
```

### 5. Dynamic Blocks (MUST)
For optional nested objects, **MUST** use the following pattern:

```hcl
resource "azurerm_kubernetes_cluster" "main" {
  # ... other configuration

  dynamic "identity" {
    for_each = var.client_id == "" || var.client_secret == "" ? [1] : []

    content {
      type                      = var.identity_type
      user_assigned_identity_id = var.user_assigned_identity_id
    }
  }
}
```

### 6. Default Values and Null Handling (SHOULD)
- **SHOULD** use `coalesce()` and `try()` for default values instead of ternary operators
- **SHOULD** use null comparison toggle pattern for complex conditional logic

```hcl
# Good - Using coalesce for defaults
locals {
  storage_account_name = coalesce(var.storage_account_name, "${var.project_name}-${var.environment}-storage")
}

# Good - Null comparison toggle pattern
variable "security_group" {
  description = "Security group configuration"
  type = object({
    id = string
  })
  default = null
}

resource "azurerm_network_security_group" "this" {
  count = var.security_group == null ? 1 : 0
  # ... configuration
}

# Avoid - Ternary operators for defaults
locals {
  storage_name = var.storage_account_name == null ? "${var.project_name}-storage" : var.storage_account_name
}
```

### 7. Ignore Changes and Lifecycle (MUST)
- **MUST NOT** use double quotes in `ignore_changes`
- **SHOULD** set `prevent_deletion_if_contains_resources` for resource groups

```hcl
# Good - No quotes in ignore_changes
resource "azurerm_storage_account" "main" {
  # ... configuration

  lifecycle {
    ignore_changes = [
      tags,
      location
    ]
  }
}

# Good - Resource group with prevention
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location

  lifecycle {
    prevent_destroy = true
  }
}

# Avoid - Quotes in ignore_changes
lifecycle {
  ignore_changes = [
    "tags",  # Don't use quotes
    "location"
  ]
}
```

### 8. Provider Configuration (MUST)
- **MUST** declare all providers in `required_providers` block
- **MUST NOT** include provider configurations in modules (pass through configuration)

```hcl
# Good - Required providers declaration
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"
    }
  }
}

# Avoid - Provider configuration in module
provider "azurerm" {
  features {}
  subscription_id = var.subscription_id  # Don't configure in modules
}
```

### 9. File Organization (MAY)
- **MAY** use `locals.tf` for locals only
- **SHOULD** use precise types for locals when possible
- **SHOULD** organize files logically (main.tf, variables.tf, outputs.tf, etc.)

```hcl
# locals.tf - Precise typing
locals {
  # Precise object type instead of any
  storage_config = {
    name                = var.storage_account_name
    tier               = var.account_tier
    replication_type   = var.replication_type
    enable_encryption  = var.enable_encryption
  }
  
  # Computed tags
  common_tags = merge(var.tags, {
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}
```

### 10. Feature Toggles and Deprecation (MUST)
- **MUST** use feature toggles for optional functionality
- **MUST** handle deprecated variables and outputs properly with warnings

```hcl
# Feature toggle pattern
variable "enable_advanced_security" {
  description = "Enable advanced security features"
  type        = bool
  default     = false
}

resource "azurerm_security_center_setting" "main" {
  count        = var.enable_advanced_security ? 1 : 0
  setting_name = "MCAS"
  enabled      = true
}

# Deprecated variable handling
variable "old_parameter_name" {
  description = "DEPRECATED: Use 'new_parameter_name' instead. This parameter will be removed in v2.0.0"
  type        = string
  default     = null
  
  validation {
    condition = var.old_parameter_name == null
    error_message = "The 'old_parameter_name' parameter is deprecated. Please use 'new_parameter_name' instead."
  }
}
```

## Naming and Composition

### 1. Module Naming
- Use clear, descriptive module names
- Include the cloud provider and resource type
- Follow semantic versioning for releases

```
terraform-aws-s3-bucket
terraform-azure-storage-account
terraform-gcp-cloud-storage
```

### 2. Variable Naming
- Use descriptive names that explain the variable's purpose
- Group related variables with common prefixes
- Avoid abbreviations unless they're widely understood

```hcl
variable "storage_account_name" {
  description = "Name of the storage account"
  type        = string
}

variable "storage_account_tier" {
  description = "Performance tier of the storage account"
  type        = string
  default     = "Standard"
}
```

### 3. Output Naming
- Use consistent naming patterns for outputs
- Include the resource type in the output name
- Provide both ID and name outputs when applicable

```hcl
output "storage_account_id" {
  description = "The ID of the storage account"
  value       = azurerm_storage_account.main.id
}

output "storage_account_name" {
  description = "The name of the storage account"
  value       = azurerm_storage_account.main.name
}
```

## Inputs and Outputs

### 1. Variable Standards
- All variables must have descriptions
- Use appropriate variable types (string, number, bool, list, map, object)
- Implement validation rules where applicable
- Provide sensible defaults when possible

```hcl
variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "tags" {
  description = "A map of tags to assign to the resource"
  type        = map(string)
  default     = {}
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
  validation {
    condition     = var.backup_retention_days >= 1 && var.backup_retention_days <= 365
    error_message = "Backup retention days must be between 1 and 365."
  }
}
```

### 2. Output Standards
- All outputs must have descriptions
- Expose important resource attributes
- Use consistent naming conventions
- Mark sensitive outputs appropriately

```hcl
output "resource_id" {
  description = "The resource identifier of the created resource"
  value       = aws_resource.main.id
}

output "resource_arn" {
  description = "The ARN of the created resource"
  value       = aws_resource.main.arn
}

output "connection_string" {
  description = "Connection string for the resource"
  value       = aws_resource.main.connection_string
  sensitive   = true
}
```

## Validation and Linting

### 1. TFLint Baseline Rules
Use the [Azure Verified Modules TFLint Ruleset](https://github.com/Azure/tflint-ruleset-avm) for baseline linting and validation of Terraform modules. This official Microsoft ruleset ensures compliance with AVM specifications.

#### Installation
Add the following configuration to your `.tflint.hcl` file:

```hcl
plugin "avm" {
  enabled = true
  version = "0.14.1"
  source  = "github.com/Azure/tflint-ruleset-avm"
}
```

Install the plugin:
```bash
tflint --init
```

#### Usage
Run TFLint with the AVM ruleset:
```bash
tflint
```

#### Benefits
- **AVM Compliance**: Ensures modules follow Azure Verified Modules specifications
- **Automated Validation**: Catches common issues and anti-patterns early
- **Consistent Standards**: Enforces naming conventions and code style requirements
- **CI/CD Integration**: Can be integrated into automated pipelines for continuous validation

### 2. Additional Linting Tools
Complement the AVM TFLint ruleset with these additional tools:

#### terraform fmt
```bash
terraform fmt -recursive
```

#### terraform validate
```bash
terraform init
terraform validate
```

#### Trivy (Security and Compliance)
```bash
trivy config .
```

## Testing Requirements

### 1. Unit Testing
- Test individual module components
- Validate variable inputs and outputs
- Test edge cases and error conditions

```python
# Example using pytest and terraform testing framework
def test_module_creates_s3_bucket():
    """Test that the module creates an S3 bucket with correct configuration."""
    terraform = Terraform("examples/basic")
    terraform.init()
    terraform.plan()
    
    plan = terraform.show_plan()
    assert "aws_s3_bucket.main" in plan["planned_values"]["root_module"]["resources"]
```

### 2. Integration Testing
- Test module interactions with other modules
- Validate end-to-end scenarios
- Test with different variable combinations

### 3. Terraform Testing
- Use Terraform's native testing framework
- Create test configurations for different scenarios
- Validate resource creation and configuration

```hcl
# tests/s3_bucket_test.tftest.hcl
run "validate_s3_bucket_creation" {
  command = plan
  
  variables {
    bucket_name = "test-bucket"
    environment = "dev"
  }
  
  assert {
    condition     = aws_s3_bucket.main.bucket == "test-bucket-dev"
    error_message = "Bucket name should include environment suffix"
  }
}

run "validate_encryption_enabled" {
  command = plan
  
  variables {
    bucket_name = "test-bucket"
    enable_encryption = true
  }
  
  assert {
    condition     = length(aws_s3_bucket_server_side_encryption_configuration.main) > 0
    error_message = "Encryption should be enabled when enable_encryption is true"
  }
}
```

## Documentation Standards

### 1. README Requirements
- Module overview and purpose
- Usage examples
- Input and output documentation (auto-generated)
- Requirements and dependencies
- License information

### 2. Auto-Generated Documentation
- Use `terraform-docs` for automatic documentation generation
- Include examples in documentation
- Keep documentation up-to-date with code changes

```bash
# Generate documentation
terraform-docs markdown table --output-file README.md .
```

### 3. Example Documentation
- Provide multiple usage examples
- Include basic and advanced configurations
- Document common use cases

```hcl
# examples/basic/main.tf
module "s3_bucket" {
  source = "../../"
  
  bucket_name = "my-app-bucket"
  environment = "dev"
  
  tags = {
    Project = "MyApp"
    Owner   = "DevTeam"
  }
}
```

## Telemetry and Monitoring

### 1. Resource Tagging
- Implement consistent tagging strategy
- Include environment, project, and ownership tags
- Support custom tags through variables

```hcl
locals {
  common_tags = merge(
    {
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "terraform"
      Module      = "terraform-aws-s3-bucket"
    },
    var.tags
  )
}
```

### 2. Monitoring Integration
- Include monitoring and alerting configurations
- Expose metrics and logs
- Support integration with monitoring tools

### 3. Compliance Tracking
- Enable compliance and governance features
- Include security configurations by default
- Support audit logging

## Contribution and Support

### 1. Module Ownership
- Clear ownership and maintenance responsibilities
- Define support channels and response times
- Establish contribution guidelines

### 2. Issue Tracking
- Comprehensive issue tracking and resolution
- Use GitHub issues for bug reports and feature requests
- Maintain issue templates and labels

### 3. Community Support
- Active community engagement and support
- Regular updates and maintenance
- Clear communication channels

## Release and Publishing

### 1. Versioning
- Follow semantic versioning (SemVer)
- Tag releases appropriately
- Maintain changelog

### 2. Publishing
- Publish to appropriate registries (Terraform Registry, private registries)
- Include proper metadata and documentation
- Test releases before publishing

### 3. Lifecycle Management
- Plan for module lifecycle and deprecation
- Provide migration guides for breaking changes
- Maintain backward compatibility when possible

## Implementation Checklist

When creating or updating Terraform modules, ensure:

- [ ] Module follows appropriate classification (Resource/Pattern/Utility)
- [ ] Uses snake_case naming conventions
- [ ] All variables have descriptions and appropriate types
- [ ] Validation rules are implemented where needed
- [ ] All outputs have descriptions
- [ ] Sensitive outputs are marked appropriately
- [ ] Comprehensive testing is implemented
- [ ] Documentation is auto-generated and up-to-date
- [ ] Examples are provided for common use cases
- [ ] Consistent tagging strategy is implemented
- [ ] Security best practices are followed
- [ ] Module is properly versioned and published
- [ ] Contribution guidelines are established
- [ ] Support channels are defined

## References

- [Azure Verified Modules Terraform Specifications](https://azure.github.io/Azure-Verified-Modules/specs/tf/)
- [HashiCorp Terraform Best Practices](https://developer.hashicorp.com/terraform/language/modules/develop)
- [Terraform Registry Publishing Guidelines](https://developer.hashicorp.com/terraform/registry/modules/publish) 