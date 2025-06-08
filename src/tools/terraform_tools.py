"""
Terraform CLI Tools - LangGraph ToolNode implementation
Following .cursorrules specifications
"""

import asyncio
import subprocess
import tempfile
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import structlog

from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

from ..workflows.state_management import ValidationResult, ValidationStatus

logger = structlog.get_logger()


@dataclass
class TerraformExecutionResult:
    """Result of Terraform command execution"""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    success: bool


class TerraformTools:
    """
    Terraform CLI wrapper tools for validation and execution
    """
    
    def __init__(self):
        self.terraform_binary = self._find_terraform_binary()
        self.temp_dir = None
    
    def _find_terraform_binary(self) -> str:
        """Find Terraform binary in PATH"""
        try:
            result = subprocess.run(
                ["which", "terraform"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            # Fallback to common locations
            common_paths = [
                "/usr/local/bin/terraform",
                "/usr/bin/terraform",
                "/opt/homebrew/bin/terraform"
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    return path
            
            return "terraform"  # Hope it's in PATH
    
    async def execute_terraform_command(self, 
                                      command: List[str], 
                                      working_dir: str = None,
                                      timeout: int = 300) -> TerraformExecutionResult:
        """Execute Terraform command asynchronously"""
        
        full_command = [self.terraform_binary] + command
        
        logger.info("Executing Terraform command", 
                   command=" ".join(full_command),
                   working_dir=working_dir)
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            process = await asyncio.create_subprocess_exec(
                *full_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            result = TerraformExecutionResult(
                command=" ".join(full_command),
                exit_code=process.returncode,
                stdout=stdout.decode('utf-8'),
                stderr=stderr.decode('utf-8'),
                execution_time=execution_time,
                success=process.returncode == 0
            )
            
            logger.info("Terraform command completed",
                       command=" ".join(command),
                       exit_code=process.returncode,
                       execution_time=execution_time)
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("Terraform command timed out",
                        command=" ".join(command),
                        timeout=timeout)
            
            return TerraformExecutionResult(
                command=" ".join(full_command),
                exit_code=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                execution_time=timeout,
                success=False
            )
        
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            
            logger.error("Terraform command failed",
                        command=" ".join(command),
                        error=str(e))
            
            return TerraformExecutionResult(
                command=" ".join(full_command),
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time=execution_time,
                success=False
            )
    
    def create_temp_terraform_dir(self, terraform_code: str) -> str:
        """Create temporary directory with Terraform code"""
        
        if self.temp_dir:
            self.cleanup_temp_dir()
        
        self.temp_dir = tempfile.mkdtemp(prefix="terraform_agent_")
        
        # Write Terraform code to main.tf
        main_tf_path = Path(self.temp_dir) / "main.tf"
        with open(main_tf_path, 'w') as f:
            f.write(terraform_code)
        
        logger.info("Created temporary Terraform directory",
                   temp_dir=self.temp_dir)
        
        return self.temp_dir
    
    def cleanup_temp_dir(self):
        """Clean up temporary directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary directory", temp_dir=self.temp_dir)
            self.temp_dir = None


# Global Terraform tools instance
terraform_tools = TerraformTools()


@tool
def terraform_validate_tool(code: str) -> Dict[str, Any]:
    """
    Validate Terraform code syntax and configuration.
    
    Args:
        code: Terraform code to validate
        
    Returns:
        Dict with validation results
    """
    
    async def _validate():
        # Create temporary directory with code
        temp_dir = terraform_tools.create_temp_terraform_dir(code)
        
        try:
            # Initialize Terraform
            init_result = await terraform_tools.execute_terraform_command(
                ["init", "-backend=false"],
                working_dir=temp_dir
            )
            
            if not init_result.success:
                return ValidationResult(
                    tool="terraform_validate",
                    status=ValidationStatus.FAILED,
                    passed=False,
                    errors=[f"Terraform init failed: {init_result.stderr}"],
                    execution_time=init_result.execution_time
                )
            
            # Run validation
            validate_result = await terraform_tools.execute_terraform_command(
                ["validate"],
                working_dir=temp_dir
            )
            
            # Parse results
            if validate_result.success:
                return ValidationResult(
                    tool="terraform_validate",
                    status=ValidationStatus.PASSED,
                    passed=True,
                    messages=["Terraform validation passed"],
                    execution_time=init_result.execution_time + validate_result.execution_time
                )
            else:
                return ValidationResult(
                    tool="terraform_validate",
                    status=ValidationStatus.FAILED,
                    passed=False,
                    errors=[validate_result.stderr],
                    execution_time=init_result.execution_time + validate_result.execution_time
                )
        
        finally:
            terraform_tools.cleanup_temp_dir()
    
    # Run async function
    result = asyncio.run(_validate())
    
    return {
        "tool": result.tool,
        "passed": result.passed,
        "status": result.status.value,
        "messages": result.messages,
        "errors": result.errors,
        "execution_time": result.execution_time
    }


@tool
def terraform_fmt_tool(code: str) -> Dict[str, Any]:
    """
    Format Terraform code and check formatting compliance.
    
    Args:
        code: Terraform code to format
        
    Returns:
        Dict with formatting results
    """
    
    async def _format():
        # Create temporary directory with code
        temp_dir = terraform_tools.create_temp_terraform_dir(code)
        
        try:
            # Run terraform fmt
            fmt_result = await terraform_tools.execute_terraform_command(
                ["fmt", "-check", "-diff"],
                working_dir=temp_dir
            )
            
            if fmt_result.success:
                return ValidationResult(
                    tool="terraform_fmt",
                    status=ValidationStatus.PASSED,
                    passed=True,
                    messages=["Terraform formatting is correct"],
                    execution_time=fmt_result.execution_time
                )
            else:
                # Get formatted code
                format_result = await terraform_tools.execute_terraform_command(
                    ["fmt", "-"],
                    working_dir=temp_dir
                )
                
                return ValidationResult(
                    tool="terraform_fmt",
                    status=ValidationStatus.WARNING,
                    passed=False,
                    warnings=["Code formatting issues found"],
                    messages=[fmt_result.stdout] if fmt_result.stdout else [],
                    execution_time=fmt_result.execution_time,
                    metadata={"formatted_code": format_result.stdout if format_result.success else None}
                )
        
        finally:
            terraform_tools.cleanup_temp_dir()
    
    # Run async function
    result = asyncio.run(_format())
    
    return {
        "tool": result.tool,
        "passed": result.passed,
        "status": result.status.value,
        "messages": result.messages,
        "warnings": result.warnings,
        "execution_time": result.execution_time,
        "metadata": result.metadata
    }


@tool
def terraform_plan_tool(code: str) -> Dict[str, Any]:
    """
    Generate Terraform execution plan.
    
    Args:
        code: Terraform code to plan
        
    Returns:
        Dict with plan results
    """
    
    async def _plan():
        # Create temporary directory with code
        temp_dir = terraform_tools.create_temp_terraform_dir(code)
        
        try:
            # Initialize Terraform
            init_result = await terraform_tools.execute_terraform_command(
                ["init", "-backend=false"],
                working_dir=temp_dir
            )
            
            if not init_result.success:
                return ValidationResult(
                    tool="terraform_plan",
                    status=ValidationStatus.FAILED,
                    passed=False,
                    errors=[f"Terraform init failed: {init_result.stderr}"],
                    execution_time=init_result.execution_time
                )
            
            # Run plan
            plan_result = await terraform_tools.execute_terraform_command(
                ["plan", "-out=tfplan"],
                working_dir=temp_dir
            )
            
            if plan_result.success:
                return ValidationResult(
                    tool="terraform_plan",
                    status=ValidationStatus.PASSED,
                    passed=True,
                    messages=["Terraform plan generated successfully"],
                    execution_time=init_result.execution_time + plan_result.execution_time,
                    metadata={"plan_output": plan_result.stdout}
                )
            else:
                return ValidationResult(
                    tool="terraform_plan",
                    status=ValidationStatus.FAILED,
                    passed=False,
                    errors=[plan_result.stderr],
                    execution_time=init_result.execution_time + plan_result.execution_time
                )
        
        finally:
            terraform_tools.cleanup_temp_dir()
    
    # Run async function
    result = asyncio.run(_plan())
    
    return {
        "tool": result.tool,
        "passed": result.passed,
        "status": result.status.value,
        "messages": result.messages,
        "errors": result.errors,
        "execution_time": result.execution_time,
        "metadata": result.metadata
    }


@tool
def terraform_test_tool(code: str) -> Dict[str, Any]:
    """
    Run Terraform tests if test files are present.
    
    Args:
        code: Terraform code to test
        
    Returns:
        Dict with test results
    """
    
    async def _test():
        # Create temporary directory with code
        temp_dir = terraform_tools.create_temp_terraform_dir(code)
        
        try:
            # Check if test files exist (this is a placeholder - would need actual test files)
            test_files = list(Path(temp_dir).glob("*.tftest.hcl"))
            
            if not test_files:
                return ValidationResult(
                    tool="terraform_test",
                    status=ValidationStatus.WARNING,
                    passed=True,
                    warnings=["No test files found"],
                    execution_time=0.0
                )
            
            # Initialize Terraform
            init_result = await terraform_tools.execute_terraform_command(
                ["init", "-backend=false"],
                working_dir=temp_dir
            )
            
            if not init_result.success:
                return ValidationResult(
                    tool="terraform_test",
                    status=ValidationStatus.FAILED,
                    passed=False,
                    errors=[f"Terraform init failed: {init_result.stderr}"],
                    execution_time=init_result.execution_time
                )
            
            # Run tests
            test_result = await terraform_tools.execute_terraform_command(
                ["test"],
                working_dir=temp_dir
            )
            
            if test_result.success:
                return ValidationResult(
                    tool="terraform_test",
                    status=ValidationStatus.PASSED,
                    passed=True,
                    messages=["All Terraform tests passed"],
                    execution_time=init_result.execution_time + test_result.execution_time,
                    metadata={"test_output": test_result.stdout}
                )
            else:
                return ValidationResult(
                    tool="terraform_test",
                    status=ValidationStatus.FAILED,
                    passed=False,
                    errors=[test_result.stderr],
                    execution_time=init_result.execution_time + test_result.execution_time
                )
        
        finally:
            terraform_tools.cleanup_temp_dir()
    
    # Run async function
    result = asyncio.run(_test())
    
    return {
        "tool": result.tool,
        "passed": result.passed,
        "status": result.status.value,
        "messages": result.messages,
        "warnings": getattr(result, 'warnings', []),
        "errors": result.errors,
        "execution_time": result.execution_time,
        "metadata": result.metadata
    }


@tool
def terraform_providers_tool(code: str) -> Dict[str, Any]:
    """
    Get information about Terraform providers used in the code.
    
    Args:
        code: Terraform code to analyze
        
    Returns:
        Dict with provider information
    """
    
    async def _providers():
        # Create temporary directory with code
        temp_dir = terraform_tools.create_temp_terraform_dir(code)
        
        try:
            # Initialize Terraform
            init_result = await terraform_tools.execute_terraform_command(
                ["init", "-backend=false"],
                working_dir=temp_dir
            )
            
            if not init_result.success:
                return ValidationResult(
                    tool="terraform_providers",
                    status=ValidationStatus.FAILED,
                    passed=False,
                    errors=[f"Terraform init failed: {init_result.stderr}"],
                    execution_time=init_result.execution_time
                )
            
            # Get providers
            providers_result = await terraform_tools.execute_terraform_command(
                ["providers"],
                working_dir=temp_dir
            )
            
            if providers_result.success:
                return ValidationResult(
                    tool="terraform_providers",
                    status=ValidationStatus.PASSED,
                    passed=True,
                    messages=["Provider information retrieved"],
                    execution_time=init_result.execution_time + providers_result.execution_time,
                    metadata={"providers_output": providers_result.stdout}
                )
            else:
                return ValidationResult(
                    tool="terraform_providers",
                    status=ValidationStatus.FAILED,
                    passed=False,
                    errors=[providers_result.stderr],
                    execution_time=init_result.execution_time + providers_result.execution_time
                )
        
        finally:
            terraform_tools.cleanup_temp_dir()
    
    # Run async function
    result = asyncio.run(_providers())
    
    return {
        "tool": result.tool,
        "passed": result.passed,
        "status": result.status.value,
        "messages": result.messages,
        "errors": result.errors,
        "execution_time": result.execution_time,
        "metadata": result.metadata
    }


# Create ToolNode with all Terraform tools
terraform_tool_node = ToolNode([
    terraform_validate_tool,
    terraform_fmt_tool,
    terraform_plan_tool,
    terraform_test_tool,
    terraform_providers_tool
]) 