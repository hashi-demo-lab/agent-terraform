"""
State definitions for Terraform Code Generation Agent
LangGraph Platform compatible state management
"""

from typing import Dict, List, Optional, TypedDict, Annotated, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from langchain_core.messages import BaseMessage
from langgraph import add_messages


class WorkflowStatus(Enum):
    """Workflow execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationStatus(Enum):
    """Validation status for code"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class ValidationResult:
    """Individual validation result"""
    tool: str
    status: ValidationStatus
    passed: bool
    messages: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequirementSpec:
    """Infrastructure requirement specification"""
    provider: str
    resources: List[Dict[str, Any]]
    environment: str
    compliance_requirements: List[str] = field(default_factory=list)
    custom_rules: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TerraformState(TypedDict):
    """
    Main LangGraph state for Terraform Code Generation Agent
    Compatible with LangGraph Platform deployment
    """
    # Core workflow state
    messages: Annotated[List[BaseMessage], add_messages]
    workflow_id: str
    thread_id: str
    status: WorkflowStatus
    current_agent: str
    iteration_count: int
    max_iterations: int
    
    # Requirements and input
    requirements: Optional[RequirementSpec]
    input_code: str
    file_paths: List[str]
    
    # Generated content
    generated_code: str
    refined_code: str
    documentation: str
    
    # Validation and analysis
    validation_results: List[ValidationResult]
    analysis_results: Dict[str, Any]
    
    # Context and memory
    context_memory: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    
    # MCP integration
    mcp_context: Dict[str, Any]
    provider_docs: Dict[str, Any]
    registry_data: Dict[str, Any]
    
    # Error handling and debugging
    errors: List[str]
    warnings: List[str]
    debug_info: Dict[str, Any]
    
    # Performance metrics
    execution_metrics: Dict[str, float]
    start_time: Optional[datetime]
    end_time: Optional[datetime] 