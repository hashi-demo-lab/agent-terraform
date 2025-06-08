"""
Tools for Terraform Code Generation Agent
LangGraph Platform compatible tool implementations
"""

from typing import Dict, Any, List
from langchain_core.tools import tool


@tool
def terraform_validate_tool(code: str) -> Dict[str, Any]:
    """
    Validate Terraform code syntax and configuration.
    
    Args:
        code: Terraform code to validate
        
    Returns:
        Dict with validation results
    """
    # Simulate terraform validate
    # In real implementation, this would run actual terraform validate
    
    # Basic syntax checks
    if not code.strip():
        return {
            "tool": "terraform_validate",
            "passed": False,
            "messages": [],
            "errors": ["Empty Terraform code provided"],
            "warnings": []
        }
    
    # Check for basic Terraform structure
    has_terraform_block = "terraform {" in code
    has_provider_block = "provider " in code
    
    if not has_terraform_block:
        return {
            "tool": "terraform_validate",
            "passed": False,
            "messages": [],
            "errors": ["Missing terraform configuration block"],
            "warnings": []
        }
    
    if not has_provider_block:
        return {
            "tool": "terraform_validate",
            "passed": False,
            "messages": [],
            "errors": ["Missing provider configuration"],
            "warnings": []
        }
    
    return {
        "tool": "terraform_validate",
        "passed": True,
        "messages": ["Terraform configuration is valid"],
        "errors": [],
        "warnings": []
    }


@tool
def terraform_fmt_tool(code: str) -> Dict[str, Any]:
    """
    Check Terraform code formatting.
    
    Args:
        code: Terraform code to format check
        
    Returns:
        Dict with formatting results
    """
    # Simulate terraform fmt check
    # In real implementation, this would run actual terraform fmt
    
    # Basic formatting checks
    lines = code.split('\n')
    issues = []
    
    for i, line in enumerate(lines, 1):
        # Check for basic indentation issues
        if line.strip() and line.startswith(' ') and not line.startswith('  '):
            issues.append(f"Line {i}: Inconsistent indentation")
        
        # Check for trailing spaces
        if line.endswith(' '):
            issues.append(f"Line {i}: Trailing whitespace")
    
    if issues:
        return {
            "tool": "terraform_fmt",
            "passed": False,
            "messages": [],
            "errors": issues,
            "warnings": []
        }
    
    return {
        "tool": "terraform_fmt",
        "passed": True,
        "messages": ["Code formatting is correct"],
        "errors": [],
        "warnings": []
    }


@tool
def terraform_test_tool(code: str) -> Dict[str, Any]:
    """
    Run Terraform tests on the configuration.
    
    Args:
        code: Terraform code to test
        
    Returns:
        Dict with test results
    """
    # Simulate terraform test
    # In real implementation, this would run actual terraform test
    
    # Basic test checks
    has_outputs = "output " in code
    has_variables = "variable " in code
    has_resources = "resource " in code
    
    warnings = []
    if not has_outputs:
        warnings.append("No outputs defined - consider adding outputs for important resources")
    
    if not has_variables:
        warnings.append("No variables defined - consider parameterizing your configuration")
    
    if not has_resources:
        return {
            "tool": "terraform_test",
            "passed": False,
            "messages": [],
            "errors": ["No resources defined in configuration"],
            "warnings": warnings
        }
    
    return {
        "tool": "terraform_test",
        "passed": True,
        "messages": ["Terraform tests passed"],
        "errors": [],
        "warnings": warnings
    }


@tool
def tflint_avm_validate_tool(code: str) -> Dict[str, Any]:
    """
    Validate Terraform code against Azure Verified Modules ruleset.
    
    Args:
        code: Terraform code to validate
        
    Returns:
        Dict with AVM validation results
    """
    # Simulate TFLint with AVM ruleset
    # In real implementation, this would run actual tflint with AVM rules
    
    issues = []
    warnings = []
    
    # Check for AVM best practices
    if "default_tags" not in code:
        warnings.append("Consider adding default_tags for consistent resource tagging")
    
    # Check for variable validation
    if "variable " in code and "validation {" not in code:
        warnings.append("Consider adding validation blocks to variables")
    
    # Check for resource descriptions
    if "description" not in code:
        warnings.append("Consider adding descriptions to variables and outputs")
    
    # Check for security best practices
    if "aws_s3_bucket" in code and "aws_s3_bucket_public_access_block" not in code:
        issues.append("S3 bucket should have public access block configured")
    
    if issues:
        return {
            "tool": "tflint_avm",
            "passed": False,
            "messages": [],
            "errors": issues,
            "warnings": warnings
        }
    
    return {
        "tool": "tflint_avm",
        "passed": True,
        "messages": ["AVM best practices compliance verified"],
        "errors": [],
        "warnings": warnings
    }


@tool
def trivy_scan_tool(code: str) -> Dict[str, Any]:
    """
    Scan Terraform code for security vulnerabilities.
    
    Args:
        code: Terraform code to scan
        
    Returns:
        Dict with security scan results
    """
    # Simulate Trivy security scan
    # In real implementation, this would run actual trivy scan
    
    security_issues = []
    warnings = []
    
    # Check for common security issues
    if "aws_s3_bucket" in code:
        if "server_side_encryption_configuration" not in code:
            security_issues.append("S3 bucket should have server-side encryption enabled")
        
        if "versioning_configuration" not in code:
            warnings.append("Consider enabling versioning for S3 bucket")
        
        if "public_access_block" not in code:
            security_issues.append("S3 bucket should have public access blocked")
    
    # Check for hardcoded secrets (basic check)
    if any(keyword in code.lower() for keyword in ["password", "secret", "key"]):
        if any(char in code for char in ['"', "'"]):
            warnings.append("Potential hardcoded secrets detected - use variables or secret management")
    
    if security_issues:
        return {
            "tool": "trivy",
            "passed": False,
            "messages": [],
            "errors": security_issues,
            "warnings": warnings
        }
    
    return {
        "tool": "trivy",
        "passed": True,
        "messages": ["No security vulnerabilities found"],
        "errors": [],
        "warnings": warnings
    } 