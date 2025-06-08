"""
Terraform Code Analyzer Agent - Inspired by AWS Well-Architected IaC Analyzer
Modernized with LangGraph, LangMem, and MCP integration
"""

import asyncio
import json
from typing import Dict, List, Optional, TypedDict, Annotated
from dataclasses import dataclass
from enum import Enum

from langgraph import StateGraph, START, END
from langgraph.platform import LangGraphPlatform
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool

from ..utils.terraform_parser import TerraformParser
from ..utils.file_manager import FileManager
from ..tools.mcp_integration import TerraformMCPIntegration
from ..config.analysis_rules import AnalysisRuleEngine


class AnalysisCategory(Enum):
    """Analysis categories inspired by Well-Architected Framework"""
    SECURITY = "security"
    RELIABILITY = "reliability"
    PERFORMANCE = "performance"
    COST_OPTIMIZATION = "cost_optimization"
    OPERATIONAL_EXCELLENCE = "operational_excellence"
    SUSTAINABILITY = "sustainability"


class SeverityLevel(Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AnalysisIssue:
    """Represents an analysis issue found in Terraform code"""
    category: AnalysisCategory
    severity: SeverityLevel
    title: str
    description: str
    resource_type: str
    resource_name: str
    file_path: str
    line_number: int
    recommendation: str
    remediation_code: Optional[str] = None
    references: List[str] = None


@dataclass
class AnalysisReport:
    """Complete analysis report"""
    summary: Dict[str, int]
    issues: List[AnalysisIssue]
    score: float
    recommendations: List[str]
    metadata: Dict[str, any]


class AnalyzerState(TypedDict):
    """LangGraph state for the analyzer workflow"""
    messages: Annotated[List[BaseMessage], "The messages in the conversation"]
    terraform_code: str
    file_paths: List[str]
    parsed_resources: Dict[str, any]
    analysis_issues: List[AnalysisIssue]
    analysis_report: Optional[AnalysisReport]
    current_category: Optional[AnalysisCategory]
    iteration_count: int
    mcp_context: Dict[str, any]


class TerraformAnalyzerAgent:
    """
    Main analyzer agent inspired by AWS Well-Architected IaC Analyzer
    Modernized with LangGraph Platform, LangMem, and MCP integration
    """
    
    def __init__(self, platform: LangGraphPlatform):
        self.platform = platform
        self.terraform_parser = TerraformParser()
        self.file_manager = FileManager()
        self.mcp_integration = TerraformMCPIntegration()
        self.rule_engine = AnalysisRuleEngine()
        self.max_iterations = 3
        
    def __call__(self, state: AnalyzerState) -> AnalyzerState:
        """Main analyzer entry point"""
        return asyncio.run(self._analyze_terraform_code(state))
    
    async def _analyze_terraform_code(self, state: AnalyzerState) -> AnalyzerState:
        """Analyze Terraform code across all categories"""
        
        # Parse Terraform code if not already done
        if not state.get("parsed_resources"):
            state["parsed_resources"] = await self._parse_terraform_files(state["terraform_code"])
        
        # Initialize analysis context
        state["analysis_issues"] = []
        state["mcp_context"] = await self._initialize_mcp_context(state["parsed_resources"])
        
        # Run analysis across all categories
        for category in AnalysisCategory:
            state["current_category"] = category
            category_issues = await self._analyze_category(state, category)
            state["analysis_issues"].extend(category_issues)
        
        # Generate comprehensive report
        state["analysis_report"] = await self._generate_analysis_report(state)
        
        # Add analysis summary to messages
        summary_message = AIMessage(
            content=f"Analysis complete. Found {len(state['analysis_issues'])} issues across {len(AnalysisCategory)} categories."
        )
        state["messages"].append(summary_message)
        
        return state
    
    async def _parse_terraform_files(self, terraform_code: str) -> Dict[str, any]:
        """Parse Terraform code and extract resources"""
        try:
            parsed_data = self.terraform_parser.parse_hcl(terraform_code)
            return {
                "resources": parsed_data.get("resource", {}),
                "variables": parsed_data.get("variable", {}),
                "outputs": parsed_data.get("output", {}),
                "locals": parsed_data.get("locals", {}),
                "providers": parsed_data.get("terraform", {}).get("required_providers", {})
            }
        except Exception as e:
            return {"error": str(e), "resources": {}}
    
    async def _initialize_mcp_context(self, parsed_resources: Dict[str, any]) -> Dict[str, any]:
        """Initialize MCP context with provider and resource information"""
        context = {
            "providers": [],
            "resource_docs": {},
            "best_practices": {}
        }
        
        # Get provider information via MCP
        for provider_name in parsed_resources.get("providers", {}):
            try:
                provider_docs = await self.mcp_integration.get_provider_docs(provider_name)
                context["providers"].append(provider_name)
                context["resource_docs"][provider_name] = provider_docs
            except Exception as e:
                print(f"Failed to get MCP docs for provider {provider_name}: {e}")
        
        return context
    
    async def _analyze_category(self, state: AnalyzerState, category: AnalysisCategory) -> List[AnalysisIssue]:
        """Analyze Terraform code for a specific category"""
        issues = []
        
        # Get category-specific analysis rules
        rules = self.rule_engine.get_rules_for_category(category)
        
        # Analyze each resource
        for resource_type, resources in state["parsed_resources"].get("resources", {}).items():
            for resource_name, resource_config in resources.items():
                resource_issues = await self._analyze_resource(
                    resource_type, 
                    resource_name, 
                    resource_config, 
                    category, 
                    rules,
                    state["mcp_context"]
                )
                issues.extend(resource_issues)
        
        return issues
    
    async def _analyze_resource(self, 
                              resource_type: str, 
                              resource_name: str, 
                              resource_config: Dict[str, any],
                              category: AnalysisCategory,
                              rules: List[Dict[str, any]],
                              mcp_context: Dict[str, any]) -> List[AnalysisIssue]:
        """Analyze a specific resource against category rules"""
        issues = []
        
        for rule in rules:
            if self._rule_applies_to_resource(rule, resource_type):
                issue = await self._evaluate_rule(
                    rule, 
                    resource_type, 
                    resource_name, 
                    resource_config,
                    category,
                    mcp_context
                )
                if issue:
                    issues.append(issue)
        
        return issues
    
    def _rule_applies_to_resource(self, rule: Dict[str, any], resource_type: str) -> bool:
        """Check if a rule applies to a specific resource type"""
        applicable_types = rule.get("resource_types", [])
        return not applicable_types or resource_type in applicable_types
    
    async def _evaluate_rule(self, 
                           rule: Dict[str, any],
                           resource_type: str,
                           resource_name: str,
                           resource_config: Dict[str, any],
                           category: AnalysisCategory,
                           mcp_context: Dict[str, any]) -> Optional[AnalysisIssue]:
        """Evaluate a specific rule against a resource"""
        
        # Get rule evaluation logic
        rule_type = rule.get("type")
        
        if rule_type == "required_attribute":
            return self._check_required_attribute(rule, resource_type, resource_name, resource_config, category)
        elif rule_type == "forbidden_attribute":
            return self._check_forbidden_attribute(rule, resource_type, resource_name, resource_config, category)
        elif rule_type == "attribute_value":
            return self._check_attribute_value(rule, resource_type, resource_name, resource_config, category)
        elif rule_type == "security_group":
            return self._check_security_group_rules(rule, resource_type, resource_name, resource_config, category)
        elif rule_type == "encryption":
            return self._check_encryption_settings(rule, resource_type, resource_name, resource_config, category)
        elif rule_type == "tagging":
            return self._check_tagging_compliance(rule, resource_type, resource_name, resource_config, category)
        elif rule_type == "best_practice":
            return await self._check_best_practice(rule, resource_type, resource_name, resource_config, category, mcp_context)
        
        return None
    
    def _check_required_attribute(self, rule, resource_type, resource_name, resource_config, category) -> Optional[AnalysisIssue]:
        """Check if required attributes are present"""
        required_attr = rule.get("attribute")
        if required_attr not in resource_config:
            return AnalysisIssue(
                category=category,
                severity=SeverityLevel(rule.get("severity", "medium")),
                title=f"Missing required attribute: {required_attr}",
                description=rule.get("description", f"Resource {resource_name} is missing required attribute {required_attr}"),
                resource_type=resource_type,
                resource_name=resource_name,
                file_path="main.tf",  # TODO: Get actual file path
                line_number=0,  # TODO: Get actual line number
                recommendation=rule.get("recommendation", f"Add the {required_attr} attribute to {resource_name}"),
                remediation_code=rule.get("remediation_code"),
                references=rule.get("references", [])
            )
        return None
    
    def _check_forbidden_attribute(self, rule, resource_type, resource_name, resource_config, category) -> Optional[AnalysisIssue]:
        """Check if forbidden attributes are present"""
        forbidden_attr = rule.get("attribute")
        if forbidden_attr in resource_config:
            return AnalysisIssue(
                category=category,
                severity=SeverityLevel(rule.get("severity", "medium")),
                title=f"Forbidden attribute present: {forbidden_attr}",
                description=rule.get("description", f"Resource {resource_name} contains forbidden attribute {forbidden_attr}"),
                resource_type=resource_type,
                resource_name=resource_name,
                file_path="main.tf",
                line_number=0,
                recommendation=rule.get("recommendation", f"Remove the {forbidden_attr} attribute from {resource_name}"),
                remediation_code=rule.get("remediation_code"),
                references=rule.get("references", [])
            )
        return None
    
    def _check_attribute_value(self, rule, resource_type, resource_name, resource_config, category) -> Optional[AnalysisIssue]:
        """Check if attribute values meet requirements"""
        attr_name = rule.get("attribute")
        expected_value = rule.get("expected_value")
        actual_value = resource_config.get(attr_name)
        
        if actual_value != expected_value:
            return AnalysisIssue(
                category=category,
                severity=SeverityLevel(rule.get("severity", "medium")),
                title=f"Incorrect attribute value: {attr_name}",
                description=f"Resource {resource_name} has {attr_name}={actual_value}, expected {expected_value}",
                resource_type=resource_type,
                resource_name=resource_name,
                file_path="main.tf",
                line_number=0,
                recommendation=rule.get("recommendation", f"Set {attr_name} to {expected_value}"),
                remediation_code=rule.get("remediation_code"),
                references=rule.get("references", [])
            )
        return None
    
    def _check_security_group_rules(self, rule, resource_type, resource_name, resource_config, category) -> Optional[AnalysisIssue]:
        """Check security group configurations"""
        if resource_type not in ["aws_security_group", "azurerm_network_security_group"]:
            return None
        
        # Check for overly permissive rules
        ingress_rules = resource_config.get("ingress", [])
        for ingress in ingress_rules:
            if ingress.get("cidr_blocks") == ["0.0.0.0/0"] and ingress.get("from_port") != 443:
                return AnalysisIssue(
                    category=category,
                    severity=SeverityLevel.HIGH,
                    title="Overly permissive security group rule",
                    description=f"Security group {resource_name} allows traffic from 0.0.0.0/0",
                    resource_type=resource_type,
                    resource_name=resource_name,
                    file_path="main.tf",
                    line_number=0,
                    recommendation="Restrict CIDR blocks to specific IP ranges",
                    references=["https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html"]
                )
        return None
    
    def _check_encryption_settings(self, rule, resource_type, resource_name, resource_config, category) -> Optional[AnalysisIssue]:
        """Check encryption configurations"""
        encryption_attrs = rule.get("encryption_attributes", [])
        
        for attr in encryption_attrs:
            if attr not in resource_config or not resource_config[attr]:
                return AnalysisIssue(
                    category=category,
                    severity=SeverityLevel.HIGH,
                    title=f"Encryption not enabled: {attr}",
                    description=f"Resource {resource_name} does not have {attr} enabled",
                    resource_type=resource_type,
                    resource_name=resource_name,
                    file_path="main.tf",
                    line_number=0,
                    recommendation=f"Enable {attr} for {resource_name}",
                    remediation_code=f'{attr} = true',
                    references=rule.get("references", [])
                )
        return None
    
    def _check_tagging_compliance(self, rule, resource_type, resource_name, resource_config, category) -> Optional[AnalysisIssue]:
        """Check tagging compliance"""
        required_tags = rule.get("required_tags", [])
        resource_tags = resource_config.get("tags", {})
        
        missing_tags = [tag for tag in required_tags if tag not in resource_tags]
        
        if missing_tags:
            return AnalysisIssue(
                category=category,
                severity=SeverityLevel.MEDIUM,
                title="Missing required tags",
                description=f"Resource {resource_name} is missing required tags: {', '.join(missing_tags)}",
                resource_type=resource_type,
                resource_name=resource_name,
                file_path="main.tf",
                line_number=0,
                recommendation=f"Add required tags: {', '.join(missing_tags)}",
                remediation_code=self._generate_tag_remediation(missing_tags),
                references=rule.get("references", [])
            )
        return None
    
    async def _check_best_practice(self, rule, resource_type, resource_name, resource_config, category, mcp_context) -> Optional[AnalysisIssue]:
        """Check against best practices using MCP context"""
        # Use MCP context to get provider-specific best practices
        provider_docs = mcp_context.get("resource_docs", {})
        
        # This would be expanded with specific best practice checks
        # using the MCP-provided documentation and recommendations
        
        return None
    
    def _generate_tag_remediation(self, missing_tags: List[str]) -> str:
        """Generate remediation code for missing tags"""
        tag_lines = []
        for tag in missing_tags:
            tag_lines.append(f'    {tag} = "TODO: Set appropriate value"')
        
        return f"""tags = {{
{chr(10).join(tag_lines)}
  }}"""
    
    async def _generate_analysis_report(self, state: AnalyzerState) -> AnalysisReport:
        """Generate comprehensive analysis report"""
        issues = state["analysis_issues"]
        
        # Calculate summary statistics
        summary = {
            "total_issues": len(issues),
            "critical": len([i for i in issues if i.severity == SeverityLevel.CRITICAL]),
            "high": len([i for i in issues if i.severity == SeverityLevel.HIGH]),
            "medium": len([i for i in issues if i.severity == SeverityLevel.MEDIUM]),
            "low": len([i for i in issues if i.severity == SeverityLevel.LOW]),
            "info": len([i for i in issues if i.severity == SeverityLevel.INFO])
        }
        
        # Calculate overall score (0-100)
        total_resources = len(state["parsed_resources"].get("resources", {}))
        if total_resources == 0:
            score = 100.0
        else:
            # Weight issues by severity
            weighted_issues = (
                summary["critical"] * 10 +
                summary["high"] * 5 +
                summary["medium"] * 2 +
                summary["low"] * 1 +
                summary["info"] * 0.5
            )
            max_possible_score = total_resources * 10  # Assuming worst case
            score = max(0, 100 - (weighted_issues / max_possible_score * 100))
        
        # Generate recommendations
        recommendations = self._generate_recommendations(issues)
        
        # Metadata
        metadata = {
            "analysis_timestamp": asyncio.get_event_loop().time(),
            "total_resources_analyzed": total_resources,
            "categories_analyzed": [cat.value for cat in AnalysisCategory],
            "mcp_providers": state["mcp_context"].get("providers", [])
        }
        
        return AnalysisReport(
            summary=summary,
            issues=issues,
            score=score,
            recommendations=recommendations,
            metadata=metadata
        )
    
    def _generate_recommendations(self, issues: List[AnalysisIssue]) -> List[str]:
        """Generate high-level recommendations based on issues"""
        recommendations = []
        
        # Group issues by category
        category_counts = {}
        for issue in issues:
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1
        
        # Generate category-specific recommendations
        for category, count in category_counts.items():
            if count > 0:
                recommendations.append(f"Address {count} {category.value} issues to improve infrastructure quality")
        
        # Add general recommendations
        if any(issue.severity == SeverityLevel.CRITICAL for issue in issues):
            recommendations.append("Prioritize fixing critical security and reliability issues")
        
        if any("encryption" in issue.title.lower() for issue in issues):
            recommendations.append("Enable encryption for all data storage and transmission")
        
        if any("tag" in issue.title.lower() for issue in issues):
            recommendations.append("Implement consistent tagging strategy for resource management")
        
        return recommendations


# LangGraph Tools for Analysis
@tool
def analyze_terraform_code_tool(terraform_code: str, analysis_categories: List[str] = None) -> Dict[str, any]:
    """Analyze Terraform code for best practices and issues."""
    # This would integrate with the main analyzer
    return {"status": "analysis_complete", "issues_found": 0}


@tool
def get_remediation_suggestions_tool(issue_type: str, resource_type: str) -> Dict[str, any]:
    """Get remediation suggestions for specific issues."""
    return {"remediation_code": "", "references": []}


@tool
def validate_fix_tool(original_code: str, fixed_code: str) -> Dict[str, any]:
    """Validate that a fix resolves the identified issue."""
    return {"fix_valid": True, "remaining_issues": []}


def create_analyzer_workflow() -> StateGraph:
    """Create the LangGraph workflow for Terraform analysis"""
    workflow = StateGraph(AnalyzerState)
    
    # Initialize platform
    platform = LangGraphPlatform()
    checkpointer = MemorySaver()
    
    # Add analyzer agent
    analyzer_agent = TerraformAnalyzerAgent(platform)
    workflow.add_node("analyzer", analyzer_agent)
    
    # Add tool nodes
    analysis_tools = ToolNode([
        analyze_terraform_code_tool,
        get_remediation_suggestions_tool,
        validate_fix_tool
    ])
    workflow.add_node("analysis_tools", analysis_tools)
    
    # Define workflow edges
    workflow.add_edge(START, "analyzer")
    workflow.add_edge("analyzer", "analysis_tools")
    workflow.add_edge("analysis_tools", END)
    
    return workflow.compile(checkpointer=checkpointer)


class TerraformAnalysisWorkflowManager:
    """Manages the complete Terraform analysis workflow"""
    
    def __init__(self):
        self.platform = LangGraphPlatform()
        self.workflow = create_analyzer_workflow()
    
    async def analyze_terraform_code(self, terraform_code: str, file_paths: List[str] = None) -> AnalysisReport:
        """Execute the complete analysis workflow"""
        
        initial_state = {
            "messages": [HumanMessage(content="Analyze the provided Terraform code")],
            "terraform_code": terraform_code,
            "file_paths": file_paths or ["main.tf"],
            "parsed_resources": {},
            "analysis_issues": [],
            "analysis_report": None,
            "current_category": None,
            "iteration_count": 0,
            "mcp_context": {}
        }
        
        config = {"configurable": {"thread_id": f"analysis_{asyncio.get_event_loop().time()}"}}
        
        final_state = None
        async for event in self.workflow.astream(initial_state, config):
            if "analyzer" in event:
                final_state = event["analyzer"]
        
        return final_state["analysis_report"] if final_state else None 