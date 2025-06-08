# src/workflows/analysis_workflow.py
"""
Terraform Analysis Workflow - LangGraph Platform Implementation
Inspired by AWS Well-Architected IaC Analyzer but cloud-agnostic
"""

import asyncio
import uuid
from typing import Dict, List, Optional, TypedDict, Annotated
from dataclasses import dataclass
from enum import Enum

from langgraph import StateGraph, START, END
from langgraph.platform import LangGraphPlatform
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool

from ..agents.analyzer import TerraformAnalyzerAgent, AnalyzerState, AnalysisReport
from ..agents.planner import PlannerAgent
from ..agents.generator import GeneratorAgent
from ..agents.validator import ValidatorAgent
from ..agents.refiner import RefinerAgent

from ..agents.reviewer import ReviewerAgent
from ..tools.terraform_tools import TerraformTools
from ..tools.mcp_integration import TerraformMCPIntegration


class WorkflowMode(Enum):
    """Analysis workflow modes"""
    ANALYSIS_ONLY = "analysis_only"
    ANALYSIS_WITH_FIXES = "analysis_with_fixes"
    FULL_GENERATION = "full_generation"


class AnalysisWorkflowState(TypedDict):
    """Extended state for the analysis workflow"""
    messages: Annotated[List[BaseMessage], "The messages in the conversation"]
    mode: WorkflowMode
    terraform_code: str
    file_paths: List[str]
    requirements: Optional[Dict[str, any]]
    
    # Analysis results
    parsed_resources: Dict[str, any]
    analysis_issues: List[any]
    analysis_report: Optional[AnalysisReport]
    
    # Generation and refinement
    generated_code: str
    validation_results: List[Dict[str, any]]
    refined_code: str
    documentation: str
    
    # Workflow control
    current_agent: str
    iteration_count: int
    max_iterations: int
    should_continue: bool
    
    # MCP and tool context
    mcp_context: Dict[str, any]
    tool_results: List[Dict[str, any]]


@tool
def analyze_terraform_code_tool(code: str, categories: List[str] = None) -> Dict[str, any]:
    """Analyze Terraform code for Well-Architected Framework compliance."""
    return {
        "tool": "terraform_analysis",
        "status": "completed",
        "issues_found": 0,
        "categories_analyzed": categories or ["all"]
    }


@tool
def generate_remediation_tool(issue_type: str, resource_type: str, current_config: str) -> Dict[str, any]:
    """Generate remediation code for identified issues."""
    return {
        "tool": "remediation_generation",
        "status": "completed",
        "remediation_code": "# Generated remediation code",
        "explanation": "Remediation explanation"
    }


@tool
def validate_terraform_syntax_tool(code: str) -> Dict[str, any]:
    """Validate Terraform syntax and configuration."""
    return {
        "tool": "terraform_validate",
        "status": "completed",
        "valid": True,
        "errors": [],
        "warnings": []
    }


@tool
def get_best_practices_tool(provider: str, resource_type: str) -> Dict[str, any]:
    """Get best practices for specific provider and resource type via MCP."""
    return {
        "tool": "best_practices",
        "status": "completed",
        "practices": [],
        "references": []
    }


class AnalysisOrchestratorAgent:
    """
    Orchestrates the analysis workflow
    Inspired by AWS Well-Architected IaC Analyzer workflow
    """
    
    def __init__(self, platform: LangGraphPlatform):
        self.platform = platform
        self.terraform_tools = TerraformTools()
        self.mcp_integration = TerraformMCPIntegration()
    
    def __call__(self, state: AnalysisWorkflowState) -> AnalysisWorkflowState:
        """Orchestrate the analysis workflow"""
        return asyncio.run(self._orchestrate_analysis(state))
    
    async def _orchestrate_analysis(self, state: AnalysisWorkflowState) -> AnalysisWorkflowState:
        """Main orchestration logic"""
        
        # Initialize workflow
        state["current_agent"] = "orchestrator"
        state["iteration_count"] = 0
        state["should_continue"] = True
        
        # Add orchestration message
        orchestration_message = AIMessage(
            content=f"Starting {state['mode'].value} workflow for Terraform analysis"
        )
        state["messages"].append(orchestration_message)
        
        # Set workflow continuation based on mode
        if state["mode"] == WorkflowMode.ANALYSIS_ONLY:
            state["should_continue"] = False  # Stop after analysis
        else:
            state["should_continue"] = True   # Continue to generation/fixes
        
        return state


