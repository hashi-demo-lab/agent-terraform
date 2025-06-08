# LangGraph Platform Deployment Guide

This guide covers deploying the Terraform Code Generation Agent to LangGraph Platform.

## Prerequisites

1. **LangGraph CLI**: Install the LangGraph CLI
   ```bash
   pip install langgraph-cli
   ```

2. **Docker**: Ensure Docker is installed and running
   ```bash
   docker --version
   ```

3. **Environment Variables**: Set up your `.env` file (copy from `.env.example`)

4. **API Keys**: Ensure you have the required API keys:
   - `LANGSMITH_API_KEY` (required for LangGraph Platform)
   - `OPENAI_API_KEY` (for embeddings and LLM)
   - `ANTHROPIC_API_KEY` (optional, for Claude models)

## Local Development

### 1. Test the Setup

First, verify your setup works locally:

```bash
# Run the test script
python test_langgraph_setup.py
```

### 2. Start Development Server

```bash
# Start the development server
langgraph dev

# With custom configuration
langgraph dev -c langgraph.json --port 2024
```

The development server will:
- Start on `http://localhost:2024`
- Enable hot reloading
- Provide debugging capabilities
- Open LangGraph Studio automatically

### 3. Test the API

```bash
# Create a new thread
curl -X POST "http://localhost:2024/threads" \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"provider": "aws", "environment": "dev"}}'

# Run the agent
curl -X POST "http://localhost:2024/threads/{thread_id}/runs" \
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

## Production Deployment

### 1. Build the Docker Image

```bash
# Build with default settings
langgraph build -t terraform-agent:latest

# Build for specific platform
langgraph build -t terraform-agent:latest --platform linux/amd64,linux/arm64

# Build without pulling latest base image (for local development)
langgraph build -t terraform-agent:latest --no-pull
```

### 2. Deploy to LangGraph Platform

```bash
# Deploy with default settings
langgraph up

# Deploy with custom port
langgraph up --port 8123

# Deploy with external database
langgraph up --postgres-uri "postgresql://user:pass@host:5432/db"

# Deploy and wait for services to be ready
langgraph up --wait
```

### 3. Production Configuration

For production deployments, update your `langgraph.json`:

```json
{
  "dependencies": ["./terraform_agent"],
  "graphs": {
    "terraform_agent": "./terraform_agent/agent.py:graph"
  },
  "env": ".env",
  "python_version": "3.11",
  "dockerfile_lines": [
    "RUN apt-get update && apt-get install -y curl unzip",
    "RUN curl -fsSL https://releases.hashicorp.com/terraform/1.12.0/terraform_1.12.0_linux_amd64.zip -o terraform.zip",
    "RUN unzip terraform.zip && mv terraform /usr/local/bin/ && rm terraform.zip",
    "RUN curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash",
    "RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin"
  ],
  "store": {
    "index": {
      "embed": "openai:text-embedding-3-small",
      "dims": 1536,
      "fields": ["$"]
    },
    "ttl": {
      "refresh_on_read": true,
      "sweep_interval_minutes": 60,
      "default_ttl": 10080
    }
  },
  "checkpointer": {
    "ttl": {
      "strategy": "delete",
      "sweep_interval_minutes": 10,
      "default_ttl": 43200
    }
  }
}
```

### 4. Environment Variables for Production

Create a production `.env` file:

```bash
# LangSmith Configuration
LANGSMITH_API_KEY=your_production_langsmith_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=terraform-agent-prod

# OpenAI Configuration
OPENAI_API_KEY=your_production_openai_key

# Database Configuration
POSTGRES_CONNECTION_STRING=postgresql://user:password@prod-db:5432/terraform_agent
REDIS_CONNECTION_STRING=redis://prod-redis:6379

# Agent Configuration
TERRAFORM_AGENT_ENV=production
CHECKPOINTER_TYPE=postgres
MAX_CONCURRENT_WORKFLOWS=50
WORKFLOW_TIMEOUT=7200

# Monitoring
ENABLE_METRICS=true
ENABLE_TRACING=true
LOG_LEVEL=INFO

