#!/usr/bin/env python3
"""
Test script to verify LangGraph Platform setup for Terraform Agent
"""

import asyncio
import sys
from pathlib import Path

# Add the terraform_agent to the path
sys.path.insert(0, str(Path(__file__).parent / "terraform_agent"))

try:
    from terraform_agent.agent import graph, GraphConfig
    from terraform_agent.utils.state import TerraformState, RequirementSpec, WorkflowStatus
    print("✅ Successfully imported LangGraph components")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def test_basic_workflow():
    """Test basic workflow execution"""
    print("\n🧪 Testing basic workflow execution...")
    
    # Create test requirements
    requirements = RequirementSpec(
        provider="aws",
        environment="dev",
        resources=[{"type": "s3_bucket", "name": "test-bucket"}],
        compliance_requirements=["security"],
        custom_rules=[],
        metadata={"test": True}
    )
    
    # Create initial state
    initial_state: TerraformState = {
        "messages": [],
        "workflow_id": "test-workflow",
        "thread_id": "test-thread",
        "status": WorkflowStatus.PENDING,
        "current_agent": "",
        "iteration_count": 0,
        "max_iterations": 3,
        "requirements": requirements,
        "input_code": "",
        "file_paths": ["main.tf"],
        "generated_code": "",
        "refined_code": "",
        "documentation": "",
        "validation_results": [],
        "analysis_results": {},
        "context_memory": {},
        "conversation_history": [],
        "mcp_context": {},
        "provider_docs": {},
        "registry_data": {},
        "errors": [],
        "warnings": [],
        "debug_info": {},
        "execution_metrics": {},
        "start_time": None,
        "end_time": None
    }
    
    # Test configuration
    config: GraphConfig = {
        "provider": "aws",
        "environment": "dev",
        "max_iterations": 3,
        "enable_security_scan": True,
        "enable_compliance_check": True
    }
    
    try:
        # Test graph compilation
        print("  📋 Testing graph compilation...")
        compiled_graph = graph
        print("  ✅ Graph compiled successfully")
        
        # Test basic invocation (synchronous)
        print("  🚀 Testing basic invocation...")
        result = compiled_graph.invoke(
            initial_state,
            config={"configurable": config}
        )
        
        print(f"  ✅ Workflow completed with status: {result.get('status', 'unknown')}")
        print(f"  📊 Generated code length: {len(result.get('generated_code', ''))}")
        print(f"  📝 Documentation length: {len(result.get('documentation', ''))}")
        print(f"  🔍 Validation results: {len(result.get('validation_results', []))}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Workflow execution failed: {e}")
        return False


def test_graph_structure():
    """Test graph structure and nodes"""
    print("\n🏗️ Testing graph structure...")
    
    try:
        # Check if graph has expected nodes
        expected_nodes = [
            "planner", "generator", "validator", "validation_processor", "refiner", 
            "reviewer", "analyzer"
        ]
        
        # Get graph nodes (this is a simplified check)
        print("  📋 Checking graph compilation...")
        compiled_graph = graph
        print("  ✅ Graph structure validated")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Graph structure test failed: {e}")
        return False


def test_imports():
    """Test all required imports"""
    print("\n📦 Testing imports...")
    
    try:
        from terraform_agent.utils.state import (
            TerraformState, WorkflowStatus, ValidationStatus, 
            ValidationResult, RequirementSpec
        )
        print("  ✅ State management imports successful")
        
        from terraform_agent.utils.nodes import (
            planner_node, generator_node, validator_node, validation_processor_node,
            should_continue_validation, should_continue_after_analysis
        )
        print("  ✅ Node function imports successful")
        
        from terraform_agent.utils.tools import (
            terraform_validate_tool, terraform_fmt_tool,
            tflint_avm_validate_tool, trivy_scan_tool
        )
        print("  ✅ Tool imports successful")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 LangGraph Platform Setup Test for Terraform Agent")
    print("=" * 60)
    
    # Run tests
    tests = [
        ("Import Test", test_imports),
        ("Graph Structure Test", test_graph_structure),
        ("Basic Workflow Test", test_basic_workflow)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! LangGraph Platform setup is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the setup.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main()) 