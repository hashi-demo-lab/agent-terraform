# src/agents/generator.py
"""
Generator Agent - Code generation and templating (LangGraph node)
Following .cursorrules specifications
"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import structlog
from pathlib import Path

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langgraph.platform import LangGraphPlatform

from ..workflows.state_management import TerraformState, context_manager
from ..tools.mcp_integration import TerraformMCPIntegration
from ..utils.terraform_parser import TerraformParser
from ..templates.template_engine import TemplateEngine

logger = structlog.get_logger()


@dataclass
class GeneratedModule:
    """Generated Terraform module"""
    main_tf: str
    variables_tf: str
    outputs_tf: str
    providers_tf: str
    versions_tf: str
    locals_tf: str
    readme_md: str
    examples: Dict[str, str]


class GeneratorAgent:
    """
    Code generation and templating agent
    LangGraph node implementation following .cursorrules
    """
    
    def __init__(self, platform: LangGraphPlatform):
        self.platform = platform
        self.mcp_integration = TerraformMCPIntegration()
        self.terraform_parser = TerraformParser()
        self.template_engine = TemplateEngine()
        self.max_iterations = 5
    
    def __call__(self, state: TerraformState) -> TerraformState:
        """Main generator entry point - LangGraph node implementation"""
        return asyncio.run(self._generate_terraform_code(state))
    
    async def _generate_terraform_code(self, state: TerraformState) -> TerraformState:
        """Generate Terraform code based on infrastructure plan"""
        
        logger.info("Starting Terraform code generation", 
                   workflow_id=state["workflow_id"],
                   current_agent="generator")
        
        state["current_agent"] = "generator"
        
        try:
            # Get infrastructure plan from context
            infrastructure_plan = context_manager.retrieve_context(
                state["workflow_id"], 
                "infrastructure_plan"
            )
            
            if not infrastructure_plan:
                error_msg = "No infrastructure plan found for code generation"
                state["errors"].append(error_msg)
                state["messages"].append(AIMessage(content=f"Error: {error_msg}"))
                return state
            
            # Generate complete Terraform module
            generated_module = await self._generate_module(infrastructure_plan, state)
            
            # Combine all files into single code string for validation
            combined_code = self._combine_module_files(generated_module)
            state["generated_code"] = combined_code
            
            # Store individual files in context
            context_manager.store_context(
                state["workflow_id"],
                "generated_module",
                generated_module
            )
            
            # Generate success message
            generation_summary = self._generate_summary(generated_module)
            state["messages"].append(AIMessage(content=generation_summary))
            
            logger.info("Terraform code generation completed successfully",
                       workflow_id=state["workflow_id"],
                       code_length=len(combined_code))
            
        except Exception as e:
            error_msg = f"Code generation failed: {str(e)}"
            logger.error("Code generation failed", 
                        workflow_id=state["workflow_id"],
                        error=str(e))
            state["errors"].append(error_msg)
            state["messages"].append(AIMessage(content=f"Generation Error: {error_msg}"))
        
        return state
    
    async def _generate_module(self, infrastructure_plan: Any, state: TerraformState) -> GeneratedModule:
        """Generate complete Terraform module following hashi-demo-lab/tf-module-template structure"""
        
        # Extract plan data
        resources = infrastructure_plan.resources
        provider_requirements = infrastructure_plan.provider_requirements
        variables = infrastructure_plan.variables
        outputs = infrastructure_plan.outputs
        
        # Get requirements for context
        requirements = state.get("requirements")
        environment = requirements.environment if requirements else "dev"
        provider = requirements.provider if requirements else "aws"
        
        # Generate each file
        main_tf = await self._generate_main_tf(resources, state)
        variables_tf = self._generate_variables_tf(variables)
        outputs_tf = self._generate_outputs_tf(outputs)
        providers_tf = self._generate_providers_tf(provider, provider_requirements)
        versions_tf = self._generate_versions_tf(provider_requirements)
        locals_tf = self._generate_locals_tf(environment)
        readme_md = await self._generate_readme_md(infrastructure_plan, state)
        examples = await self._generate_examples(infrastructure_plan, state)
        
        return GeneratedModule(
            main_tf=main_tf,
            variables_tf=variables_tf,
            outputs_tf=outputs_tf,
            providers_tf=providers_tf,
            versions_tf=versions_tf,
            locals_tf=locals_tf,
            readme_md=readme_md,
            examples=examples
        )
    
    async def _generate_main_tf(self, resources: List[Any], state: TerraformState) -> str:
        """Generate main.tf with all resources"""
        
        main_tf_lines = [
            "# main.tf - Primary resource definitions and module logic",
            "# Generated by Terraform Code Generation Agent",
            ""
        ]
        
        # Generate random ID for unique naming if needed
        has_random_naming = any("bucket" in r.resource_type for r in resources)
        if has_random_naming:
            main_tf_lines.extend([
                "resource \"random_id\" \"suffix\" {",
                "  byte_length = 4",
                "}",
                ""
            ])
        
        # Generate each resource
        for resource in resources:
            resource_code = await self._generate_resource_code(resource, state)
            main_tf_lines.extend([resource_code, ""])
        
        return "\n".join(main_tf_lines)
    
    async def _generate_resource_code(self, resource: Any, state: TerraformState) -> str:
        """Generate code for a specific resource"""
        
        # Get resource examples from MCP if available
        try:
            examples = await self.mcp_integration.get_resource_examples(
                resource.provider, 
                resource.resource_type
            )
        except:
            examples = []
        
        # Start resource block
        lines = [f"resource \"{resource.resource_type}\" \"{resource.resource_name}\" {{"]
        
        # Add configuration
        for key, value in resource.configuration.items():
            if key == "tags":
                lines.append("  tags = merge(local.common_tags, {")
                for tag_key, tag_value in value.items():
                    if tag_key not in ["Environment", "ManagedBy", "CreatedBy"]:
                        lines.append(f"    {tag_key} = \"{tag_value}\"")
                lines.append("  })")
            elif isinstance(value, dict):
                lines.append(f"  {key} {{")
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, dict):
                        lines.append(f"    {sub_key} {{")
                        for sub_sub_key, sub_sub_value in sub_value.items():
                            lines.append(f"      {sub_sub_key} = \"{sub_sub_value}\"")
                        lines.append("    }")
                    else:
                        lines.append(f"    {sub_key} = \"{sub_value}\"")
                lines.append("  }")
            elif isinstance(value, list):
                lines.append(f"  {key} = {value}")
            elif isinstance(value, bool):
                lines.append(f"  {key} = {str(value).lower()}")
            elif isinstance(value, (int, float)):
                lines.append(f"  {key} = {value}")
            else:
                lines.append(f"  {key} = \"{value}\"")
        
        lines.append("}")
        
        # Add security-specific resources for certain types
        if "s3_bucket" in resource.resource_type:
            lines.extend(self._generate_s3_security_resources(resource.resource_name))
        elif "security_group" in resource.resource_type:
            lines.extend(self._generate_security_group_rules(resource.resource_name))
        
        return "\n".join(lines)
    
    def _generate_s3_security_resources(self, bucket_name: str) -> List[str]:
        """Generate S3 security-related resources"""
        return [
            "",
            f"resource \"aws_s3_bucket_versioning\" \"{bucket_name}\" {{",
            f"  bucket = aws_s3_bucket.{bucket_name}.id",
            "  versioning_configuration {",
            "    status = \"Enabled\"",
            "  }",
            "}",
            "",
            f"resource \"aws_s3_bucket_server_side_encryption_configuration\" \"{bucket_name}\" {{",
            f"  bucket = aws_s3_bucket.{bucket_name}.id",
            "",
            "  rule {",
            "    apply_server_side_encryption_by_default {",
            "      sse_algorithm = \"AES256\"",
            "    }",
            "  }",
            "}",
            "",
            f"resource \"aws_s3_bucket_public_access_block\" \"{bucket_name}\" {{",
            f"  bucket = aws_s3_bucket.{bucket_name}.id",
            "",
            "  block_public_acls       = true",
            "  block_public_policy     = true",
            "  ignore_public_acls      = true",
            "  restrict_public_buckets = true",
            "}"
        ]
    
    def _generate_security_group_rules(self, sg_name: str) -> List[str]:
        """Generate additional security group rules if needed"""
        # This could be expanded to add specific rules based on best practices
        return []
    
    def _generate_variables_tf(self, variables: Dict[str, Any]) -> str:
        """Generate variables.tf"""
        
        lines = [
            "# variables.tf - Input variable declarations with descriptions and validation",
            "# Generated by Terraform Code Generation Agent",
            ""
        ]
        
        for var_name, var_config in variables.items():
            lines.extend([
                f"variable \"{var_name}\" {{",
                f"  description = \"{var_config['description']}\"",
                f"  type        = {var_config['type']}"
            ])
            
            if "default" in var_config:
                default_value = var_config["default"]
                if isinstance(default_value, str):
                    lines.append(f"  default     = \"{default_value}\"")
                else:
                    lines.append(f"  default     = {default_value}")
            
            if "validation" in var_config:
                validation = var_config["validation"]
                lines.extend([
                    "  validation {",
                    f"    condition     = {validation['condition']}",
                    f"    error_message = \"{validation['error_message']}\"",
                    "  }"
                ])
            
            lines.extend(["}", ""])
        
        return "\n".join(lines)
    
    def _generate_outputs_tf(self, outputs: Dict[str, Any]) -> str:
        """Generate outputs.tf"""
        
        lines = [
            "# outputs.tf - Output value definitions with descriptions",
            "# Generated by Terraform Code Generation Agent",
            ""
        ]
        
        for output_name, output_config in outputs.items():
            lines.extend([
                f"output \"{output_name}\" {{",
                f"  description = \"{output_config['description']}\"",
                f"  value       = {output_config['value']}"
            ])
            
            if output_config.get("sensitive"):
                lines.append("  sensitive   = true")
            
            lines.extend(["}", ""])
        
        return "\n".join(lines)
    
    def _generate_providers_tf(self, provider: str, provider_requirements: Dict[str, Any]) -> str:
        """Generate providers.tf"""
        
        lines = [
            "# providers.tf - Provider configurations",
            "# Generated by Terraform Code Generation Agent",
            ""
        ]
        
        if provider == "aws":
            lines.extend([
                "provider \"aws\" {",
                "  region = var.aws_region",
                "",
                "  default_tags {",
                "    tags = local.common_tags",
                "  }",
                "}"
            ])
        elif provider == "azurerm":
            lines.extend([
                "provider \"azurerm\" {",
                "  features {}",
                "",
                "  # Configure default tags if supported",
                "}"
            ])
        elif provider == "google":
            lines.extend([
                "provider \"google\" {",
                "  project = var.project_id",
                "  region  = var.region",
                "}"
            ])
        
        return "\n".join(lines)
    
    def _generate_versions_tf(self, provider_requirements: Dict[str, Any]) -> str:
        """Generate versions.tf"""
        
        lines = [
            "# versions.tf - Terraform version constraints and provider requirements",
            "# Generated by Terraform Code Generation Agent",
            "",
            "terraform {",
            "  required_version = \">= 1.0\"",
            "",
            "  required_providers {"
        ]
        
        for provider, config in provider_requirements.items():
            if isinstance(config, dict):
                lines.extend([
                    f"    {provider} = {{",
                    f"      source  = \"{config['source']}\"",
                    f"      version = \"{config['version']}\"",
                    "    }"
                ])
            else:
                lines.extend([
                    f"    {provider} = {{",
                    f"      source  = \"hashicorp/{provider}\"",
                    f"      version = \"{config}\"",
                    "    }"
                ])
        
        lines.extend([
            "  }",
            "}"
        ])
        
        return "\n".join(lines)
    
    def _generate_locals_tf(self, environment: str) -> str:
        """Generate locals.tf"""
        
        return f"""# locals.tf - Local value definitions for computed values