# Security
ENABLE_AUTH=true
API_KEY=your_secure_api_key
```

## Scaling and Performance

### 1. Horizontal Scaling

LangGraph Platform supports horizontal scaling:

```bash
# Scale to multiple instances
langgraph up --replicas 3

# Auto-scaling configuration in langgraph.json
{
  "scaling": {
    "min_instances": 2,
    "max_instances": 10,
    "target_cpu_utilization": 70
  }
}
```

### 2. Database Optimization

For high-throughput deployments:

```json
{
  "checkpointer": {
    "connection_pool_size": 20,
    "max_overflow": 30,
    "ttl": {
      "strategy": "delete",
      "sweep_interval_minutes": 5,
      "default_ttl": 43200
    }
  }
}
```

### 3. Memory and Storage

Configure memory and storage limits:

```json
{
  "resources": {
    "memory": "4Gi",
    "cpu": "2",
    "storage": "10Gi"
  }
}
```

## Monitoring and Observability

### 1. Health Checks

LangGraph Platform provides built-in health checks:

```bash
# Check service health
curl http://localhost:8123/ok

# Get service info
curl http://localhost:8123/info

# Prometheus metrics
curl http://localhost:8123/metrics
```

### 2. Logging

Configure structured logging:

```bash
# View logs
langgraph logs

# Follow logs in real-time
langgraph logs --follow

# Filter logs by level
langgraph logs --level ERROR
```

### 3. Debugging

Enable debugging for troubleshooting:

```bash
# Start with debugger
langgraph dev --debug-port 5678 --wait-for-client

# Enable verbose logging
langgraph up --verbose
```

## Security

### 1. Authentication

Enable authentication in production:

```json
{
  "auth": {
    "path": "./auth.py:auth",
    "openapi": {
      "securitySchemes": {
        "apiKeyAuth": {
          "type": "apiKey",
          "in": "header",
          "name": "X-API-Key"
        }
      },
      "security": [{"apiKeyAuth": []}]
    }
  }
}
```

### 2. Network Security

- Use HTTPS in production
- Configure proper firewall rules
- Implement rate limiting
- Use secure database connections

### 3. Secret Management

- Use environment variables for secrets
- Consider using secret management services
- Rotate API keys regularly
- Audit access logs

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Check Python path and dependencies
   python test_langgraph_setup.py
   ```

2. **Docker Build Failures**
   ```bash
   # Check dockerfile_lines in langgraph.json
   langgraph dockerfile Dockerfile
   docker build -t test .
   ```

3. **Database Connection Issues**
   ```bash
   # Test database connectivity
   psql $POSTGRES_CONNECTION_STRING -c "SELECT 1;"
   ```

4. **Memory Issues**
   ```bash
   # Monitor memory usage
   docker stats
   # Adjust memory limits in configuration
   ```

### Debug Mode

Enable comprehensive debugging:

```bash
# Start with full debugging
langgraph dev \
  --debug-port 5678 \
  --wait-for-client \
  --verbose \
  --no-browser
```

### Performance Profiling

Monitor performance metrics:

```bash
# Check execution times
curl http://localhost:8123/metrics | grep terraform_workflow_duration

# Monitor active workflows
curl http://localhost:8123/metrics | grep terraform_active_workflows
```

## Backup and Recovery

### 1. Database Backups

```bash
# Backup PostgreSQL database
pg_dump $POSTGRES_CONNECTION_STRING > backup.sql

# Restore from backup
psql $POSTGRES_CONNECTION_STRING < backup.sql
```

### 2. Configuration Backups

- Version control `langgraph.json`
- Backup environment configurations
- Document deployment procedures

### 3. Disaster Recovery

- Implement multi-region deployments
- Regular backup testing
- Automated failover procedures

## Next Steps

1. **Custom Authentication**: Implement custom auth handlers
2. **Custom Tools**: Add domain-specific validation tools
3. **Monitoring**: Set up comprehensive monitoring dashboards
4. **CI/CD**: Integrate with your deployment pipeline
5. **Testing**: Implement comprehensive test suites 