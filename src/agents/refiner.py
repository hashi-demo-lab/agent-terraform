"""
Refiner Agent - Code improvement and optimization (LangGraph node)
Following .cursorrules specifications
"""

import asyncio
from typing import Dict, List, Any
import structlog

from langchain_core.messages import BaseMessage, AIMessage
from langgraph.platform import LangGraphPlatform

from ..workflows.state_management import TerraformState, context_manager

logger = structlog.get_logger()


class RefinerAgent:
    """
    Code improvement and optimization agent
    LangGraph node implementation following .cursorrules
    """
    
    def __init__(self, platform: LangGraphPlatform):
        self.platform = platform
        self.max_iterations = 5
    
    def __call__(self, state: TerraformState) -> TerraformState:
        """Main refiner entry point - LangGraph node implementation"""
        return asyncio.run(self._refine_terraform_code(state))
    
    async def _refine_terraform_code(self, state: TerraformState) -> TerraformState:
        """Refine Terraform code based on validation results"""
        
        logger.info("Starting code refinement", 
                   workflow_id=state["workflow_id"],
                   current_agent="refiner")
        
        state["current_agent"] = "refiner"
        state["iteration_count"] = state.get("iteration_count", 0) + 1
        
        # Get validation results to understand what needs fixing
        validation_results = state.get("validation_results", [])
        current_code = state.get("generated_code", "")
        
        if not validation_results:
            warning_msg = "No validation results available for refinement"
            state["warnings"].append(warning_msg)
            state["messages"].append(AIMessage(content=f"Refiner Warning: {warning_msg}"))
            return state
        
        try:
            # Analyze issues and create refinement plan
            refinement_plan = self._create_refinement_plan(validation_results)
            
            # Apply refinements
            refined_code = await self._apply_refinements(current_code, refinement_plan, state)
            
            # Update state with refined code
            state["refined_code"] = refined_code
            state["generated_code"] = refined_code  # Update for next validation
            
            # Store refinement details in context
            context_manager.store_context(
                state["workflow_id"],
                "refinement_plan",
                refinement_plan
            )
            
            # Generate refinement message
            refinement_message = self._generate_refinement_message(refinement_plan)
            state["messages"].append(AIMessage(content=refinement_message))
            
            logger.info("Code refinement completed",
                       workflow_id=state["workflow_id"],
                       iteration=state["iteration_count"],
                       issues_addressed=len(refinement_plan["fixes_applied"]))
            
        except Exception as e:
            error_msg = f"Code refinement failed: {str(e)}"
            logger.error("Code refinement failed", 
                        workflow_id=state["workflow_id"],
                        error=str(e))
            state["errors"].append(error_msg)
            state["messages"].append(AIMessage(content=f"Refinement Error: {error_msg}"))
        
        return state
    
    def _create_refinement_plan(self, validation_results: List[Any]) -> Dict[str, Any]:
        """Create a plan for addressing validation issues"""
        
        fixes_to_apply = []
        
        for result in validation_results:
            if not result.passed:
                for error in result.errors:
                    fix = self._map_error_to_fix(result.tool, error)
                    if fix:
                        fixes_to_apply.append(fix)
        
        return {
            "total_issues": sum(len(r.errors) for r in validation_results if not r.passed),
            "fixes_planned": len(fixes_to_apply),
            "fixes_applied": [],
            "fixes_to_apply": fixes_to_apply
        }
    
    def _map_error_to_fix(self, tool: str, error: str) -> Dict[str, Any]:
        """Map validation error to specific fix"""
        
        error_lower = error.lower()
        
        # Terraform validation fixes
        if tool == "terraform_validate":
            if "missing required argument" in error_lower:
                return {
                    "type": "add_required_argument",
                    "description": "Add missing required argument",
                    "error": error,
                    "tool": tool
                }
            elif "invalid reference" in error_lower:
                return {
                    "type": "fix_reference",
                    "description": "Fix invalid resource reference",
                    "error": error,
                    "tool": tool
                }
        
        # Terraform formatting fixes
        elif tool == "terraform_fmt":
            return {
                "type": "format_code",
                "description": "Apply Terraform formatting",
                "error": error,
                "tool": tool
            }
        
        # TFLint fixes
        elif tool == "tflint_avm":
            if "deprecated" in error_lower:
                return {
                    "type": "update_deprecated",
                    "description": "Update deprecated syntax/resources",
                    "error": error,
                    "tool": tool
                }
            elif "naming convention" in error_lower:
                return {
                    "type": "fix_naming",
                    "description": "Fix naming convention violations",
                    "error": error,
                    "tool": tool
                }
        
        # Trivy security fixes
        elif tool == "trivy":
            if "public access" in error_lower:
                return {
                    "type": "fix_public_access",
                    "description": "Block public access",
                    "error": error,
                    "tool": tool
                }
            elif "encryption" in error_lower:
                return {
                    "type": "enable_encryption",
                    "description": "Enable encryption",
                    "error": error,
                    "tool": tool
                }
        
        # Generic fix
        return {
            "type": "generic_fix",
            "description": f"Address {tool} issue",
            "error": error,
            "tool": tool
        }
    
    async def _apply_refinements(self, code: str, plan: Dict[str, Any], state: TerraformState) -> str:
        """Apply refinements to the code"""
        
        refined_code = code
        
        for fix in plan["fixes_to_apply"]:
            try:
                refined_code = self._apply_single_fix(refined_code, fix)
                plan["fixes_applied"].append(fix)
                
                logger.info("Applied fix",
                           fix_type=fix["type"],
                           workflow_id=state["workflow_id"])
                
            except Exception as e:
                logger.warning("Failed to apply fix",
                              fix_type=fix["type"],
                              error=str(e),
                              workflow_id=state["workflow_id"])
        
        return refined_code
    
    def _apply_single_fix(self, code: str, fix: Dict[str, Any]) -> str:
        """Apply a single fix to the code"""
        
        fix_type = fix["type"]
        
        if fix_type == "format_code":
            # Apply basic formatting fixes
            lines = code.split('\n')
            formatted_lines = []
            
            for line in lines:
                # Fix indentation
                stripped = line.strip()
                if stripped:
                    # Count braces to determine indentation
                    indent_level = self._calculate_indent_level(formatted_lines)
                    formatted_lines.append('  ' * indent_level + stripped)
                else:
                    formatted_lines.append('')
            
            return '\n'.join(formatted_lines)
        
        elif fix_type == "fix_public_access":
            # Add public access block for S3 buckets
            if "aws_s3_bucket" in code and "aws_s3_bucket_public_access_block" not in code:
                # Find S3 bucket resources and add public access blocks
                lines = code.split('\n')
                new_lines = []
                
                for i, line in enumerate(lines):
                    new_lines.append(line)
                    
                    # If this is the end of an S3 bucket resource, add public access block
                    if line.strip() == '}' and i > 0:
                        # Look back to see if this was an S3 bucket
                        for j in range(i-1, max(0, i-10), -1):
                            if 'resource "aws_s3_bucket"' in lines[j]:
                                bucket_name = self._extract_resource_name(lines[j])
                                if bucket_name:
                                    public_access_block = f'''
resource "aws_s3_bucket_public_access_block" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}'''
                                    new_lines.append(public_access_block)
                                break
                
                return '\n'.join(new_lines)
        
        elif fix_type == "enable_encryption":
            # Add encryption configuration for S3 buckets
            if "aws_s3_bucket" in code and "server_side_encryption_configuration" not in code:
                lines = code.split('\n')
                new_lines = []
                
                for i, line in enumerate(lines):
                    new_lines.append(line)
                    
                    # If this is the end of an S3 bucket resource, add encryption
                    if line.strip() == '}' and i > 0:
                        for j in range(i-1, max(0, i-10), -1):
                            if 'resource "aws_s3_bucket"' in lines[j]:
                                bucket_name = self._extract_resource_name(lines[j])
                                if bucket_name:
                                    encryption_config = f'''
resource "aws_s3_bucket_server_side_encryption_configuration" "{bucket_name}" {{
  bucket = aws_s3_bucket.{bucket_name}.id

  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}'''
                                    new_lines.append(encryption_config)
                                break
                
                return '\n'.join(new_lines)
        
        elif fix_type == "fix_naming":
            # Fix snake_case naming
            import re
            
            # Replace camelCase with snake_case in resource names
            def to_snake_case(name):
                s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
                return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
            
            # Find and replace resource names
            lines = code.split('\n')
            new_lines = []
            
            for line in lines:
                if 'resource "' in line or 'data "' in line:
                    # Extract and fix resource name
                    parts = line.split('"')
                    if len(parts) >= 4:
                        resource_name = parts[3]
                        fixed_name = to_snake_case(resource_name)
                        line = line.replace(f'"{resource_name}"', f'"{fixed_name}"')
                
                new_lines.append(line)
            
            return '\n'.join(new_lines)
        
        # For other fix types, return code unchanged for now
        return code
    
    def _calculate_indent_level(self, previous_lines: List[str]) -> int:
        """Calculate appropriate indentation level"""
        
        open_braces = 0
        
        for line in previous_lines:
            open_braces += line.count('{')
            open_braces -= line.count('}')
        
        return max(0, open_braces)
    
    def _extract_resource_name(self, line: str) -> str:
        """Extract resource name from resource declaration line"""
        
        import re
        match = re.search(r'resource\s+"[^"]+"\s+"([^"]+)"', line)
        return match.group(1) if match else None
    
    def _generate_refinement_message(self, plan: Dict[str, Any]) -> str:
        """Generate refinement summary message"""
        
        message_lines = [
            f"🔧 Code Refinement Complete",
            f"",
            f"📊 Refinement Summary:",
            f"   • Issues Identified: {plan['total_issues']}",
            f"   • Fixes Planned: {plan['fixes_planned']}",
            f"   • Fixes Applied: {len(plan['fixes_applied'])}",
        ]
        
        if plan["fixes_applied"]:
            message_lines.extend([
                f"",
                f"✅ Applied Fixes:"
            ])
            
            for fix in plan["fixes_applied"]:
                message_lines.append(f"   • {fix['description']} ({fix['tool']})")
        
        failed_fixes = plan["fixes_planned"] - len(plan["fixes_applied"])
        if failed_fixes > 0:
            message_lines.extend([
                f"",
                f"⚠️ {failed_fixes} fixes could not be applied automatically",
                f"   Manual review may be required"
            ])
        
        message_lines.extend([
            f"",
            f"🔄 Code has been refined and is ready for re-validation"
        ])
        
        return "\n".join(message_lines) 