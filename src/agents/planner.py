"""
Planner Agent - Requirements analysis and resource planning (LangGraph node)
Following .cursorrules specifications
"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import structlog

from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langgraph.platform import LangGraphPlatform

from ..workflows.state_management import TerraformState, RequirementSpec, context_manager
from ..tools.mcp_integration import TerraformMCPIntegration
from ..config.validation_rules import ValidationRuleEngine

logger = structlog.get_logger()


@dataclass
class ResourcePlan:
    """Planned resource configuration"""
    resource_type: str
    resource_name: str
    provider: str
    configuration: Dict[str, Any]
    dependencies: List[str]
    compliance_requirements: List[str]
    estimated_cost: Optional[float] = None


@dataclass
class InfrastructurePlan:
    """Complete infrastructure plan"""
    resources: List[ResourcePlan]
    provider_requirements: Dict[str, str]
    variables: Dict[str, Any]
    outputs: Dict[str, Any]
    compliance_matrix: Dict[str, List[str]]
    estimated_total_cost: Optional[float] = None


class PlannerAgent:
    """
    Requirements analysis and resource planning agent
    LangGraph node implementation following .cursorrules
    """
    
    def __init__(self, platform: LangGraphPlatform):
        self.platform = platform
        self.mcp_integration = TerraformMCPIntegration()
        self.validation_engine = ValidationRuleEngine()
        self.max_iterations = 5
        
        # Resource type mappings for different providers
        self.provider_resource_mappings = {
            "aws": {
                "compute": ["aws_instance", "aws_autoscaling_group", "aws_launch_template"],
                "storage": ["aws_s3_bucket", "aws_ebs_volume", "aws_efs_file_system"],
                "database": ["aws_rds_instance", "aws_dynamodb_table", "aws_elasticache_cluster"],
                "network": ["aws_vpc", "aws_subnet", "aws_security_group", "aws_lb"],
                "security": ["aws_iam_role", "aws_kms_key", "aws_acm_certificate"]
            },
            "azurerm": {
                "compute": ["azurerm_virtual_machine", "azurerm_virtual_machine_scale_set"],
                "storage": ["azurerm_storage_account", "azurerm_managed_disk"],
                "database": ["azurerm_sql_database", "azurerm_cosmosdb_account"],
                "network": ["azurerm_virtual_network", "azurerm_subnet", "azurerm_network_security_group"],
                "security": ["azurerm_key_vault", "azurerm_role_assignment"]
            },
            "google": {
                "compute": ["google_compute_instance", "google_compute_instance_group"],
                "storage": ["google_storage_bucket", "google_compute_disk"],
                "database": ["google_sql_database_instance", "google_firestore_database"],
                "network": ["google_compute_network", "google_compute_subnetwork", "google_compute_firewall"],
                "security": ["google_kms_crypto_key", "google_project_iam_binding"]
            }
        }
    
    def __call__(self, state: TerraformState) -> TerraformState:
        """Main planner entry point - LangGraph node implementation"""
        return asyncio.run(self._plan_infrastructure(state))
    
    async def _plan_infrastructure(self, state: TerraformState) -> TerraformState:
        """Plan infrastructure based on requirements"""
        
        logger.info("Starting infrastructure planning", 
                   workflow_id=state["workflow_id"],
                   current_agent="planner")
        
        state["current_agent"] = "planner"
        
        # Validate requirements
        requirements = state.get("requirements")
        if not requirements:
            error_msg = "No requirements provided for planning"
            state["errors"].append(error_msg)
            state["messages"].append(AIMessage(content=f"Error: {error_msg}"))
            return state
        
        try:
            # Analyze requirements and create plan
            infrastructure_plan = await self._analyze_requirements(requirements, state)
            
            # Store plan in context
            context_manager.store_context(
                state["workflow_id"], 
                "infrastructure_plan", 
                infrastructure_plan
            )
            
            # Update state with planning results
            state["analysis_results"]["infrastructure_plan"] = infrastructure_plan.__dict__
            
            # Generate planning summary message
            planning_summary = self._generate_planning_summary(infrastructure_plan)
            state["messages"].append(AIMessage(content=planning_summary))
            
            logger.info("Infrastructure planning completed successfully",
                       workflow_id=state["workflow_id"],
                       resources_planned=len(infrastructure_plan.resources))
            
        except Exception as e:
            error_msg = f"Planning failed: {str(e)}"
            logger.error("Planning failed", 
                        workflow_id=state["workflow_id"],
                        error=str(e))
            state["errors"].append(error_msg)
            state["messages"].append(AIMessage(content=f"Planning Error: {error_msg}"))
        
        return state
    
    async def _analyze_requirements(self, requirements: RequirementSpec, state: TerraformState) -> InfrastructurePlan:
        """Analyze requirements and create detailed infrastructure plan"""
        
        # Initialize MCP context for provider information
        await self._initialize_mcp_context(requirements.provider, state)
        
        # Plan resources
        planned_resources = []
        for resource_req in requirements.resources:
            resource_plan = await self._plan_resource(
                resource_req, 
                requirements.provider,
                requirements.environment,
                state
            )
            planned_resources.append(resource_plan)
        
        # Determine provider requirements
        provider_requirements = await self._determine_provider_requirements(
            requirements.provider, 
            planned_resources
        )
        
        # Plan variables
        variables = self._plan_variables(requirements, planned_resources)
        
        # Plan outputs
        outputs = self._plan_outputs(planned_resources)
        
        # Create compliance matrix
        compliance_matrix = self._create_compliance_matrix(
            planned_resources, 
            requirements.compliance_requirements
        )
        
        # Estimate costs (placeholder implementation)
        estimated_cost = self._estimate_total_cost(planned_resources)
        
        return InfrastructurePlan(
            resources=planned_resources,
            provider_requirements=provider_requirements,
            variables=variables,
            outputs=outputs,
            compliance_matrix=compliance_matrix,
            estimated_total_cost=estimated_cost
        )
    
    async def _initialize_mcp_context(self, provider: str, state: TerraformState):
        """Initialize MCP context with provider information"""
        try:
            # Get provider documentation
            provider_docs = await self.mcp_integration.get_provider_docs(provider)
            state["provider_docs"][provider] = provider_docs
            
            # Get best practices
            best_practices = await self.mcp_integration.get_best_practices(provider)
            state["mcp_context"]["best_practices"] = best_practices
            
            logger.info("MCP context initialized", 
                       provider=provider,
                       workflow_id=state["workflow_id"])
            
        except Exception as e:
            logger.warning("Failed to initialize MCP context", 
                          provider=provider,
                          error=str(e))
    
    async def _plan_resource(self, 
                           resource_req: Dict[str, Any], 
                           provider: str,
                           environment: str,
                           state: TerraformState) -> ResourcePlan:
        """Plan a specific resource"""
        
        resource_type_hint = resource_req.get("type", "")
        resource_name = resource_req.get("name", f"resource_{len(state.get('analysis_results', {}).get('infrastructure_plan', {}).get('resources', []))}")
        
        # Map resource type hint to actual Terraform resource type
        terraform_resource_type = self._map_resource_type(resource_type_hint, provider)
        
        # Get resource documentation from MCP
        resource_docs = await self.mcp_integration.get_resource_documentation(
            provider, 
            terraform_resource_type
        )
        
        # Build base configuration
        configuration = self._build_resource_configuration(
            resource_req, 
            terraform_resource_type,
            environment,
            resource_docs
        )
        
        # Determine dependencies
        dependencies = self._determine_dependencies(resource_req, terraform_resource_type)
        
        # Map compliance requirements
        compliance_requirements = self._map_compliance_requirements(
            resource_req.get("compliance", []),
            terraform_resource_type
        )
        
        # Estimate cost (placeholder)
        estimated_cost = self._estimate_resource_cost(terraform_resource_type, configuration)
        
        return ResourcePlan(
            resource_type=terraform_resource_type,
            resource_name=resource_name,
            provider=provider,
            configuration=configuration,
            dependencies=dependencies,
            compliance_requirements=compliance_requirements,
            estimated_cost=estimated_cost
        )
    
    def _map_resource_type(self, resource_type_hint: str, provider: str) -> str:
        """Map generic resource type hint to provider-specific Terraform resource type"""
        
        # Get provider mappings
        provider_mappings = self.provider_resource_mappings.get(provider, {})
        
        # Try to find matching resource type
        for category, resource_types in provider_mappings.items():
            if resource_type_hint.lower() in category or any(hint in rt for rt in resource_types for hint in resource_type_hint.lower().split('_')):
                return resource_types[0]  # Return first match
        
        # Fallback: try direct mapping
        if resource_type_hint.startswith(f"{provider}_"):
            return resource_type_hint
        
        # Default fallback
        return f"{provider}_{resource_type_hint}"
    
    def _build_resource_configuration(self, 
                                    resource_req: Dict[str, Any],
                                    terraform_resource_type: str,
                                    environment: str,
                                    resource_docs: Dict[str, Any]) -> Dict[str, Any]:
        """Build resource configuration based on requirements and best practices"""
        
        config = {}
        
        # Add basic configuration from requirements
        for key, value in resource_req.items():
            if key not in ["type", "name", "compliance"]:
                config[key] = value
        
        # Add environment-specific configurations
        config["tags"] = config.get("tags", {})
        config["tags"].update({
            "Environment": environment,
            "ManagedBy": "terraform",
            "CreatedBy": "terraform-agent"
        })
        
        # Apply security best practices based on resource type
        if "s3_bucket" in terraform_resource_type:
            config.update({
                "versioning": {"enabled": True},
                "server_side_encryption_configuration": {
                    "rule": {
                        "apply_server_side_encryption_by_default": {
                            "sse_algorithm": "AES256"
                        }
                    }
                }
            })
        
        elif "security_group" in terraform_resource_type:
            # Ensure no overly permissive rules
            if "ingress" in config:
                for rule in config["ingress"]:
                    if rule.get("cidr_blocks") == ["0.0.0.0/0"] and rule.get("from_port") != 443:
                        rule["cidr_blocks"] = ["10.0.0.0/8"]  # Restrict to private networks
        
        elif "rds" in terraform_resource_type or "database" in terraform_resource_type:
            config.update({
                "encrypted": True,
                "backup_retention_period": 7,
                "multi_az": environment == "prod"
            })
        
        return config
    
    def _determine_dependencies(self, resource_req: Dict[str, Any], terraform_resource_type: str) -> List[str]:
        """Determine resource dependencies"""
        dependencies = []
        
        # Add explicit dependencies from requirements
        if "depends_on" in resource_req:
            dependencies.extend(resource_req["depends_on"])
        
        # Add implicit dependencies based on resource type
        if "instance" in terraform_resource_type:
            dependencies.extend(["security_group", "subnet"])
        elif "rds" in terraform_resource_type:
            dependencies.extend(["subnet_group", "security_group"])
        elif "lb" in terraform_resource_type:
            dependencies.extend(["subnet", "security_group"])
        
        return dependencies
    
    def _map_compliance_requirements(self, compliance_reqs: List[str], resource_type: str) -> List[str]:
        """Map compliance requirements to specific checks for resource type"""
        mapped_requirements = []
        
        for req in compliance_reqs:
            if req.lower() == "security":
                if "s3" in resource_type:
                    mapped_requirements.extend(["encryption", "public_access_block", "versioning"])
                elif "rds" in resource_type:
                    mapped_requirements.extend(["encryption", "backup", "multi_az"])
                elif "security_group" in resource_type:
                    mapped_requirements.extend(["restricted_ingress", "no_ssh_from_internet"])
            
            elif req.lower() == "reliability":
                if "instance" in resource_type:
                    mapped_requirements.extend(["auto_scaling", "health_checks"])
                elif "rds" in resource_type:
                    mapped_requirements.extend(["multi_az", "backup_retention"])
            
            elif req.lower() == "cost_optimization":
                mapped_requirements.extend(["appropriate_sizing", "lifecycle_policies"])
        
        return mapped_requirements
    
    async def _determine_provider_requirements(self, provider: str, resources: List[ResourcePlan]) -> Dict[str, str]:
        """Determine provider version requirements"""
        
        # Get provider versions from MCP
        try:
            versions = await self.mcp_integration.get_provider_versions(provider)
            latest_version = versions[0] if versions else "~> 1.0"
        except:
            latest_version = "~> 1.0"
        
        return {
            provider: {
                "source": f"hashicorp/{provider}",
                "version": latest_version
            }
        }
    
    def _plan_variables(self, requirements: RequirementSpec, resources: List[ResourcePlan]) -> Dict[str, Any]:
        """Plan Terraform variables"""
        variables = {
            "environment": {
                "description": "Environment name (e.g., dev, staging, prod)",
                "type": "string",
                "validation": {
                    "condition": "contains([\"dev\", \"staging\", \"prod\"], var.environment)",
                    "error_message": "Environment must be dev, staging, or prod."
                }
            },
            "project_name": {
                "description": "Name of the project",
                "type": "string"
            }
        }
        
        # Add provider-specific variables
        if requirements.provider == "aws":
            variables["aws_region"] = {
                "description": "AWS region for resources",
                "type": "string",
                "default": "us-west-2",
                "validation": {
                    "condition": "can(regex(\"^[a-z]{2}-[a-z]+-[0-9]$\", var.aws_region))",
                    "error_message": "AWS region must be in valid format."
                }
            }
        
        # Add resource-specific variables
        for resource in resources:
            if "instance" in resource.resource_type:
                variables[f"{resource.resource_name}_instance_type"] = {
                    "description": f"Instance type for {resource.resource_name}",
                    "type": "string",
                    "default": "t3.micro"
                }
        
        return variables
    
    def _plan_outputs(self, resources: List[ResourcePlan]) -> Dict[str, Any]:
        """Plan Terraform outputs"""
        outputs = {}
        
        for resource in resources:
            # Add standard outputs based on resource type
            if "s3_bucket" in resource.resource_type:
                outputs[f"{resource.resource_name}_bucket_name"] = {
                    "description": f"Name of the {resource.resource_name} S3 bucket",
                    "value": f"${{{resource.resource_type}.{resource.resource_name}.bucket}}"
                }
                outputs[f"{resource.resource_name}_bucket_arn"] = {
                    "description": f"ARN of the {resource.resource_name} S3 bucket",
                    "value": f"${{{resource.resource_type}.{resource.resource_name}.arn}}"
                }
            
            elif "instance" in resource.resource_type:
                outputs[f"{resource.resource_name}_instance_id"] = {
                    "description": f"ID of the {resource.resource_name} instance",
                    "value": f"${{{resource.resource_type}.{resource.resource_name}.id}}"
                }
                outputs[f"{resource.resource_name}_public_ip"] = {
                    "description": f"Public IP of the {resource.resource_name} instance",
                    "value": f"${{{resource.resource_type}.{resource.resource_name}.public_ip}}"
                }
            
            elif "rds" in resource.resource_type:
                outputs[f"{resource.resource_name}_endpoint"] = {
                    "description": f"RDS instance endpoint",
                    "value": f"${{{resource.resource_type}.{resource.resource_name}.endpoint}}",
                    "sensitive": True
                }
        
        return outputs
    
    def _create_compliance_matrix(self, resources: List[ResourcePlan], compliance_reqs: List[str]) -> Dict[str, List[str]]:
        """Create compliance matrix mapping requirements to resources"""
        matrix = {}
        
        for req in compliance_reqs:
            matrix[req] = []
            for resource in resources:
                if req in resource.compliance_requirements:
                    matrix[req].append(f"{resource.resource_type}.{resource.resource_name}")
        
        return matrix
    
    def _estimate_resource_cost(self, resource_type: str, configuration: Dict[str, Any]) -> Optional[float]:
        """Estimate resource cost (placeholder implementation)"""
        # This would integrate with cloud provider pricing APIs
        # For now, return placeholder values
        
        cost_estimates = {
            "aws_instance": 50.0,  # per month
            "aws_s3_bucket": 5.0,
            "aws_rds_instance": 100.0,
            "azurerm_virtual_machine": 60.0,
            "google_compute_instance": 55.0
        }
        
        return cost_estimates.get(resource_type, 10.0)
    
    def _estimate_total_cost(self, resources: List[ResourcePlan]) -> Optional[float]:
        """Estimate total infrastructure cost"""
        total = 0.0
        for resource in resources:
            if resource.estimated_cost:
                total += resource.estimated_cost
        return total if total > 0 else None
    
    def _generate_planning_summary(self, plan: InfrastructurePlan) -> str:
        """Generate human-readable planning summary"""
        
        summary_lines = [
            f"🏗️ Infrastructure Planning Complete",
            f"",
            f"📊 Plan Summary:",
            f"   • Resources planned: {len(plan.resources)}",
            f"   • Provider requirements: {len(plan.provider_requirements)}",
            f"   • Variables defined: {len(plan.variables)}",
            f"   • Outputs planned: {len(plan.outputs)}",
        ]
        
        if plan.estimated_total_cost:
            summary_lines.append(f"   • Estimated monthly cost: ${plan.estimated_total_cost:.2f}")
        
        summary_lines.extend([
            f"",
            f"🔧 Resources to be created:"
        ])
        
        for resource in plan.resources:
            summary_lines.append(f"   • {resource.resource_type}.{resource.resource_name}")
            if resource.estimated_cost:
                summary_lines.append(f"     Cost: ${resource.estimated_cost:.2f}/month")
        
        if plan.compliance_matrix:
            summary_lines.extend([
                f"",
                f"✅ Compliance Requirements:"
            ])
            for req, resources in plan.compliance_matrix.items():
                summary_lines.append(f"   • {req}: {len(resources)} resources")
        
        return "\n".join(summary_lines) 