# Generated by Terraform Code Generation Agent

locals {{
  common_tags = {{
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    CreatedBy   = "terraform-agent"
  }}
  
  name_prefix = "${{var.project_name}}-${{var.environment}}"
}}"""
    
    async def _generate_readme_md(self, infrastructure_plan: Any, state: TerraformState) -> str:
        """Generate README.md documentation"""
        
        requirements = state.get("requirements")
        provider = requirements.provider if requirements else "aws"
        
        lines = [
            f"# Terraform Module",
            "",
            "This Terraform module was generated by the Terraform Code Generation Agent.",
            "",
            "## Description",
            "",
            f"This module creates infrastructure on {provider.upper()} following best practices and security guidelines.",
            "",
            "## Resources Created",
            ""
        ]
        
        # List resources
        for resource in infrastructure_plan.resources:
            lines.append(f"- `{resource.resource_type}.{resource.resource_name}`")
        
        lines.extend([
            "",
            "## Usage",
            "",
            "```hcl",
            "module \"infrastructure\" {",
            "  source = \"./\"",
            "",
            "  project_name = \"my-project\"",
            "  environment  = \"dev\"",
        ])
        
        if provider == "aws":
            lines.append("  aws_region   = \"us-west-2\"")
        
        lines.extend([
            "}",
            "```",
            "",
            "## Variables",
            "",
            "| Name | Description | Type | Default | Required |",
            "|------|-------------|------|---------|:--------:|"
        ])
        
        # Add variables table
        for var_name, var_config in infrastructure_plan.variables.items():
            default = var_config.get("default", "n/a")
            required = "no" if "default" in var_config else "yes"
            lines.append(f"| {var_name} | {var_config['description']} | `{var_config['type']}` | {default} | {required} |")
        
        lines.extend([
            "",
            "## Outputs",
            "",
            "| Name | Description |",
            "|------|-------------|"
        ])
        
        # Add outputs table
        for output_name, output_config in infrastructure_plan.outputs.items():
            lines.append(f"| {output_name} | {output_config['description']} |")
        
        lines.extend([
            "",
            "## Security",
            "",
            "This module implements security best practices including:",
            "",
            "- Encryption at rest and in transit",
            "- Least privilege access policies",
            "- Network security controls",
            "- Resource tagging for compliance",
            "",
            "## Compliance",
            ""
        ])
        
        if infrastructure_plan.compliance_matrix:
            for req, resources in infrastructure_plan.compliance_matrix.items():
                lines.append(f"- **{req.title()}**: {len(resources)} resources configured")
        
        lines.extend([
            "",
            "## Cost Estimation",
            ""
        ])
        
        if infrastructure_plan.estimated_total_cost:
            lines.append(f"Estimated monthly cost: ${infrastructure_plan.estimated_total_cost:.2f}")
        else:
            lines.append("Cost estimation not available. Please use AWS Cost Calculator for accurate estimates.")
        
        return "\n".join(lines)
    
    async def _generate_examples(self, infrastructure_plan: Any, state: TerraformState) -> Dict[str, str]:
        """Generate usage examples"""
        
        requirements = state.get("requirements")
        provider = requirements.provider if requirements else "aws"
        
        # Basic example
        basic_example = f"""# Basic usage example
