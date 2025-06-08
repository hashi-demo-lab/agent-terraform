# Terraform Code Generation Agent

A LangGraph Platform compatible agent for generating, validating, and refining Terraform infrastructure code.

## Overview

This agent uses LangGraph Platform to orchestrate a multi-agent workflow that:

1. **Plans** infrastructure based on requirements
2. **Generates** Terraform code following best practices
3. **Validates** code using multiple tools (terraform validate, tflint, trivy)
4. **Refines** code based on validation feedback
5. **Analyzes** code for security and compliance
6. **Documents** the generated infrastructure
7. **Reviews** the final output for quality assurance

## Features

- **Multi-Agent Workflow**: Specialized agents for each phase of code generation
- **Validation Pipeline**: Integrated terraform, tflint (AVM), and trivy security scanning
- **Iterative Refinement**: Automatic code improvement based on validation feedback
- **Security-First**: Built-in security scanning and compliance checking
- **Documentation Generation**: Automatic README and documentation creation
- **LangGraph Platform Ready**: Fully compatible with LangGraph Platform deployment

## Quick Start

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (copy from .env.example):
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Run with LangGraph CLI:
```bash
langgraph dev
```

### LangGraph Platform Deployment

1. Build the Docker image:
```bash
langgraph build -t terraform-agent
```

2. Deploy to LangGraph Platform:
```bash
langgraph up
```

## Configuration

The agent is configured via `langgraph.json` with the following key settings:

- **Graph Definition**: `./terraform_agent/agent.py:graph`
- **Dependencies**: Automatically installs from `requirements.txt`
- **Tools**: Includes terraform, tflint, and trivy in the Docker image
- **Store**: Semantic search enabled for context management
- **Checkpointing**: Persistent state management

## Usage

### Basic Usage

```python
from terraform_agent.agent import graph

# Configure the graph
config = {
    "configurable": {
        "provider": "aws",
        "environment": "dev",
        "max_iterations": 5,
        "enable_security_scan": True,
        "enable_compliance_check": True
    }
}

# Run the workflow
result = graph.invoke({
    "messages": [],
    "requirements": {
        "provider": "aws",
        "environment": "dev",
        "resources": [{"type": "s3_bucket", "name": "example"}]
    }
}, config)
```

### API Usage (LangGraph Platform)

```bash
# Create a new thread
curl -X POST "http://localhost:8123/threads" \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"provider": "aws", "environment": "dev"}}'

# Run the agent
curl -X POST "http://localhost:8123/threads/{thread_id}/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "terraform_agent",
    "input": {
      "requirements": {
        "provider": "aws",
        "environment": "dev",
        "resources": [{"type": "s3_bucket", "name": "example"}]
      }
    }
  }'
```

## Architecture

### Workflow Nodes

1. **Planner**: Analyzes requirements and creates execution plan
2. **Generator**: Generates Terraform code based on requirements
3. **Validator**: Runs validation tools (terraform, tflint, trivy)
4. **Refiner**: Improves code based on validation feedback
5. **Analyzer**: Performs deep analysis for security and compliance
6. **Documenter**: Generates documentation and README files
7. **Reviewer**: Final quality assurance and review

### State Management

The agent uses a comprehensive state structure that includes:

- Workflow metadata and status
- Generated Terraform code
- Validation results
- Analysis findings
- Context memory for multi-turn conversations
- Performance metrics

### Tool Integration

- **Terraform CLI**: Syntax validation and formatting
- **TFLint with AVM**: Azure Verified Modules best practices
- **Trivy**: Security vulnerability scanning
- **Custom Tools**: Additional validation and analysis

## Best Practices

The agent follows these best practices:

- **HashiCorp Module Structure**: Standard file organization
- **Azure Verified Modules**: Generic best practices for all providers
- **Security-First Approach**: Encryption, access controls, and scanning
- **Comprehensive Validation**: Multiple validation layers
- **Documentation**: Auto-generated docs with examples

## Development

### Adding New Agents

1. Create agent function in `utils/nodes.py`
2. Add to workflow in `agent.py`
3. Update state management if needed

### Adding New Tools

1. Define tool in `utils/tools.py` using `@tool` decorator
2. Add to validation pipeline
3. Update tool node configuration

### Testing

```bash
# Run tests
pytest tests/

# Run with specific provider
pytest tests/ -k "aws"
```

## Troubleshooting

### Common Issues

1. **Missing API Keys**: Ensure all required API keys are set in `.env`
2. **Docker Build Fails**: Check dockerfile_lines in `langgraph.json`
3. **Validation Errors**: Review tool configurations and dependencies
4. **Memory Issues**: Adjust checkpointer settings for large workflows

### Debugging

Enable debug mode:
```bash
langgraph dev --debug-port 5678 --wait-for-client
```

## Contributing

1. Follow the coding standards in `.cursorrules`
2. Add tests for new functionality
3. Update documentation
4. Ensure LangGraph Platform compatibility

## License

MIT License - see LICENSE file for details. 