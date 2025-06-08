"""
Terraform Code Generation Agent - Main Entry Point
LangGraph Platform compatible agent implementation
"""

from typing import Literal, Dict, Any, List
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END

# Import our agent components
from utils.state import TerraformState
from utils.nodes import (
    planner_node,
    generator_node,
    validator_node,
    validation_processor_node,
    refiner_node,
    reviewer_node,
    analyzer_node,
    should_continue_validation,
    should_continue_after_analysis
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
workflow.add_node("validation_processor", validation_processor_node)
workflow.add_node("refiner", refiner_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("analyzer", analyzer_node)

# Define the workflow edges
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "generator")
workflow.add_edge("generator", "validator")

# Connect validator to validation processor
workflow.add_edge("validator", "validation_processor")

# Conditional edges for validation results (after validation tools run)
workflow.add_conditional_edges(
    "validation_processor",
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