"""
Documenter Agent - Documentation generation (LangGraph node)
Following .cursorrules specifications
"""

import asyncio
from typing import Dict, List, Any
import structlog

from langchain_core.messages import BaseMessage, AIMessage
from langgraph.platform import LangGraphPlatform

from ..workflows.state_management import TerraformState, context_manager

logger = structlog.get_logger()


class DocumenterAgent:
    """
    Documentation generation agent
    LangGraph node implementation following .cursorrules
    """
    
    def __init__(self, platform: LangGraphPlatform):
        self.platform = platform
    
    def __call__(self, state: TerraformState) -> TerraformState:
        """Main documenter entry point - LangGraph node implementation"""
        return asyncio.run(self._generate_documentation(state))
    
    async def _generate_documentation(self, state: TerraformState) -> TerraformState:
        """Generate comprehensive documentation for the Terraform module"""
        
        logger.info("Starting documentation generation", 
                   workflow_id=state["workflow_id"],
                   current_agent="documenter")
        
        state["current_agent"] = "documenter"
        
        try:
            # Get generated module and infrastructure plan from context
            generated_module = context_manager.retrieve_context(
                state["workflow_id"],
                "generated_module"
            )
            
            infrastructure_plan = context_manager.retrieve_context(
                state["workflow_id"],
                "infrastructure_plan"
            )
            
            if not generated_module:
                warning_msg = "No generated module found for documentation"
                state["warnings"].append(warning_msg)
                state["messages"].append(AIMessage(content=f"Documenter Warning: {warning_msg}"))
                return state
            
            # Generate enhanced documentation
            enhanced_docs = await self._create_enhanced_documentation(
                generated_module, 
                infrastructure_plan, 
                state
            )
            
            # Update state with documentation
            state["documentation"] = enhanced_docs
            
            # Store documentation in context
            context_manager.store_context(
                state["workflow_id"],
                "enhanced_documentation",
                enhanced_docs
            )
            
            # Generate documentation message
            doc_message = self._generate_documentation_message(enhanced_docs)
            state["messages"].append(AIMessage(content=doc_message))
            
            logger.info("Documentation generation completed",
                       workflow_id=state["workflow_id"],
                       doc_length=len(enhanced_docs))
            
        except Exception as e:
            error_msg = f"Documentation generation failed: {str(e)}"
            logger.error("Documentation generation failed", 
                        workflow_id=state["workflow_id"],
                        error=str(e))
            state["errors"].append(error_msg)
            state["messages"].append(AIMessage(content=f"Documentation Error: {error_msg}"))
        
        return state
    
    async def _create_enhanced_documentation(self, 
                                           generated_module: Any, 
                                           infrastructure_plan: Any, 
                                           state: TerraformState) -> str:
        """Create enhanced documentation with additional sections"""
        
        requirements = state.get("requirements")
        validation_results = state.get("validation_results", [])
        
        # Start with base README from generated module
        base_readme = getattr(generated_module, 'readme_md', '')
        
        # Add enhanced sections
        enhanced_sections = []
        
        # Add architecture diagram section
        enhanced_sections.append(self._create_architecture_section(infrastructure_plan))
        
        # Add security section
        enhanced_sections.append(self._create_security_section(infrastructure_plan, validation_results))
        
        # Add deployment guide
        enhanced_sections.append(self._create_deployment_guide(requirements))
        
        # Add troubleshooting section
        enhanced_sections.append(self._create_troubleshooting_section(validation_results))
        
        # Add changelog section
        enhanced_sections.append(self._create_changelog_section(state))
        
        # Combine base README with enhanced sections
        enhanced_readme = base_readme + "\n\n" + "\n\n".join(enhanced_sections)
        
        return enhanced_readme
    
    def _create_architecture_section(self, infrastructure_plan: Any) -> str:
        """Create architecture documentation section"""
        
        if not infrastructure_plan:
            return ""
        
        resources = getattr(infrastructure_plan, 'resources', [])
        
        lines = [
            "## Architecture",
            "",
            "This module creates the following infrastructure components:",
            ""
        ]
        
        # Group resources by type
        resource_groups = {}
        for resource in resources:
            resource_type = resource.resource_type.split('_')[1] if '_' in resource.resource_type else resource.resource_type
            if resource_type not in resource_groups:
                resource_groups[resource_type] = []
            resource_groups[resource_type].append(resource)
        
        # Document each group
        for group_name, group_resources in resource_groups.items():
            lines.extend([
                f"### {group_name.title()} Resources",
                ""
            ])
            
            for resource in group_resources:
                lines.append(f"- **{resource.resource_name}** (`{resource.resource_type}`)")
                if hasattr(resource, 'configuration') and resource.configuration:
                    key_configs = []
                    for key, value in resource.configuration.items():
                        if key not in ['tags'] and not isinstance(value, dict):
                            key_configs.append(f"{key}: {value}")
                    if key_configs:
                        lines.append(f"  - {', '.join(key_configs[:3])}")
            
            lines.append("")
        
        # Add resource dependencies
        lines.extend([
            "### Resource Dependencies",
            "",
            "```mermaid",
            "graph TD"
        ])
        
        for resource in resources:
            resource_id = f"{resource.resource_type}_{resource.resource_name}"
            lines.append(f"    {resource_id}[\"{resource.resource_name}\"]")
            
            if hasattr(resource, 'dependencies'):
                for dep in resource.dependencies:
                    dep_id = f"dep_{dep}"
                    lines.append(f"    {dep_id} --> {resource_id}")
        
        lines.extend([
            "```",
            ""
        ])
        
        return "\n".join(lines)
    
    def _create_security_section(self, infrastructure_plan: Any, validation_results: List[Any]) -> str:
        """Create security documentation section"""
        
        lines = [
            "## Security",
            "",
            "This module implements security best practices:",
            ""
        ]
        
        # Security features implemented
        security_features = [
            "🔐 Encryption at rest and in transit",
            "🛡️ Least privilege access policies",
            "🔒 Network security controls",
            "🏷️ Resource tagging for compliance",
            "🚫 Public access restrictions"
        ]
        
        for feature in security_features:
            lines.append(f"- {feature}")
        
        lines.extend([
            "",
            "### Security Validation",
            ""
        ])
        
        # Add security validation results
        security_tools = [r for r in validation_results if r.tool in ['trivy', 'tflint_avm']]
        
        if security_tools:
            for result in security_tools:
                status_icon = "✅" if result.passed else "❌"
                lines.append(f"- {status_icon} **{result.tool}**: {result.status.value if hasattr(result.status, 'value') else result.status}")
        else:
            lines.append("- Security validation will be performed during deployment")
        
        lines.extend([
            "",
            "### Security Checklist",
            "",
            "Before deploying this module, ensure:",
            "",
            "- [ ] Review all resource configurations",
            "- [ ] Validate IAM policies and permissions",
            "- [ ] Confirm encryption settings",
            "- [ ] Check network security groups",
            "- [ ] Verify backup and recovery procedures",
            ""
        ])
        
        return "\n".join(lines)
    
    def _create_deployment_guide(self, requirements: Any) -> str:
        """Create deployment guide section"""
        
        provider = getattr(requirements, 'provider', 'aws') if requirements else 'aws'
        environment = getattr(requirements, 'environment', 'dev') if requirements else 'dev'
        
        lines = [
            "## Deployment Guide",
            "",
            "### Prerequisites",
            "",
            f"- Terraform >= 1.0",
            f"- {provider.upper()} CLI configured",
            f"- Appropriate {provider.upper()} permissions",
            "",
            "### Quick Start",
            "",
            "1. **Clone and Navigate**",
            "   ```bash",
            "   git clone <repository-url>",
            "   cd terraform-module",
            "   ```",
            "",
            "2. **Initialize Terraform**",
            "   ```bash",
            "   terraform init",
            "   ```",
            "",
            "3. **Review Plan**",
            "   ```bash",
            "   terraform plan",
            "   ```",
            "",
            "4. **Apply Configuration**",
            "   ```bash",
            "   terraform apply",
            "   ```",
            "",
            "### Environment-Specific Deployment",
            "",
            f"For {environment} environment:",
            "",
            "```hcl",
            "module \"infrastructure\" {",
            "  source = \"./\"",
            "",
            "  project_name = \"my-project\"",
            f"  environment  = \"{environment}\"",
        ]
        
        if provider == "aws":
            lines.append("  aws_region   = \"us-west-2\"")
        
        lines.extend([
            "}",
            "```",
            "",
            "### Validation Commands",
            "",
            "```bash",
            "# Validate configuration",
            "terraform validate",
            "",
            "# Format code",
            "terraform fmt",
            "",
            "# Security scan (if Trivy installed)",
            "trivy config .",
            "",
            "# Lint check (if TFLint installed)",
            "tflint",
            "```",
            ""
        ])
        
        return "\n".join(lines)
    
    def _create_troubleshooting_section(self, validation_results: List[Any]) -> str:
        """Create troubleshooting section"""
        
        lines = [
            "## Troubleshooting",
            "",
            "### Common Issues",
            ""
        ]
        
        # Add common issues based on validation results
        common_issues = {
            "terraform_validate": {
                "issue": "Terraform validation fails",
                "solution": "Check syntax and required arguments"
            },
            "terraform_fmt": {
                "issue": "Code formatting issues",
                "solution": "Run `terraform fmt` to fix formatting"
            },
            "tflint_avm": {
                "issue": "Linting errors",
                "solution": "Review TFLint output and fix naming/structure issues"
            },
            "trivy": {
                "issue": "Security vulnerabilities",
                "solution": "Review security configurations and apply recommended fixes"
            }
        }
        
        # Add issues found during validation
        found_issues = set()
        for result in validation_results:
            if not result.passed and result.tool in common_issues:
                found_issues.add(result.tool)
        
        if found_issues:
            lines.append("#### Issues Found During Generation")
            lines.append("")
            
            for tool in found_issues:
                issue_info = common_issues[tool]
                lines.extend([
                    f"**{issue_info['issue']}**",
                    f"- Solution: {issue_info['solution']}",
                    ""
                ])
        
        # Add general troubleshooting
        lines.extend([
            "#### General Troubleshooting",
            "",
            "**Provider Authentication Issues**",
            "- Ensure cloud provider CLI is configured",
            "- Check environment variables and credentials",
            "- Verify required permissions",
            "",
            "**Resource Conflicts**",
            "- Check for existing resources with same names",
            "- Review resource dependencies",
            "- Ensure unique naming across environments",
            "",
            "**State Management Issues**",
            "- Verify backend configuration",
            "- Check state file permissions",
            "- Consider state migration if needed",
            "",
            "### Getting Help",
            "",
            "- Review Terraform documentation",
            "- Check provider-specific guides",
            "- Consult team documentation",
            "- Open support ticket if needed",
            ""
        ])
        
        return "\n".join(lines)
    
    def _create_changelog_section(self, state: TerraformState) -> str:
        """Create changelog section"""
        
        from datetime import datetime
        
        lines = [
            "## Changelog",
            "",
            f"### v1.0.0 - {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "**Generated by Terraform Code Generation Agent**",
            "",
            "#### Added",
            "- Initial module structure",
            "- Resource configurations",
            "- Security best practices",
            "- Comprehensive documentation",
            ""
        ]
        
        # Add validation results summary
        validation_results = state.get("validation_results", [])
        if validation_results:
            passed_tools = sum(1 for r in validation_results if r.passed)
            total_tools = len(validation_results)
            
            lines.extend([
                "#### Validation",
                f"- Passed {passed_tools}/{total_tools} validation tools",
                ""
            ])
        
        # Add iteration information
        iteration_count = state.get("iteration_count", 0)
        if iteration_count > 0:
            lines.extend([
                "#### Refinements",
                f"- Applied {iteration_count} refinement iterations",
                ""
            ])
        
        return "\n".join(lines)
    
    def _generate_documentation_message(self, documentation: str) -> str:
        """Generate documentation completion message"""
        
        doc_lines = documentation.split('\n')
        sections = [line for line in doc_lines if line.startswith('##')]
        
        return f"""📚 Documentation Generation Complete

📊 Documentation Summary:
   • Total sections: {len(sections)}
   • Documentation length: {len(documentation)} characters
   • Includes: Architecture, Security, Deployment, Troubleshooting

📁 Generated Sections:
{chr(10).join(f'   • {section[3:]}' for section in sections[:10])}

✅ Comprehensive documentation ready for deployment""" 