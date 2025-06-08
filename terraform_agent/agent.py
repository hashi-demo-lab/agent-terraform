"""
Terraform Code Generation Agent - Main Entry Point
LangGraph Platform compatible agent implementation
"""

from typing import Literal, Dict, Any, List
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

# Import our agent components
from utils.state import TerraformState
from utils.nodes import (
    planner_node,
    generator_node,
    validator_node,
    refiner_node,

    reviewer_node,
    analyzer_node,
    should_continue_validation,
    should_continue_after_analysis
)
from utils.tools import (
    terraform_validate_tool,
    terraform_fmt_tool,
    terraform_test_tool,
    tflint_avm_validate_tool,
    trivy_scan_tool
)


# Define the config schema for the graph
class GraphConfig(TypedDict):
    """Configuration schema for the Terraform agent graph"""
    provider: Literal["aws", "azure", "gcp"]
    environment: Literal["dev", "staging", "prod"]
    max_iterations: int
    enable_security_scan: bool
    enable_compliance_check: bool


# Create the workflow graph
workflow = StateGraph(TerraformState, config_schema=GraphConfig)

# Add agent nodes
workflow.add_node("planner", planner_node)
workflow.add_node("generator", generator_node)
workflow.add_node("validator", validator_node)
workflow.add_node("refiner", refiner_node)

workflow.add_node("reviewer", reviewer_node)
workflow.add_node("analyzer", analyzer_node)

# Add tool nodes for validation
validation_tools = [
    terraform_validate_tool,
    terraform_fmt_tool,
    terraform_test_tool,
    tflint_avm_validate_tool,
    trivy_scan_tool
]
workflow.add_node("validation_tools", ToolNode(validation_tools))

# Define the workflow edges
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "generator")
workflow.add_edge("generator", "validator")

# Conditional edges for validation results
workflow.add_conditional_edges(
    "validator",
    should_continue_validation,
    {
        "continue": "refiner",
        "complete": "reviewer",
        "analyze": "analyzer"
    }
)

# Refinement cycle
workflow.add_edge("refiner", "generator")

# Analysis path
workflow.add_conditional_edges(
    "analyzer",
    should_continue_after_analysis,
    {
        "refine": "refiner",
        "complete": "reviewer"
    }
)

# Final review
workflow.add_edge("reviewer", END)

# Compile the graph
graph = workflow.compile() 