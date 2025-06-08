"""
MCP Integration for Terraform Registry Access
Provides cloud-agnostic access to provider documentation and best practices
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

try:
    from mcp_client import MCPClient
except ImportError:
    # Fallback implementation for development
    class MCPClient:
        def __init__(self, server_name: str):
            self.server_name = server_name
        
        async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
            return {"status": "mock_response", "data": {}}


class ProviderType(Enum):
    """Supported cloud providers"""
    AWS = "aws"
    AZURE = "azurerm"
    GCP = "google"
    KUBERNETES = "kubernetes"
    HELM = "helm"
    RANDOM = "random"
    TLS = "tls"


@dataclass
class ProviderResource:
    """Represents a Terraform provider resource"""
    name: str
    provider: str
    description: str
    attributes: Dict[str, Any]
    examples: List[str]
    best_practices: List[str]


@dataclass
class ModuleInfo:
    """Represents a Terraform module from the registry"""
    name: str
    namespace: str
    provider: str
    version: str
    description: str
    source_url: str
    documentation_url: str
    examples: List[Dict[str, Any]]


class TerraformMCPIntegration:
    """
    MCP integration for Terraform Registry access
    Provides cloud-agnostic provider and module information
    """
    
    def __init__(self):
        self.mcp_client = MCPClient("terraform")
        self.cache = {}
        self.supported_providers = [provider.value for provider in ProviderType]
    
    async def get_provider_docs(self, provider_name: str) -> Dict[str, Any]:
        """Get provider documentation via MCP"""
        cache_key = f"provider_docs_{provider_name}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            result = await self.mcp_client.call_tool(
                "resolveProviderDocID",
                {"serviceSlug": provider_name}
            )
            
            if result.get("status") == "success":
                docs = await self.mcp_client.call_tool(
                    "getProviderDocs",
                    {"serviceSlug": provider_name}
                )
                self.cache[cache_key] = docs
                return docs
            
        except Exception as e:
            print(f"Failed to get provider docs for {provider_name}: {e}")
        
        return self._get_fallback_provider_docs(provider_name)
    
    async def get_resource_documentation(self, provider: str, resource_type: str) -> Dict[str, Any]:
        """Get specific resource documentation"""
        cache_key = f"resource_docs_{provider}_{resource_type}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            result = await self.mcp_client.call_tool(
                "getProviderDocs",
                {
                    "serviceSlug": provider,
                    "resourceType": resource_type
                }
            )
            
            if result.get("status") == "success":
                self.cache[cache_key] = result
                return result
                
        except Exception as e:
            print(f"Failed to get resource docs for {provider}.{resource_type}: {e}")
        
        return self._get_fallback_resource_docs(provider, resource_type)
    
    async def search_modules(self, query: str, provider: str = None, limit: int = 10) -> List[ModuleInfo]:
        """Search Terraform Registry for modules"""
        try:
            search_params = {
                "query": query,
                "limit": limit
            }
            
            if provider:
                search_params["provider"] = provider
            
            result = await self.mcp_client.call_tool(
                "searchModules",
                search_params
            )
            
            if result.get("status") == "success":
                modules = []
                for module_data in result.get("modules", []):
                    module = ModuleInfo(
                        name=module_data.get("name", ""),
                        namespace=module_data.get("namespace", ""),
                        provider=module_data.get("provider", ""),
                        version=module_data.get("version", ""),
                        description=module_data.get("description", ""),
                        source_url=module_data.get("source", ""),
                        documentation_url=module_data.get("documentation", ""),
                        examples=module_data.get("examples", [])
                    )
                    modules.append(module)
                return modules
                
        except Exception as e:
            print(f"Failed to search modules: {e}")
        
        return []
    
    async def get_module_details(self, module_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific module"""
        cache_key = f"module_details_{module_id}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            result = await self.mcp_client.call_tool(
                "moduleDetails",
                {"moduleId": module_id}
            )
            
            if result.get("status") == "success":
                self.cache[cache_key] = result
                return result
                
        except Exception as e:
            print(f"Failed to get module details for {module_id}: {e}")
        
        return {}
    
    async def get_best_practices(self, provider: str, resource_type: str = None) -> List[str]:
        """Get best practices for a provider or specific resource type"""
        try:
            # Get provider documentation
            provider_docs = await self.get_provider_docs(provider)
            
            if resource_type:
                resource_docs = await self.get_resource_documentation(provider, resource_type)
                return self._extract_best_practices(resource_docs)
            else:
                return self._extract_provider_best_practices(provider_docs)
                
        except Exception as e:
            print(f"Failed to get best practices for {provider}: {e}")
        
        return self._get_fallback_best_practices(provider, resource_type)
    
    async def get_security_recommendations(self, provider: str, resource_type: str) -> List[Dict[str, Any]]:
        """Get security recommendations for specific resources"""
        try:
            resource_docs = await self.get_resource_documentation(provider, resource_type)
            return self._extract_security_recommendations(resource_docs)
            
        except Exception as e:
            print(f"Failed to get security recommendations for {provider}.{resource_type}: {e}")
        
        return self._get_fallback_security_recommendations(provider, resource_type)
    
    async def validate_resource_configuration(self, provider: str, resource_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate resource configuration against provider specifications"""
        try:
            resource_docs = await self.get_resource_documentation(provider, resource_type)
            
            validation_result = {
                "valid": True,
                "warnings": [],
                "errors": [],
                "suggestions": []
            }
            
            # Extract schema from documentation
            schema = resource_docs.get("schema", {})
            required_attributes = schema.get("required", [])
            optional_attributes = schema.get("optional", [])
            
            # Check required attributes
            for attr in required_attributes:
                if attr not in config:
                    validation_result["errors"].append(f"Missing required attribute: {attr}")
                    validation_result["valid"] = False
            
            # Check for unknown attributes
            all_attributes = required_attributes + optional_attributes
            for attr in config:
                if attr not in all_attributes:
                    validation_result["warnings"].append(f"Unknown attribute: {attr}")
            
            # Add suggestions based on best practices
            best_practices = await self.get_best_practices(provider, resource_type)
            validation_result["suggestions"] = best_practices[:3]  # Top 3 suggestions
            
            return validation_result
            
        except Exception as e:
            print(f"Failed to validate configuration for {provider}.{resource_type}: {e}")
            return {"valid": False, "errors": [str(e)], "warnings": [], "suggestions": []}
    
    def _extract_best_practices(self, resource_docs: Dict[str, Any]) -> List[str]:
        """Extract best practices from resource documentation"""
        best_practices = []
        
        # Look for best practices in various sections
        sections_to_check = ["best_practices", "recommendations", "security", "examples"]
        
        for section in sections_to_check:
            if section in resource_docs:
                section_data = resource_docs[section]
                if isinstance(section_data, list):
                    best_practices.extend(section_data)
                elif isinstance(section_data, str):
                    best_practices.append(section_data)
        
        return best_practices
    
    def _extract_provider_best_practices(self, provider_docs: Dict[str, Any]) -> List[str]:
        """Extract general best practices for a provider"""
        return provider_docs.get("best_practices", [])
    
    def _extract_security_recommendations(self, resource_docs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract security recommendations from resource documentation"""
        security_recommendations = []
        
        security_section = resource_docs.get("security", {})
        if isinstance(security_section, dict):
            for category, recommendations in security_section.items():
                if isinstance(recommendations, list):
                    for rec in recommendations:
                        security_recommendations.append({
                            "category": category,
                            "recommendation": rec,
                            "severity": "medium"  # Default severity
                        })
        
        return security_recommendations
    
    def _get_fallback_provider_docs(self, provider_name: str) -> Dict[str, Any]:
        """Fallback provider documentation when MCP is unavailable"""
        fallback_docs = {
            "aws": {
                "name": "AWS Provider",
                "description": "The Amazon Web Services (AWS) provider for Terraform",
                "version": "~> 5.0",
                "best_practices": [
                    "Use IAM roles instead of access keys",
                    "Enable encryption at rest for all storage",
                    "Use VPC endpoints for AWS services",
                    "Implement least privilege access",
                    "Enable CloudTrail for audit logging"
                ]
            },
            "azurerm": {
                "name": "Azure Provider",
                "description": "The Azure Resource Manager provider for Terraform",
                "version": "~> 3.0",
                "best_practices": [
                    "Use managed identities for authentication",
                    "Enable Azure Security Center",
                    "Use Azure Key Vault for secrets",
                    "Implement network security groups",
                    "Enable diagnostic logging"
                ]
            },
            "google": {
                "name": "Google Cloud Provider",
                "description": "The Google Cloud Platform provider for Terraform",
                "version": "~> 4.0",
                "best_practices": [
                    "Use service accounts for authentication",
                    "Enable Cloud Security Command Center",
                    "Use Cloud KMS for encryption",
                    "Implement VPC firewall rules",
                    "Enable audit logging"
                ]
            }
        }
        
        return fallback_docs.get(provider_name, {
            "name": f"{provider_name.title()} Provider",
            "description": f"Terraform provider for {provider_name}",
            "best_practices": []
        })
    
    def _get_fallback_resource_docs(self, provider: str, resource_type: str) -> Dict[str, Any]:
        """Fallback resource documentation when MCP is unavailable"""
        return {
            "name": resource_type,
            "provider": provider,
            "description": f"Terraform resource {resource_type}",
            "schema": {
                "required": [],
                "optional": []
            },
            "best_practices": [],
            "security": {}
        }
    
    def _get_fallback_best_practices(self, provider: str, resource_type: str = None) -> List[str]:
        """Fallback best practices when MCP is unavailable"""
        general_practices = [
            "Use descriptive resource names",
            "Add appropriate tags for resource management",
            "Enable monitoring and logging",
            "Follow security best practices",
            "Use variables for configurable values"
        ]
        
        provider_specific = {
            "aws": [
                "Use IAM roles for service authentication",
                "Enable encryption at rest and in transit",
                "Use VPC for network isolation",
                "Implement least privilege access"
            ],
            "azurerm": [
                "Use managed identities",
                "Enable Azure Security Center",
                "Use resource groups for organization",
                "Implement network security groups"
            ],
            "google": [
                "Use service accounts",
                "Enable Cloud Security Command Center",
                "Use VPC for network isolation",
                "Implement IAM policies"
            ]
        }
        
        practices = general_practices.copy()
        if provider in provider_specific:
            practices.extend(provider_specific[provider])
        
        return practices
    
    def _get_fallback_security_recommendations(self, provider: str, resource_type: str) -> List[Dict[str, Any]]:
        """Fallback security recommendations when MCP is unavailable"""
        return [
            {
                "category": "encryption",
                "recommendation": "Enable encryption at rest",
                "severity": "high"
            },
            {
                "category": "access_control",
                "recommendation": "Implement least privilege access",
                "severity": "high"
            },
            {
                "category": "monitoring",
                "recommendation": "Enable audit logging",
                "severity": "medium"
            }
        ]
    
    async def get_provider_versions(self, provider: str) -> List[str]:
        """Get available versions for a provider"""
        try:
            result = await self.mcp_client.call_tool(
                "getProviderVersions",
                {"provider": provider}
            )
            
            if result.get("status") == "success":
                return result.get("versions", [])
                
        except Exception as e:
            print(f"Failed to get provider versions for {provider}: {e}")
        
        return ["latest"]
    
    async def get_resource_examples(self, provider: str, resource_type: str) -> List[Dict[str, Any]]:
        """Get usage examples for a specific resource type"""
        try:
            resource_docs = await self.get_resource_documentation(provider, resource_type)
            return resource_docs.get("examples", [])
            
        except Exception as e:
            print(f"Failed to get examples for {provider}.{resource_type}: {e}")
        
        return []
    
    def clear_cache(self) -> None:
        """Clear the MCP response cache"""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.cache),
            "cached_items": list(self.cache.keys())
        } 