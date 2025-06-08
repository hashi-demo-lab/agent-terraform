#!/bin/bash

# Terraform Code Generation Agent - LangGraph Platform Setup Script
# This script sets up the complete environment for the Terraform Agent

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if command_exists python3; then
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
            print_success "Python $PYTHON_VERSION found"
            return 0
        else
            print_error "Python 3.11+ required, found $PYTHON_VERSION"
            return 1
        fi
    else
        print_error "Python 3 not found"
        return 1
    fi
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Install core LangGraph dependencies
    pip3 install --upgrade pip
    pip3 install typing_extensions
    
    # Install from terraform_agent requirements
    if [ -f "terraform_agent/requirements.txt" ]; then
        pip3 install -r terraform_agent/requirements.txt
        print_success "Terraform agent dependencies installed"
    else
        print_warning "terraform_agent/requirements.txt not found, installing core dependencies"
        pip3 install langgraph>=0.3.27 langgraph-sdk>=0.1.66 langgraph-checkpoint>=2.0.23
        pip3 install langchain-core>=0.2.38 langsmith>=0.1.63
        pip3 install langchain-anthropic langchain-openai langchain-community
        pip3 install pydantic>=2.0.0 python-dotenv>=1.0.0 structlog>=24.1.0
        pip install --upgrade "langgraph-cli[inmem]"
    fi
    
    # Install LangGraph CLI
    print_status "Installing LangGraph CLI..."
    pip3 install langgraph-cli
    
    print_success "All dependencies installed"
}

# Function to check Docker
check_docker() {
    if command_exists docker; then
        if docker info >/dev/null 2>&1; then
            print_success "Docker is running"
            return 0
        else
            print_warning "Docker is installed but not running"
            print_status "Please start Docker and run this script again"
            return 1
        fi
    else
        print_warning "Docker not found"
        print_status "Docker is required for LangGraph Platform deployment"
        print_status "Please install Docker from https://docker.com"
        return 1
    fi
}

# Function to setup environment file
setup_environment() {
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_status "Creating .env file from .env.example..."
            cp .env.example .env
            print_success ".env file created"
            print_warning "Please edit .env file with your API keys"
        else
            print_status "Creating basic .env file..."
            cat > .env << EOF
# Terraform Code Generation Agent Environment Variables
# LangSmith Configuration (required for LangGraph Platform)
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_PROJECT=terraform-agent

# OpenAI Configuration (for embeddings and LLM)
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic Configuration (alternative LLM)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Terraform Agent Configuration
TERRAFORM_AGENT_ENV=development
CHECKPOINTER_TYPE=memory
THREAD_MANAGEMENT=true
STATE_PERSISTENCE=true
MAX_CONCURRENT_WORKFLOWS=10
WORKFLOW_TIMEOUT=3600

# Monitoring and Logging
ENABLE_METRICS=true
ENABLE_TRACING=false
LOG_LEVEL=INFO
EOF
            print_success "Basic .env file created"
            print_warning "Please edit .env file with your actual API keys"
        fi
    else
        print_success ".env file already exists"
    fi
}

# Function to test the setup
test_setup() {
    print_status "Testing LangGraph Platform setup..."
    
    # Test basic imports
    python3 -c "
import sys
sys.path.insert(0, 'terraform_agent')

try:
    from terraform_agent.agent import graph, GraphConfig
    from terraform_agent.utils.state import TerraformState, RequirementSpec, WorkflowStatus
    print('✅ Successfully imported LangGraph components')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)

try:
    # Test graph compilation
    compiled_graph = graph
    print('✅ Graph compiled successfully')
except Exception as e:
    print(f'❌ Graph compilation failed: {e}')
    sys.exit(1)

print('🎉 LangGraph Platform setup test passed!')
"
    
    if [ $? -eq 0 ]; then
        print_success "Setup test passed!"
        return 0
    else
        print_error "Setup test failed!"
        return 1
    fi
}

# Function to run full test suite
run_full_test() {
    if [ -f "test_langgraph_setup.py" ]; then
        print_status "Running comprehensive test suite..."
        python3 test_langgraph_setup.py
    else
        print_warning "test_langgraph_setup.py not found, skipping comprehensive tests"
    fi
}

# Function to check LangGraph CLI
check_langgraph_cli() {
    if command_exists langgraph; then
        print_success "LangGraph CLI is available"
        langgraph --version
        return 0
    else
        print_error "LangGraph CLI not found in PATH"
        print_status "Try running: pip3 install langgraph-cli"
        return 1
    fi
}

# Function to validate langgraph.json
validate_config() {
    if [ -f "langgraph.json" ]; then
        print_status "Validating langgraph.json..."
        python3 -c "
import json
try:
    with open('langgraph.json', 'r') as f:
        config = json.load(f)
    
    required_keys = ['dependencies', 'graphs']
    for key in required_keys:
        if key not in config:
            print(f'❌ Missing required key: {key}')
            exit(1)
    
    print('✅ langgraph.json is valid')
except json.JSONDecodeError as e:
    print(f'❌ Invalid JSON in langgraph.json: {e}')
    exit(1)
except Exception as e:
    print(f'❌ Error validating langgraph.json: {e}')
    exit(1)
"
        if [ $? -eq 0 ]; then
            print_success "langgraph.json validation passed"
        else
            print_error "langgraph.json validation failed"
            return 1
        fi
    else
        print_error "langgraph.json not found"
        return 1
    fi
}

# Function to show next steps
show_next_steps() {
    echo ""
    print_success "🎉 Setup completed successfully!"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Edit .env file with your API keys:"
    echo "   - LANGSMITH_API_KEY (required for LangGraph Platform)"
    echo "   - OPENAI_API_KEY (for embeddings and LLM)"
    echo ""
    echo "2. Test the setup:"
    echo "   ./setup.sh --test"
    echo ""
    echo "3. Start development server:"
    echo "   langgraph dev"
    echo ""
    echo "4. Build for deployment:"
    echo "   langgraph build -t terraform-agent"
    echo ""
    echo "5. Deploy to LangGraph Platform:"
    echo "   langgraph up"
    echo ""
    echo -e "${BLUE}Documentation:${NC}"
    echo "- README: terraform_agent/README.md"
    echo "- Deployment Guide: DEPLOYMENT.md"
    echo "- LangGraph Platform Docs: https://langchain-ai.github.io/langgraph/"
    echo ""
}

# Main function
main() {
    echo "🚀 Terraform Code Generation Agent - LangGraph Platform Setup"
    echo "=============================================================="
    echo ""
    
    # Parse command line arguments
    case "${1:-}" in
        --test)
            print_status "Running tests only..."
            test_setup
            run_full_test
            exit $?
            ;;
        --validate)
            print_status "Validating configuration only..."
            validate_config
            exit $?
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --test      Run tests only"
            echo "  --validate  Validate configuration only"
            echo "  --help      Show this help message"
            echo ""
            exit 0
            ;;
    esac
    
    # Check prerequisites
    print_status "Checking prerequisites..."
    
    if ! check_python_version; then
        print_error "Python 3.11+ is required"
        exit 1
    fi
    
    # Check Docker (optional for development)
    check_docker || print_warning "Docker not available - deployment features will be limited"
    
    # Install dependencies
    install_dependencies
    
    # Setup environment
    setup_environment
    
    # Validate configuration
    validate_config
    
    # Check LangGraph CLI
    check_langgraph_cli
    
    # Test the setup
    if test_setup; then
        show_next_steps
    else
        print_error "Setup test failed. Please check the errors above."
        exit 1
    fi
}

# Run main function with all arguments
main "$@" 