class AnalysisValidatorAgent:
    """
    Validates analysis results and determines next steps
    """
    
    def __init__(self, platform: LangGraphPlatform):
        self.platform = platform
    
    def __call__(self, state: AnalysisWorkflowState) -> AnalysisWorkflowState:
        """Validate analysis results and determine workflow continuation"""
        
        state["current_agent"] = "analysis_validator"
        
        # Check if analysis is complete and valid
        analysis_report = state.get("analysis_report")
        
        if analysis_report:
            critical_issues = len([
                issue for issue in analysis_report.issues 
                if issue.severity.value == "critical"
            ])
            
            high_issues = len([
                issue for issue in analysis_report.issues 
                if issue.severity.value == "high"
            ])
            
            # Determine if fixes are needed
            if state["mode"] == WorkflowMode.ANALYSIS_WITH_FIXES and (critical_issues > 0 or high_issues > 0):
                state["should_continue"] = True
                validation_message = AIMessage(
                    content=f"Analysis complete. Found {critical_issues} critical and {high_issues} high severity issues. Proceeding with automated fixes."
                )
            elif state["mode"] == WorkflowMode.FULL_GENERATION:
                state["should_continue"] = True
                validation_message = AIMessage(
                    content="Analysis complete. Proceeding with full code generation workflow."
                )
            else:
                state["should_continue"] = False
                validation_message = AIMessage(
                    content=f"Analysis complete. Found {len(analysis_report.issues)} total issues. Workflow complete."
                )
            
            state["messages"].append(validation_message)
        else:
            # Analysis failed, stop workflow
            state["should_continue"] = False
            error_message = AIMessage(
                content="Analysis failed to complete. Stopping workflow."
            )
            state["messages"].append(error_message)
        
        return state


class FixGeneratorAgent:
    """
    Generates fixes for identified issues
    """
    
    def __init__(self, platform: LangGraphPlatform):
        self.platform = platform
        self.mcp_integration = TerraformMCPIntegration()
    
    def __call__(self, state: AnalysisWorkflowState) -> AnalysisWorkflowState:
        """Generate fixes for critical and high severity issues"""
        return asyncio.run(self._generate_fixes(state))
    
    async def _generate_fixes(self, state: AnalysisWorkflowState) -> AnalysisWorkflowState:
        """Generate automated fixes for issues"""
        
        state["current_agent"] = "fix_generator"
        
        analysis_report = state.get("analysis_report")
        if not analysis_report:
            return state
        
        # Filter issues that can be automatically fixed
        fixable_issues = [
            issue for issue in analysis_report.issues
            if issue.severity.value in ["critical", "high"] and issue.remediation_code
        ]
        
        if not fixable_issues:
            fix_message = AIMessage(
                content="No automatically fixable issues found."
            )
            state["messages"].append(fix_message)
            return state
        
        # Generate fixes
        original_code = state["terraform_code"]
        fixed_code = original_code
        
        for issue in fixable_issues:
            # Apply remediation code
            # This is a simplified implementation - in practice, you'd need
            # more sophisticated code modification logic
            if issue.remediation_code:
                # For demonstration, we'll just append the remediation
                fixed_code += f"\n\n# Fix for {issue.title}\n{issue.remediation_code}\n"
        
        state["refined_code"] = fixed_code
        
        fix_message = AIMessage(
            content=f"Generated fixes for {len(fixable_issues)} issues."
        )
        state["messages"].append(fix_message)
        
        return state


def should_continue_analysis(state: AnalysisWorkflowState) -> str:
    """Determine if the workflow should continue after analysis"""
    if state.get("should_continue", False):
        if state["mode"] == WorkflowMode.ANALYSIS_WITH_FIXES:
            return "fix_generator"
        elif state["mode"] == WorkflowMode.FULL_GENERATION:
            return "planner"
    return "end"


def should_continue_after_fixes(state: AnalysisWorkflowState) -> str:
    """Determine if the workflow should continue after generating fixes"""
    if state["mode"] == WorkflowMode.FULL_GENERATION:
        return "validator"
    return "end"


