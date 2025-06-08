# src/tools/tflint_tools.py
"""
TFLint Tools - AVM ruleset integration (LangGraph ToolNode)
Following .cursorrules specifications
"""

import asyncio
import subprocess
import tempfile
import os
from typing import Dict, List, Any
from pathlib import Path
import structlog

from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

from ..workflows.state_management import ValidationResult, ValidationStatus

logger = structlog.get_logger()


class TFLintTools:
    """
    TFLint CLI wrapper tools for Azure Verified Modules validation
    """
    
    def __init__(self):
        self.tflint_binary = self._find_tflint_binary()
        self.temp_dir = None
    
    def _find_tflint_binary(self) -> str:
        """Find TFLint binary in PATH"""
        try:
            result = subprocess.run(
                ["which", "tflint"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "tflint"  # Hope it's in PATH
    
    async def execute_tflint_command(self, 
                                   command: List[str], 
                                   working_dir: str = None,
                                   timeout: int = 120) -> Dict[str, Any]:
        """Execute TFLint command asynchronously"""
        
        full_command = [self.tflint_binary] + command
        
        logger.info("Executing TFLint command", 
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
            
            return {
                "command": " ".join(full_command),
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8'),
                "execution_time": execution_time,
                "success": process.returncode == 0
            }
            
        except asyncio.TimeoutError:
            logger.error("TFLint command timed out",
                        command=" ".join(command),
                        timeout=timeout)
            
            return {
                "command": " ".join(full_command),
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "execution_time": timeout,
                "success": False
            }
        
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            
            logger.error("TFLint command failed",
                        command=" ".join(command),
                        error=str(e))
            
            return {
                "command": " ".join(full_command),
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "execution_time": execution_time,
                "success": False
            }
    
    def create_temp_terraform_dir(self, terraform_code: str) -> str:
        """Create temporary directory with Terraform code and TFLint config"""
        
        if self.temp_dir:
            self.cleanup_temp_dir()
        
        self.temp_dir = tempfile.mkdtemp(prefix="tflint_")
        
        # Write Terraform code to main.tf
        main_tf_path = Path(self.temp_dir) / "main.tf"
        with open(main_tf_path, 'w') as f:
            f.write(terraform_code)
        
        # Create TFLint configuration with AVM rules
        tflint_config = self._create_avm_tflint_config()
        config_path = Path(self.temp_dir) / ".tflint.hcl"
        with open(config_path, 'w') as f:
            f.write(tflint_config)
        
        logger.info("Created temporary TFLint directory",
                   temp_dir=self.temp_dir)
        
        return self.temp_dir
    
    def _create_avm_tflint_config(self) -> str:
        """Create TFLint configuration with Azure Verified Modules rules"""
        
        return """
config {
  module = true
  force = false
  disabled_by_default = false
}

# Azure Verified Modules ruleset
plugin "azurerm" {
  enabled = true
  version = "0.25.1"
  source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}

# AWS provider rules (for AWS modules)
plugin "aws" {
  enabled = true
  version = "0.24.1"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}

# Google Cloud provider rules
plugin "google" {
  enabled = true
  version = "0.23.1"
  source  = "github.com/terraform-linters/tflint-ruleset-google"
}

# Core Terraform rules following AVM best practices
rule "terraform_deprecated_interpolation" {
  enabled = true
}

rule "terraform_unused_declarations" {
  enabled = true
}

rule "terraform_comment_syntax" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_typed_variables" {
  enabled = true
}

rule "terraform_module_pinned_source" {
  enabled = true
}

rule "terraform_naming_convention" {
  enabled = true
  format  = "snake_case"
}

rule "terraform_standard_module_structure" {
  enabled = true
}

rule "terraform_workspace_remote" {
  enabled = true
}

# AVM-specific rules
rule "terraform_required_version" {
  enabled = true
}

rule "terraform_required_providers" {
  enabled = true
}
"""
    
    def cleanup_temp_dir(self):
        """Clean up temporary directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary directory", temp_dir=self.temp_dir)
            self.temp_dir = None


# Global TFLint tools instance
tflint_tools = TFLintTools()


@tool
def tflint_avm_validate_tool(code: str) -> Dict[str, Any]:
    """
    Validate Terraform code against Azure Verified Modules ruleset.
    
    Args:
        code: Terraform code to validate
        
    Returns:
        Dict with validation results
    """
    
    async def _validate():
        # Create temporary directory with code and config
        temp_dir = tflint_tools.create_temp_terraform_dir(code)
        
        try:
            # Initialize TFLint (download plugins)
            init_result = await tflint_tools.execute_tflint_command(
                ["--init"],
                working_dir=temp_dir
            )
            
            if not init_result["success"]:
                logger.warning("TFLint init failed, continuing with validation",
                              error=init_result["stderr"])
            
            # Run TFLint validation
            validate_result = await tflint_tools.execute_tflint_command(
                ["--format=json"],
                working_dir=temp_dir
            )
            
            # Parse results
            issues = []
            warnings = []
            
            if validate_result["success"]:
                # TFLint returns 0 when no issues found
                return ValidationResult(
                    tool="tflint_avm",
                    status=ValidationStatus.PASSED,
                    passed=True,
                    messages=["TFLint AVM validation passed"],
                    execution_time=init_result["execution_time"] + validate_result["execution_time"]
                )
            else:
                # Parse TFLint output for issues
                stdout = validate_result["stdout"]
                stderr = validate_result["stderr"]
                
                # Try to parse JSON output
                try:
                    import json
                    if stdout.strip():
                        tflint_results = json.loads(stdout)
                        
                        for issue in tflint_results.get("issues", []):
                            severity = issue.get("rule", {}).get("severity", "error")
                            message = f"{issue.get('message', 'Unknown issue')} ({issue.get('rule', {}).get('name', 'unknown_rule')})"
                            
                            if severity.lower() in ["error", "warning"]:
                                if severity.lower() == "error":
                                    issues.append(message)
                                else:
                                    warnings.append(message)
                    
                except json.JSONDecodeError:
                    # Fallback to parsing stderr
                    if stderr:
                        issues.append(stderr)
                    elif stdout:
                        issues.append(stdout)
                    else:
                        issues.append("TFLint validation failed with unknown error")
                
                # Determine status based on issues
                if issues:
                    status = ValidationStatus.FAILED
                    passed = False
                elif warnings:
                    status = ValidationStatus.WARNING
                    passed = True
                else:
                    status = ValidationStatus.FAILED
                    passed = False
                    issues = ["TFLint validation failed"]
                
                return ValidationResult(
                    tool="tflint_avm",
                    status=status,
                    passed=passed,
                    errors=issues,
                    warnings=warnings,
                    execution_time=init_result["execution_time"] + validate_result["execution_time"]
                )
        
        finally:
            tflint_tools.cleanup_temp_dir()
    
    # Run async function
    result = asyncio.run(_validate())
    
    return {
        "tool": result.tool,
        "passed": result.passed,
        "status": result.status.value,
        "messages": result.messages,
        "errors": result.errors,
        "warnings": result.warnings,
        "execution_time": result.execution_time
    }


@tool
def tflint_format_check_tool(code: str) -> Dict[str, Any]:
    """
    Check Terraform code formatting with TFLint.
    
    Args:
        code: Terraform code to check
        
    Returns:
        Dict with formatting check results
    """
    
    async def _check_format():
        # Create temporary directory with code
        temp_dir = tflint_tools.create_temp_terraform_dir(code)
        
        try:
            # Run TFLint with format-specific rules
            result = await tflint_tools.execute_tflint_command(
                ["--only=terraform_comment_syntax,terraform_deprecated_interpolation"],
                working_dir=temp_dir
            )
            
            if result["success"]:
                return ValidationResult(
                    tool="tflint_format",
                    status=ValidationStatus.PASSED,
                    passed=True,
                    messages=["Code formatting follows best practices"],
                    execution_time=result["execution_time"]
                )
            else:
                return ValidationResult(
                    tool="tflint_format",
                    status=ValidationStatus.WARNING,
                    passed=False,
                    warnings=[result["stderr"] or result["stdout"] or "Formatting issues found"],
                    execution_time=result["execution_time"]
                )
        
        finally:
            tflint_tools.cleanup_temp_dir()
    
    # Run async function
    result = asyncio.run(_check_format())
    
    return {
        "tool": result.tool,
        "passed": result.passed,
        "status": result.status.value,
        "messages": result.messages,
        "warnings": result.warnings,
        "execution_time": result.execution_time
    }


@tool
def tflint_naming_check_tool(code: str) -> Dict[str, Any]:
    """
    Check Terraform naming conventions with TFLint.
    
    Args:
        code: Terraform code to check
        
    Returns:
        Dict with naming check results
    """
    
    async def _check_naming():
        # Create temporary directory with code
        temp_dir = tflint_tools.create_temp_terraform_dir(code)
        
        try:
            # Run TFLint with naming-specific rules
            result = await tflint_tools.execute_tflint_command(
                ["--only=terraform_naming_convention"],
                working_dir=temp_dir
            )
            
            if result["success"]:
                return ValidationResult(
                    tool="tflint_naming",
                    status=ValidationStatus.PASSED,
                    passed=True,
                    messages=["Naming conventions follow snake_case standard"],
                    execution_time=result["execution_time"]
                )
            else:
                return ValidationResult(
                    tool="tflint_naming",
                    status=ValidationStatus.WARNING,
                    passed=False,
                    warnings=[result["stderr"] or result["stdout"] or "Naming convention violations found"],
                    execution_time=result["execution_time"]
                )
        
        finally:
            tflint_tools.cleanup_temp_dir()
    
    # Run async function
    result = asyncio.run(_check_naming())
    
    return {
        "tool": result.tool,
        "passed": result.passed,
        "status": result.status.value,
        "messages": result.messages,
        "warnings": result.warnings,
        "execution_time": result.execution_time
    }


# Create ToolNode with all TFLint tools
tflint_tool_node = ToolNode([
    tflint_avm_validate_tool,
    tflint_format_check_tool,
    tflint_naming_check_tool
]) 