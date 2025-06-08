"""
LangGraph State Definitions and Management
Core state management for Terraform Code Generation Agent
"""

from typing import Dict, List, Optional, TypedDict, Annotated, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid
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
    Following .cursorrules specifications
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
    
    # LangMem context
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


class ValidationState(TypedDict):
    """State for validation pipeline workflow"""
    messages: Annotated[List[BaseMessage], add_messages]
    terraform_code: str
    validation_results: List[ValidationResult]
    overall_status: ValidationStatus
    iteration_count: int
    max_iterations: int
    should_continue: bool


class AnalysisState(TypedDict):
    """State for analysis workflow"""
    messages: Annotated[List[BaseMessage], add_messages]
    terraform_code: str
    analysis_categories: List[str]
    analysis_results: Dict[str, Any]
    issues_found: List[Dict[str, Any]]
    recommendations: List[str]
    score: float


class StateManager:
    """
    Manages LangGraph state transitions and persistence
    """
    
    def __init__(self):
        self.active_workflows: Dict[str, TerraformState] = {}
    
    def create_initial_state(self, 
                           requirements: Optional[RequirementSpec] = None,
                           input_code: str = "",
                           file_paths: List[str] = None) -> TerraformState:
        """Create initial workflow state"""
        
        workflow_id = str(uuid.uuid4())
        thread_id = f"terraform_{workflow_id}"
        
        initial_state: TerraformState = {
            # Core workflow state
            "messages": [],
            "workflow_id": workflow_id,
            "thread_id": thread_id,
            "status": WorkflowStatus.PENDING,
            "current_agent": "",
            "iteration_count": 0,
            "max_iterations": 5,
            
            # Requirements and input
            "requirements": requirements,
            "input_code": input_code,
            "file_paths": file_paths or ["main.tf"],
            
            # Generated content
            "generated_code": "",
            "refined_code": "",
            "documentation": "",
            
            # Validation and analysis
            "validation_results": [],
            "analysis_results": {},
            
            # LangMem context
            "context_memory": {},
            "conversation_history": [],
            
            # MCP integration
            "mcp_context": {},
            "provider_docs": {},
            "registry_data": {},
            
            # Error handling and debugging
            "errors": [],
            "warnings": [],
            "debug_info": {},
            
            # Performance metrics
            "execution_metrics": {},
            "start_time": datetime.now(),
            "end_time": None
        }
        
        self.active_workflows[workflow_id] = initial_state
        return initial_state
    
    def update_state(self, workflow_id: str, updates: Dict[str, Any]) -> TerraformState:
        """Update workflow state"""
        if workflow_id not in self.active_workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        state = self.active_workflows[workflow_id]
        
        # Update state with new values
        for key, value in updates.items():
            if key in state:
                state[key] = value
        
        return state
    
    def get_state(self, workflow_id: str) -> Optional[TerraformState]:
        """Get current workflow state"""
        return self.active_workflows.get(workflow_id)
    
    def complete_workflow(self, workflow_id: str, status: WorkflowStatus = WorkflowStatus.COMPLETED):
        """Mark workflow as completed"""
        if workflow_id in self.active_workflows:
            state = self.active_workflows[workflow_id]
            state["status"] = status
            state["end_time"] = datetime.now()
            
            # Calculate total execution time
            if state["start_time"]:
                execution_time = (state["end_time"] - state["start_time"]).total_seconds()
                state["execution_metrics"]["total_execution_time"] = execution_time
    
    def cleanup_workflow(self, workflow_id: str):
        """Clean up completed workflow"""
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
    
    def get_active_workflows(self) -> List[str]:
        """Get list of active workflow IDs"""
        return list(self.active_workflows.keys())
    
    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowStatus]:
        """Get workflow status"""
        state = self.get_state(workflow_id)
        return state["status"] if state else None


class StateValidator:
    """
    Validates state transitions and ensures state consistency
    """
    
    @staticmethod
    def validate_state_transition(current_agent: str, next_agent: str) -> bool:
        """Validate that state transition is allowed"""
        
        # Define allowed transitions based on .cursorrules workflow
        allowed_transitions = {
            "": ["planner"],
            "planner": ["generator", "analyzer"],
            "generator": ["validator"],
            "validator": ["refiner", "reviewer"],
            "refiner": ["generator", "validator"],
            "reviewer": ["end"],
            "analyzer": ["validator", "refiner"]
        }
        
        return next_agent in allowed_transitions.get(current_agent, [])
    
    @staticmethod
    def validate_requirements(requirements: RequirementSpec) -> List[str]:
        """Validate requirement specification"""
        errors = []
        
        if not requirements.provider:
            errors.append("Provider is required")
        
        if not requirements.resources:
            errors.append("At least one resource must be specified")
        
        if not requirements.environment:
            errors.append("Environment is required")
        
        # Validate provider is supported
        supported_providers = ["aws", "azurerm", "google", "kubernetes"]
        if requirements.provider not in supported_providers:
            errors.append(f"Provider {requirements.provider} not supported. Supported: {supported_providers}")
        
        return errors
    
    @staticmethod
    def validate_terraform_code(code: str) -> List[str]:
        """Basic validation of Terraform code structure"""
        errors = []
        
        if not code.strip():
            errors.append("Terraform code cannot be empty")
            return errors
        
        # Check for basic Terraform blocks
        required_patterns = ["resource", "variable", "output"]
        has_terraform_content = any(pattern in code for pattern in required_patterns)
        
        if not has_terraform_content:
            errors.append("No recognizable Terraform blocks found")
        
        # Check for balanced braces
        open_braces = code.count('{')
        close_braces = code.count('}')
        
        if open_braces != close_braces:
            errors.append(f"Unbalanced braces: {open_braces} opening, {close_braces} closing")
        
        return errors


class ContextManager:
    """
    Manages LangMem context and conversation history
    """
    
    def __init__(self):
        self.context_store: Dict[str, Dict[str, Any]] = {}
    
    def store_context(self, workflow_id: str, context_key: str, context_data: Any):
        """Store context data for workflow"""
        if workflow_id not in self.context_store:
            self.context_store[workflow_id] = {}
        
        self.context_store[workflow_id][context_key] = {
            "data": context_data,
            "timestamp": datetime.now(),
            "type": type(context_data).__name__
        }
    
    def retrieve_context(self, workflow_id: str, context_key: str) -> Optional[Any]:
        """Retrieve context data for workflow"""
        if workflow_id in self.context_store and context_key in self.context_store[workflow_id]:
            return self.context_store[workflow_id][context_key]["data"]
        return None
    
    def get_all_context(self, workflow_id: str) -> Dict[str, Any]:
        """Get all context for workflow"""
        return self.context_store.get(workflow_id, {})
    
    def clear_context(self, workflow_id: str):
        """Clear all context for workflow"""
        if workflow_id in self.context_store:
            del self.context_store[workflow_id]
    
    def add_conversation_entry(self, workflow_id: str, agent: str, action: str, result: Any):
        """Add entry to conversation history"""
        entry = {
            "timestamp": datetime.now(),
            "agent": agent,
            "action": action,
            "result": result,
            "workflow_id": workflow_id
        }
        
        context_key = "conversation_history"
        history = self.retrieve_context(workflow_id, context_key) or []
        history.append(entry)
        self.store_context(workflow_id, context_key, history)


# Global instances
state_manager = StateManager()
context_manager = ContextManager()
state_validator = StateValidator() 