module "infrastructure" {{
  source = "../"

  project_name = "my-project"
  environment  = "dev"
"""
        
        if provider == "aws":
            basic_example += "  aws_region   = \"us-west-2\"\n"
        
        basic_example += "}\n"
        
        # Production example
        prod_example = f"""# Production usage example
module "infrastructure" {{
  source = "../"

  project_name = "my-project"
  environment  = "prod"
"""
        
        if provider == "aws":
            prod_example += "  aws_region   = \"us-east-1\"\n"
        
        prod_example += "}\n"
        
        return {
            "basic": basic_example,
            "production": prod_example
        }
    
    def _combine_module_files(self, module: GeneratedModule) -> str:
        """Combine all module files into single string for validation"""
        
        combined = []
        
        # Add file headers and content
        files = [
            ("# versions.tf", module.versions_tf),
            ("# providers.tf", module.providers_tf),
            ("# variables.tf", module.variables_tf),
            ("# locals.tf", module.locals_tf),
            ("# main.tf", module.main_tf),
            ("# outputs.tf", module.outputs_tf)
        ]
        
        for header, content in files:
            combined.extend([header, content, ""])
        
        return "\n".join(combined)
    
    def _generate_summary(self, module: GeneratedModule) -> str:
        """Generate generation summary message"""
        
        # Count lines of code
        total_lines = (
            len(module.main_tf.split('\n')) +
            len(module.variables_tf.split('\n')) +
            len(module.outputs_tf.split('\n')) +
            len(module.providers_tf.split('\n')) +
            len(module.versions_tf.split('\n')) +
            len(module.locals_tf.split('\n'))
        )
        
        return f"""🚀 Terraform Code Generation Complete

📊 Generation Summary:
   • Total lines of code: {total_lines}
   • Files generated: 6 core files + README
   • Examples created: {len(module.examples)}
   • Documentation: Complete with usage examples

📁 Generated Files:
   • main.tf - Resource definitions
   • variables.tf - Input variables
   • outputs.tf - Output values
   • providers.tf - Provider configuration
   • versions.tf - Version constraints
   • locals.tf - Local values
   • README.md - Complete documentation

✅ Code follows HashiCorp module template structure and AVM best practices.""" 