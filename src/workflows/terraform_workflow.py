# src/workflows/terraform_workflow.py
"""
Main LangGraph Platform Workflow for Terraform Code Generation Agent
Following .cursorrules specifications
"""

import asyncio
from typing import Dict, Any, Literal
import structlog

from langgraph import StateGraph, START, END
from langgraph.platform import LangGraphPlatform
from langgraph.prebuilt import ToolNode

from .state_management import TerraformState, WorkflowStatus, state_manager, context_manager
from ..platform.langgraph_config import platform_manager
from ..agents.planner import PlannerAgent
from ..agents.generator import GeneratorAgent
from ..agents.validator import ValidatorAgent
from ..agents.refiner import RefinerAgent
from ..agents.documenter import DocumenterAgent
from ..agents.reviewer import ReviewerAgent
from ..agents.analyzer import AnalyzerAgent
from ..tools.terraform_tools import terraform_tool_node
from ..tools.tflint_tools import tflint_tool_node
from ..tools.trivy_tools import trivy_tool_node

logger = structlog.get_logger()


class TerraformWorkflow:
    """
    Main Terraform Code Generation Workflow using LangGraph Platform
    """
    
    def __init__(self):
        self.platform = platform_manager.platform
        self.checkpointer = platform_manager.checkpointer
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create the main Terraform workflow graph"""
        
        # Initialize workflow with state
        workflow = StateGraph(TerraformState)
        
        # Initialize agents with platform
        planner = PlannerAgent(self.platform)
        generator = GeneratorAgent(self.platform)
        validator = ValidatorAgent(self.platform)
        refiner = RefinerAgent(self.platform)
        documenter = DocumenterAgent(self.platform)
        reviewer = ReviewerAgent(self.platform)
        analyzer = AnalyzerAgent(self.platform)
        
        # Add agent nodes
        workflow.add_node("planner", planner)
        workflow.add_node("generator", generator)
        workflow.add_node("validator", validator)
        workflow.add_node("refiner", refiner)
        workflow.add_node("documenter", documenter)
        workflow.add_node("reviewer", reviewer)
        workflow.add_node("analyzer", analyzer)
        
        # Add tool nodes for validation
        workflow.add_node("terraform_tools", terraform_tool_node)
        workflow.add_node("tflint_tools", tflint_tool_node)
        workflow.add_node("trivy_tools", trivy_tool_node)
        
        # Define workflow edges
        workflow.add_edge(START, "planner")
        workflow.add_edge("planner", "generator")
        workflow.add_edge("generator", "validator")
        
        # Conditional edges for validation results
        workflow.add_conditional_edges(
            "validator",
            self._should_continue_validation,
            {
                "continue": "refiner",
                "complete": "documenter",
                "analyze": "analyzer"
            }
        )
        
        # Refinement cycle
        workflow.add_edge("refiner", "generator")
        
        # Analysis path
        workflow.add_conditional_edges(
            "analyzer",
            self._should_continue_after_analysis,
            {
                "refine": "refiner",
                "document": "documenter"
            }
        )
        
        # Documentation and review
        workflow.add_edge("documenter", "reviewer")
        workflow.add_edge("reviewer", END)
        
        # Compile workflow with checkpointer
        return workflow.compile(checkpointer=self.checkpointer)
    
    def _should_continue_validation(self, state: TerraformState) -> Literal["continue", "complete", "analyze"]:
        """Determine next step after validation"""
        
        validation_results = state.get("validation_results", [])
        iteration_count = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 5)
        
        # Check if we've hit max iterations
        if iteration_count >= max_iterations:
            logger.warning("Max iterations reached", 
                          workflow_id=state["workflow_id"],
                          iteration_count=iteration_count)
            return "complete"
        
        # Check validation results
        if not validation_results:
            return "analyze"  # No validation results yet, run analysis
        
        # Check if all validations passed
        all_passed = all(result.passed for result in validation_results)
        
        if all_passed:
            return "complete"
        
        # Check for critical failures that need analysis
        critical_failures = [
            result for result in validation_results 
            if not result.passed and "critical" in str(result.errors).lower()
        ]
        
        if critical_failures:
            return "analyze"
        
        # Continue with refinement
        return "continue"
    
    def _should_continue_after_analysis(self, state: TerraformState) -> Literal["refine", "document"]:
        """Determine next step after analysis"""
        
        analysis_results = state.get("analysis_results", {})
        
        # Check if analysis found issues that need fixing
        issues_found = analysis_results.get("issues_found", [])
        critical_issues = [
            issue for issue in issues_found 
            if issue.get("severity") in ["critical", "high"]
        ]
        
        if critical_issues:
            return "refine"
        
        return "document"
    
    async def execute_workflow(self, 
                             requirements: Dict[str, Any],
                             input_code: str = "",
                             thread_id: str = None) -> Dict[str, Any]:
        """
        Execute the complete Terraform workflow
        
        Args:
            requirements: Infrastructure requirements
            input_code: Optional existing Terraform code to refine
            thread_id: Optional thread ID for state persistence
            
        Returns:
            Dict with workflow results
        """
        
        # Create initial state
        from ..workflows.state_management import RequirementSpec
        
        req_spec = RequirementSpec(
            provider=requirements.get("provider", "aws"),
            resources=requirements.get("resources", []),
            environment=requirements.get("environment", "dev"),
            compliance_requirements=requirements.get("compliance_requirements", []),
            custom_rules=requirements.get("custom_rules", []),
            metadata=requirements.get("metadata", {})
        )
        
        initial_state = state_manager.create_initial_state(
            requirements=req_spec,
            input_code=input_code
        )
        
        # Use provided thread_id or generate one
        if thread_id:
            initial_state["thread_id"] = thread_id
        
        config = {"configurable": {"thread_id": initial_state["thread_id"]}}
        
        logger.info("Starting Terraform workflow execution",
                   workflow_id=initial_state["workflow_id"],
                   thread_id=initial_state["thread_id"],
                   provider=req_spec.provider)
        
        try:
            # Update workflow status
            initial_state["status"] = WorkflowStatus.RUNNING
            
            # Execute workflow
            final_state = None
            async for event in self.workflow.astream(initial_state, config):
                # Log workflow progress
                for node_name, node_state in event.items():
                    if node_name != "__end__":
                        logger.info("Workflow node completed",
                                   workflow_id=initial_state["workflow_id"],
                                   node=node_name,
                                   current_agent=node_state.get("current_agent", "unknown"))
                        
                        # Store intermediate state
                        context_manager.add_conversation_entry(
                            initial_state["workflow_id"],
                            node_name,
                            "node_execution",
                            {"status": "completed", "agent": node_state.get("current_agent")}
                        )
                
                final_state = event
            
            # Extract final state from the last event
            if final_state and "__end__" in final_state:
                final_state = final_state["__end__"]
            elif final_state:
                # Get the last node's state
                final_state = list(final_state.values())[-1]
            else:
                final_state = initial_state
            
            # Mark workflow as completed
            state_manager.complete_workflow(
                initial_state["workflow_id"], 
                WorkflowStatus.COMPLETED
            )
            
            logger.info("Terraform workflow completed successfully",
                       workflow_id=initial_state["workflow_id"],
                       execution_time=final_state.get("execution_metrics", {}).get("total_execution_time", 0))
            
            return self._format_workflow_results(final_state)
            
        except Exception as e:
            logger.error("Terraform workflow failed",
                        workflow_id=initial_state["workflow_id"],
                        error=str(e))
            
            # Mark workflow as failed
            state_manager.complete_workflow(
                initial_state["workflow_id"], 
                WorkflowStatus.FAILED
            )
            
            return {
                "success": False,
                "error": str(e),
                "workflow_id": initial_state["workflow_id"],
                "thread_id": initial_state["thread_id"]
            }
    
    def _format_workflow_results(self, final_state: TerraformState) -> Dict[str, Any]:
        """Format workflow results for return"""
        
        # Get generated module from context
        generated_module = context_manager.retrieve_context(
            final_state["workflow_id"],
            "generated_module"
        )
        
        # Get infrastructure plan from context
        infrastructure_plan = context_manager.retrieve_context(
            final_state["workflow_id"],
            "infrastructure_plan"
        )
        
        return {
            "success": True,
            "workflow_id": final_state["workflow_id"],
            "thread_id": final_state["thread_id"],
            "status": final_state["status"].value if hasattr(final_state["status"], 'value') else final_state["status"],
            "generated_code": final_state.get("generated_code", ""),
            "refined_code": final_state.get("refined_code", ""),
            "documentation": final_state.get("documentation", ""),
            "validation_results": [
                {
                    "tool": result.tool,
                    "passed": result.passed,
                    "status": result.status.value if hasattr(result.status, 'value') else result.status,
                    "messages": result.messages,
                    "errors": result.errors,
                    "warnings": getattr(result, 'warnings', []),
                    "execution_time": result.execution_time
                }
                for result in final_state.get("validation_results", [])
            ],
            "analysis_results": final_state.get("analysis_results", {}),
            "execution_metrics": final_state.get("execution_metrics", {}),
            "errors": final_state.get("errors", []),
            "warnings": final_state.get("warnings", []),
            "generated_module": generated_module.__dict__ if generated_module else None,
            "infrastructure_plan": infrastructure_plan.__dict__ if infrastructure_plan else None
        }
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current workflow status"""
        
        state = state_manager.get_state(workflow_id)
        if not state:
            return {"error": "Workflow not found"}
        
        return {
            "workflow_id": workflow_id,
            "status": state["status"].value if hasattr(state["status"], 'value') else state["status"],
            "current_agent": state.get("current_agent", ""),
            "iteration_count": state.get("iteration_count", 0),
            "errors": state.get("errors", []),
            "warnings": state.get("warnings", [])
        }
    
    async def cancel_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Cancel a running workflow"""
        
        state = state_manager.get_state(workflow_id)
        if not state:
            return {"error": "Workflow not found"}
        
        # Mark as cancelled
        state_manager.complete_workflow(workflow_id, WorkflowStatus.CANCELLED)
        
        logger.info("Workflow cancelled", workflow_id=workflow_id)
        
        return {
            "workflow_id": workflow_id,
            "status": "cancelled",
            "message": "Workflow has been cancelled"
        }


# Global workflow instance
terraform_workflow = TerraformWorkflow() 