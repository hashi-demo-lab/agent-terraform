"""
LangGraph Platform Configuration
Core platform setup for Terraform Code Generation Agent
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from langgraph.platform import LangGraphPlatform
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresCheckpointSaver
from langgraph.checkpoint.redis import RedisCheckpointSaver


class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    LOCAL = "local"


class CheckpointerType(Enum):
    """Available checkpointer types"""
    MEMORY = "memory"
    POSTGRES = "postgres"
    REDIS = "redis"


@dataclass
class PlatformConfig:
    """LangGraph Platform configuration"""
    environment: Environment
    checkpointer_type: CheckpointerType
    thread_management: bool = True
    state_persistence: bool = True
    max_concurrent_workflows: int = 10
    workflow_timeout: int = 3600  # seconds
    
    # Database configurations
    postgres_connection_string: Optional[str] = None
    redis_connection_string: Optional[str] = None
    
    # Performance settings
    enable_metrics: bool = True
    enable_tracing: bool = True
    log_level: str = "INFO"
    
    # Security settings
    enable_auth: bool = False
    api_key: Optional[str] = None


class LangGraphPlatformManager:
    """
    Manages LangGraph Platform initialization and configuration
    """
    
    def __init__(self, config: PlatformConfig):
        self.config = config
        self.platform = LangGraphPlatform()
        self.checkpointer = self._create_checkpointer()
    
    def _create_checkpointer(self):
        """Create appropriate checkpointer based on configuration"""
        
        if self.config.checkpointer_type == CheckpointerType.MEMORY:
            return MemorySaver()
        
        elif self.config.checkpointer_type == CheckpointerType.POSTGRES:
            if not self.config.postgres_connection_string:
                raise ValueError("PostgreSQL connection string required for postgres checkpointer")
            
            return PostgresCheckpointSaver(
                connection_string=self.config.postgres_connection_string
            )
        
        elif self.config.checkpointer_type == CheckpointerType.REDIS:
            if not self.config.redis_connection_string:
                raise ValueError("Redis connection string required for redis checkpointer")
            
            return RedisCheckpointSaver(
                connection_string=self.config.redis_connection_string
            )
        
        else:
            raise ValueError(f"Unsupported checkpointer type: {self.config.checkpointer_type}")
    
    def get_platform_config(self) -> Dict[str, Any]:
        """Get platform configuration dictionary"""
        return {
            "platform": self.platform,
            "checkpointer": self.checkpointer,
            "thread_management": self.config.thread_management,
            "state_persistence": self.config.state_persistence,
            "max_concurrent_workflows": self.config.max_concurrent_workflows,
            "workflow_timeout": self.config.workflow_timeout,
            "environment": self.config.environment.value,
            "metrics_enabled": self.config.enable_metrics,
            "tracing_enabled": self.config.enable_tracing
        }
    
    def initialize_platform(self) -> Dict[str, Any]:
        """Initialize the LangGraph Platform with configuration"""
        
        # Set up logging
        import logging
        logging.basicConfig(level=getattr(logging, self.config.log_level))
        
        # Initialize platform components
        platform_config = self.get_platform_config()
        
        # Set up metrics if enabled
        if self.config.enable_metrics:
            self._setup_metrics()
        
        # Set up tracing if enabled
        if self.config.enable_tracing:
            self._setup_tracing()
        
        return platform_config
    
    def _setup_metrics(self):
        """Set up metrics collection"""
        try:
            from prometheus_client import start_http_server, Counter, Histogram, Gauge
            
            # Start metrics server
            start_http_server(8000)
            
            # Define metrics
            self.workflow_counter = Counter(
                'terraform_workflows_total',
                'Total number of Terraform workflows executed',
                ['status', 'agent']
            )
            
            self.workflow_duration = Histogram(
                'terraform_workflow_duration_seconds',
                'Time spent executing Terraform workflows',
                ['agent']
            )
            
            self.active_workflows = Gauge(
                'terraform_active_workflows',
                'Number of currently active workflows'
            )
            
        except ImportError:
            print("Prometheus client not available, metrics disabled")
    
    def _setup_tracing(self):
        """Set up distributed tracing"""
        # Placeholder for tracing setup
        # Could integrate with OpenTelemetry, Jaeger, etc.
        pass


def create_platform_config(environment: str = None) -> PlatformConfig:
    """
    Create platform configuration from environment variables
    """
    
    # Determine environment
    env_name = environment or os.getenv("TERRAFORM_AGENT_ENV", "development")
    env = Environment(env_name.lower())
    
    # Determine checkpointer type
    checkpointer_name = os.getenv("CHECKPOINTER_TYPE", "memory")
    checkpointer_type = CheckpointerType(checkpointer_name.lower())
    
    # Create configuration
    config = PlatformConfig(
        environment=env,
        checkpointer_type=checkpointer_type,
        thread_management=os.getenv("THREAD_MANAGEMENT", "true").lower() == "true",
        state_persistence=os.getenv("STATE_PERSISTENCE", "true").lower() == "true",
        max_concurrent_workflows=int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "10")),
        workflow_timeout=int(os.getenv("WORKFLOW_TIMEOUT", "3600")),
        postgres_connection_string=os.getenv("POSTGRES_CONNECTION_STRING"),
        redis_connection_string=os.getenv("REDIS_CONNECTION_STRING"),
        enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
        enable_tracing=os.getenv("ENABLE_TRACING", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        enable_auth=os.getenv("ENABLE_AUTH", "false").lower() == "true",
        api_key=os.getenv("API_KEY")
    )
    
    return config


def get_default_platform_manager() -> LangGraphPlatformManager:
    """Get default platform manager with environment-based configuration"""
    config = create_platform_config()
    return LangGraphPlatformManager(config)


# Global platform manager instance
platform_manager = get_default_platform_manager() 