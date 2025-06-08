"""
Validator Agent - Multi-tool validation orchestration (LangGraph node)
Following .cursorrules specifications
"""

import asyncio
from typing import Dict, List, Any
import structlog

from langchain_core.messages import BaseMessage, AIMessage
from langgraph.platform import LangGraphPlatform

from ..workflows.state_management import TerraformState, ValidationResult, ValidationStatus, context_manager
from ..tools.terraform_tools import terraform_validate_tool, terraform_fmt_tool, terraform_plan_tool
from ..tools.tflint_tools import tflint_avm_validate_tool
from ..tools.trivy_tools import trivy_scan_tool

logger = structlog.get_logger()


class ValidatorAgent:
    """
    Multi-tool validation orchestration agent
    LangGraph node implementation following .cursorrules
    """
    
    def __init__(self, platform: LangGraphPlatform):
        self.platform = platform
        self.max_iterations = 5
        
        # Define validation tool sequence as per .cursorrules
        self.validation_tools = [
            terraform_validate_tool,
            terraform_fmt_tool,
            terraform_plan_tool,
            tflint_avm_validate_tool,
            trivy_scan_tool
        ]
    
    def __call__(self, state: TerraformState) -> TerraformState:
        """Main validator entry point - LangGraph node implementation"""
        return asyncio.run(self._validate_terraform_code(state))
    
    async def _validate_terraform_code(self, state: TerraformState) -> TerraformState:
        """Orchestrate multi-tool validation pipeline"""
        
        logger.info("Starting validation pipeline", 
                   workflow_id=state["workflow_id"],
                   current_agent="validator")
        
        state["current_agent"] = "validator"
        
        # Get code to validate
        code_to_validate = state.get("generated_code") or state.get("input_code", "")
        
        if not code_to_validate.strip():
            error_msg = "No Terraform code available for validation"
            state["errors"].append(error_msg)
            state["messages"].append(AIMessage(content=f"Validation Error: {error_msg}"))
            return state
        
        try:
            # Run validation pipeline
            validation_results = await self._run_validation_pipeline(code_to_validate, state)
            
            # Store results in state
            state["validation_results"] = validation_results
            
            # Analyze results
            validation_summary = self._analyze_validation_results(validation_results)
            
            # Store summary in context
            context_manager.store_context(
                state["workflow_id"],
                "validation_summary",
                validation_summary
            )
            
            # Generate validation message
            validation_message = self._generate_validation_message(validation_summary)
            state["messages"].append(AIMessage(content=validation_message))
            
            logger.info("Validation pipeline completed",
                       workflow_id=state["workflow_id"],
                       total_tools=len(validation_results),
                       passed_tools=sum(1 for r in validation_results if r.passed))
            
        except Exception as e:
            error_msg = f"Validation pipeline failed: {str(e)}"
            logger.error("Validation pipeline failed", 
                        workflow_id=state["workflow_id"],
                        error=str(e))
            state["errors"].append(error_msg)
            state["messages"].append(AIMessage(content=f"Validation Error: {error_msg}"))
        
        return state
    
    async def _run_validation_pipeline(self, code: str, state: TerraformState) -> List[ValidationResult]:
        """Run the complete validation pipeline"""
        
        validation_results = []
        
        for tool in self.validation_tools:
            try:
                logger.info("Running validation tool", 
                           tool=tool.name,
                           workflow_id=state["workflow_id"])
                
                # Execute tool
                result_dict = tool.invoke({"code": code})
                
                # Convert to ValidationResult
                validation_result = ValidationResult(
                    tool=result_dict["tool"],
                    status=ValidationStatus(result_dict["status"]),
                    passed=result_dict["passed"],
                    messages=result_dict.get("messages", []),
                    errors=result_dict.get("errors", []),
                    warnings=result_dict.get("warnings", []),
                    execution_time=result_dict.get("execution_time", 0.0),
                    metadata=result_dict.get("metadata", {})
                )
                
                validation_results.append(validation_result)
                
                logger.info("Validation tool completed",
                           tool=tool.name,
                           passed=validation_result.passed,
                           execution_time=validation_result.execution_time)
                
                # Store individual result in context
                context_manager.add_conversation_entry(
                    state["workflow_id"],
                    "validator",
                    f"tool_execution_{tool.name}",
                    validation_result.__dict__
                )
                
            except Exception as e:
                logger.error("Validation tool failed",
                            tool=tool.name,
                            error=str(e))
                
                # Create error result
                error_result = ValidationResult(
                    tool=tool.name,
                    status=ValidationStatus.FAILED,
                    passed=False,
                    errors=[f"Tool execution failed: {str(e)}"],
                    execution_time=0.0
                )
                
                validation_results.append(error_result)
        
        return validation_results
    
    def _analyze_validation_results(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Analyze validation results and create summary"""
        
        total_tools = len(results)
        passed_tools = sum(1 for r in results if r.passed)
        failed_tools = total_tools - passed_tools
        
        # Categorize issues by severity
        critical_issues = []
        high_issues = []
        medium_issues = []
        low_issues = []
        
        for result in results:
            if not result.passed:
                for error in result.errors:
                    issue = {
                        "tool": result.tool,
                        "message": error,
                        "type": "error"
                    }
                    
                    # Categorize by keywords
                    error_lower = error.lower()
                    if any(keyword in error_lower for keyword in ["critical", "security", "vulnerability"]):
                        critical_issues.append(issue)
                    elif any(keyword in error_lower for keyword in ["error", "failed", "invalid"]):
                        high_issues.append(issue)
                    else:
                        medium_issues.append(issue)
            
            # Add warnings as low issues
            for warning in result.warnings:
                low_issues.append({
                    "tool": result.tool,
                    "message": warning,
                    "type": "warning"
                })
        
        # Calculate overall score
        score = (passed_tools / total_tools * 100) if total_tools > 0 else 0
        
        # Determine overall status
        if critical_issues:
            overall_status = "critical"
        elif high_issues:
            overall_status = "failed"
        elif medium_issues:
            overall_status = "warning"
        elif passed_tools == total_tools:
            overall_status = "passed"
        else:
            overall_status = "partial"
        
        return {
            "total_tools": total_tools,
            "passed_tools": passed_tools,
            "failed_tools": failed_tools,
            "overall_status": overall_status,
            "score": score,
            "critical_issues": critical_issues,
            "high_issues": high_issues,
            "medium_issues": medium_issues,
            "low_issues": low_issues,
            "total_execution_time": sum(r.execution_time for r in results),
            "tool_results": {r.tool: r.passed for r in results}
        }
    
    def _generate_validation_message(self, summary: Dict[str, Any]) -> str:
        """Generate human-readable validation message"""
        
        status_emoji = {
            "passed": "✅",
            "partial": "⚠️",
            "warning": "⚠️",
            "failed": "❌",
            "critical": "🚨"
        }
        
        emoji = status_emoji.get(summary["overall_status"], "❓")
        
        message_lines = [
            f"{emoji} Validation Pipeline Complete",
            f"",
            f"📊 Validation Summary:",
            f"   • Overall Score: {summary['score']:.1f}/100",
            f"   • Tools Passed: {summary['passed_tools']}/{summary['total_tools']}",
            f"   • Execution Time: {summary['total_execution_time']:.2f}s",
            f"   • Status: {summary['overall_status'].title()}"
        ]
        
        # Add tool breakdown
        if summary["tool_results"]:
            message_lines.extend([
                f"",
                f"🔧 Tool Results:"
            ])
            
            for tool, passed in summary["tool_results"].items():
                tool_emoji = "✅" if passed else "❌"
                message_lines.append(f"   {tool_emoji} {tool}")
        
        # Add issues summary
        if summary["critical_issues"]:
            message_lines.extend([
                f"",
                f"🚨 Critical Issues ({len(summary['critical_issues'])}):"
            ])
            for issue in summary["critical_issues"][:3]:  # Show first 3
                message_lines.append(f"   • {issue['tool']}: {issue['message']}")
            if len(summary["critical_issues"]) > 3:
                message_lines.append(f"   • ... and {len(summary['critical_issues']) - 3} more")
        
        if summary["high_issues"]:
            message_lines.extend([
                f"",
                f"❌ High Priority Issues ({len(summary['high_issues'])}):"
            ])
            for issue in summary["high_issues"][:3]:  # Show first 3
                message_lines.append(f"   • {issue['tool']}: {issue['message']}")
            if len(summary["high_issues"]) > 3:
                message_lines.append(f"   • ... and {len(summary['high_issues']) - 3} more")
        
        if summary["medium_issues"]:
            message_lines.extend([
                f"",
                f"⚠️ Medium Priority Issues ({len(summary['medium_issues'])}):"
            ])
            for issue in summary["medium_issues"][:2]:  # Show first 2
                message_lines.append(f"   • {issue['tool']}: {issue['message']}")
            if len(summary["medium_issues"]) > 2:
                message_lines.append(f"   • ... and {len(summary['medium_issues']) - 2} more")
        
        # Add recommendations
        if summary["overall_status"] in ["failed", "critical"]:
            message_lines.extend([
                f"",
                f"💡 Recommendations:",
                f"   • Review and fix critical/high priority issues",
                f"   • Consider running refinement cycle",
                f"   • Check compliance with security best practices"
            ])
        elif summary["overall_status"] == "warning":
            message_lines.extend([
                f"",
                f"💡 Recommendations:",
                f"   • Address warnings to improve code quality",
                f"   • Consider optional improvements"
            ])
        else:
            message_lines.extend([
                f"",
                f"🎉 All validations passed! Code is ready for deployment."
            ])
        
        return "\n".join(message_lines) 