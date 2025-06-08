# Terraform Code Generation Agent

A comprehensive Terraform code generation agent that follows industry best practices and integrates with modern tooling for Infrastructure as Code (IaC) development.

## Features

- **Azure Verified Modules (AVM) Best Practices**: Implements comprehensive best practices from [Azure Verified Modules](https://azure.github.io/Azure-Verified-Modules/specs/tf/)
- **HashiCorp Template Structure**: Follows [hashi-demo-lab/tf-module-template](https://github.com/hashi-demo-lab/tf-module-template) structure
- **AWS Provider Focus**: Optimized for [HashiCorp Terraform AWS Provider](https://github.com/hashicorp/terraform-provider-aws)
- **MCP Integration**: Leverages [HashiCorp Terraform MCP Server](https://github.com/hashicorp/terraform-mcp-server) for registry access
- **Multi-tool Validation**: Integrates terraform, tflint, trivy, and checkov validation
- **LangGraph Workflows**: Uses LangGraph for agent orchestration and workflow management
- **LangMem Context**: Implements persistent context management with LangMem

## Documentation

- [Azure Verified Modules Best Practices](./AVM_BEST_PRACTICES.md) - Comprehensive guide to AVM best practices
- [Cursor Rules](./.cursorrules) - Development rules and standards for the agent

## Quick Start

The agent follows a structured approach to Terraform module generation:

1. **Requirements Analysis** - Analyzes infrastructure requirements
2. **Code Generation** - Generates Terraform code following best practices
3. **Validation Pipeline** - Runs comprehensive validation tools
4. **Refinement** - Iteratively improves code based on validation results
5. **Documentation** - Auto-generates documentation with terraform-docs

## Module Classifications

The agent supports three types of Terraform modules:

- **Resource Modules**: Single-purpose modules for specific cloud resources
- **Pattern Modules**: Multi-resource modules implementing common architectural patterns
- **Utility Modules**: Helper modules for common operations and transformations

## Best Practices

This agent implements industry-leading best practices including:

- Snake_case naming conventions
- Comprehensive variable validation
- Security-first approach with encryption by default
- Consistent resource tagging
- Auto-generated documentation
- Comprehensive testing strategies
- Telemetry and monitoring integration

## Integration Points

- **Version Control**: Git integration for module versioning
- **CI/CD**: GitHub Actions/GitLab CI templates
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **Cloud Integration**: Support for Terraform Cloud/Enterprise
- **Registry Access**: Automated provider and module discovery through MCP tools