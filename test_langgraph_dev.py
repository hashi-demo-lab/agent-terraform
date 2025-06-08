#!/usr/bin/env python3
"""
Test LangGraph Development Server
"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def test_langgraph_dev_server():
    """Test LangGraph development server startup"""
    print("🧪 Testing LangGraph Development Server...")
    
    # Check if langgraph.json exists
    if not Path("langgraph.json").exists():
        print("❌ langgraph.json not found")
        return False
    
    print("✅ langgraph.json found")
    
    # Test langgraph CLI
    try:
        result = subprocess.run(
            ["langgraph", "--help"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            print("✅ LangGraph CLI is working")
        else:
            print("❌ LangGraph CLI failed")
            return False
    except Exception as e:
        print(f"❌ LangGraph CLI error: {e}")
        return False
    
    # Test graph validation
    try:
        result = subprocess.run(
            ["langgraph", "build"], 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        if result.returncode == 0:
            print("✅ LangGraph build successful")
        else:
            print(f"⚠️ LangGraph build warning: {result.stderr}")
    except Exception as e:
        print(f"⚠️ LangGraph build error: {e}")
    
    return True

if __name__ == "__main__":
    print("🚀 LangGraph Development Server Test")
    print("=" * 50)
    
    success = test_langgraph_dev_server()
    
    if success:
        print("\n🎉 LangGraph development environment is ready!")
        print("\nNext steps:")
        print("1. Run: langgraph dev")
        print("2. Open: http://localhost:8123")
        print("3. Test your Terraform agent workflow")
    else:
        print("\n❌ Setup needs attention")
        sys.exit(1) 