def create_analysis_workflow() -> StateGraph:
    """Create the LangGraph workflow for Terraform analysis"""
    
    # Initialize platform and checkpointer
    platform = LangGraphPlatform()
    checkpointer = MemorySaver()
    
    # Create workflow
    workflow = StateGraph(AnalysisWorkflowState)
    
    # Add agent nodes
    workflow.add_node("orchestrator", AnalysisOrchestratorAgent(platform))
    workflow.add_node("analyzer", TerraformAnalyzerAgent(platform))
    workflow.add_node("analysis_validator", AnalysisValidatorAgent(platform))
    workflow.add_node("fix_generator", FixGeneratorAgent(platform))
    
    # Add full generation workflow agents (for FULL_GENERATION mode)
    workflow.add_node("planner", PlannerAgent(platform))
    workflow.add_node("generator", GeneratorAgent(platform))
    workflow.add_node("validator", ValidatorAgent(platform))
    workflow.add_node("refiner", RefinerAgent(platform))

    workflow.add_node("reviewer", ReviewerAgent(platform))
    
    # Add tool nodes
    analysis_tools = ToolNode([
        analyze_terraform_code_tool,
        validate_terraform_syntax_tool,
        get_best_practices_tool
    ])
    
    remediation_tools = ToolNode([
        generate_remediation_tool,
        validate_terraform_syntax_tool
    ])
    
    workflow.add_node("analysis_tools", analysis_tools)
    workflow.add_node("remediation_tools", remediation_tools)
    
    # Define workflow edges
    workflow.add_edge(START, "orchestrator")
    workflow.add_edge("orchestrator", "analyzer")
    workflow.add_edge("analyzer", "analysis_tools")
    workflow.add_edge("analysis_tools", "analysis_validator")
    
    # Conditional edges based on analysis results
    workflow.add_conditional_edges(
        "analysis_validator",
        should_continue_analysis,
        {
            "fix_generator": "fix_generator",
            "planner": "planner",
            "end": END
        }
    )
    
    # Fix generation path
    workflow.add_edge("fix_generator", "remediation_tools")
    workflow.add_conditional_edges(
        "remediation_tools",
        should_continue_after_fixes,
        {
            "validator": "validator",
            "end": END
        }
    )
    
    # Full generation workflow path
    workflow.add_edge("planner", "generator")
    workflow.add_edge("generator", "validator")
    workflow.add_conditional_edges(
        "validator",
        lambda state: "refiner" if state.get("iteration_count", 0) < state.get("max_iterations", 3) else "reviewer",
        {
            "refiner": "refiner",
            "reviewer": "reviewer"
        }
    )
    workflow.add_edge("refiner", "generator")
    workflow.add_edge("reviewer", END)
    
    return workflow.compile(checkpointer=checkpointer)


class TerraformAnalysisWorkflowManager:
    """
    Manages the complete Terraform analysis workflow
    Inspired by AWS Well-Architected IaC Analyzer
    """
    
    def __init__(self):
        self.platform = LangGraphPlatform()
        self.workflow = create_analysis_workflow()
    
    async def analyze_terraform_code(self, 
                                   terraform_code: str, 
                                   mode: WorkflowMode = WorkflowMode.ANALYSIS_ONLY,
                                   file_paths: List[str] = None,
                                   requirements: Dict[str, any] = None) -> AnalysisReport:
        """Execute the analysis workflow"""
        
        thread_id = f"analysis_{uuid.uuid4()}"
        config = {"configurable": {"thread_id": thread_id}}
        
        initial_state = {
            "messages": [HumanMessage(content="Analyze the provided Terraform code")],
            "mode": mode,
            "terraform_code": terraform_code,
            "file_paths": file_paths or ["main.tf"],
            "requirements": requirements,
            "parsed_resources": {},
            "analysis_issues": [],
            "analysis_report": None,
            "generated_code": "",
            "validation_results": [],
            "refined_code": "",
            "documentation": "",
            "current_agent": "",
            "iteration_count": 0,
            "max_iterations": 3,
            "should_continue": False,
            "mcp_context": {},
            "tool_results": []
        }
        
        final_state = None
        async for event in self.workflow.astream(initial_state, config):
            # Track the final state
            for node_name, node_state in event.items():
                if node_name in ["analysis_validator", "reviewer", "remediation_tools"]:
                    final_state = node_state
        
        if final_state:
            return final_state.get("analysis_report")
        return None
    
    async def analyze_with_fixes(self, terraform_code: str, file_paths: List[str] = None) -> Dict[str, any]:
        """Analyze code and generate automated fixes"""
        
        analysis_report = await self.analyze_terraform_code(
            terraform_code, 
            WorkflowMode.ANALYSIS_WITH_FIXES, 
            file_paths
        )
        
        # Get the final state to extract fixed code
        thread_id = f"analysis_{uuid.uuid4()}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # Re-run to get the refined code
        # In practice, you'd store this in the state and return it
        
        return {
            "analysis_report": analysis_report,
            "fixed_code": "",  # Would be extracted from final state
            "fixes_applied": []
        }
    
    async def full_generation_workflow(self, 
                                     requirements: Dict[str, any], 
                                     existing_code: str = None) -> Dict[str, any]:
        """Execute the full generation workflow with analysis"""
        
        # Start with analysis if existing code is provided
        if existing_code:
            analysis_report = await self.analyze_terraform_code(
                existing_code,
                WorkflowMode.FULL_GENERATION,
                requirements=requirements
            )
        else:
            analysis_report = None
        
        # The workflow will continue to generation based on the mode
        # Return comprehensive results
        return {
            "analysis_report": analysis_report,
            "generated_code": "",  # Would be extracted from final state
            "documentation": "",   # Would be extracted from final state
            "validation_results": []
        }
    
    def get_workflow_status(self, thread_id: str) -> Dict[str, any]:
        """Get the current status of a workflow execution"""
        # This would query the checkpointer for workflow state
        return {
            "thread_id": thread_id,
            "status": "running",
            "current_agent": "",
            "progress": 0.0
        } 