# examples/simple_s3_example.py
"""
Simple S3 Example - Terraform Code Generation Agent
Demonstrates basic usage of the agent to generate an S3 bucket module
"""

import asyncio
import json
from pathlib import Path

# Add src to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.workflows.terraform_workflow import terraform_workflow


async def main():
    """
    Example: Generate a simple S3 bucket module
    """
    
    print("🚀 Terraform Code Generation Agent - Simple S3 Example")
    print("=" * 60)
    
    # Define requirements for a simple S3 bucket
    requirements = {
        "provider": "aws",
        "environment": "dev",
        "project_name": "example-project",
        "resources": [
            {
                "type": "s3_bucket",
                "name": "data_bucket",
                "configuration": {
                    "bucket": "example-project-data-bucket",
                    "tags": {
                        "Purpose": "Data Storage",
                        "Team": "Engineering"
                    }
                }
            }
        ],
        "compliance_requirements": ["security", "cost_optimization"],
        "metadata": {
            "description": "Simple S3 bucket for data storage",
            "owner": "engineering-team"
        }
    }
    
    print("📋 Requirements:")
    print(json.dumps(requirements, indent=2))
    print()
    
    try:
        # Execute the workflow
        print("🔄 Executing Terraform workflow...")
        result = await terraform_workflow.execute_workflow(requirements)
        
        if result["success"]:
            print("✅ Workflow completed successfully!")
            print()
            
            # Display results
            print("📊 Workflow Summary:")
            print(f"   • Workflow ID: {result['workflow_id']}")
            print(f"   • Status: {result['status']}")
            print(f"   • Thread ID: {result['thread_id']}")
            print()
            
            # Display validation results
            if result.get("validation_results"):
                print("🔍 Validation Results:")
                for validation in result["validation_results"]:
                    status_icon = "✅" if validation["passed"] else "❌"
                    print(f"   {status_icon} {validation['tool']}: {validation['status']}")
                    if validation.get("errors"):
                        for error in validation["errors"]:
                            print(f"      ❌ {error}")
                print()
            
            # Display generated code
            if result.get("generated_code"):
                print("📝 Generated Terraform Code:")
                print("-" * 40)
                print(result["generated_code"])
                print("-" * 40)
                print()
            
            # Save to files
            output_dir = Path("examples/generated_modules/simple_s3")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if result.get("generated_module"):
                module = result["generated_module"]
                
                # Save individual files
                files_to_save = {
                    "main.tf": module.get("main_tf"),
                    "variables.tf": module.get("variables_tf"),
                    "outputs.tf": module.get("outputs_tf"),
                    "providers.tf": module.get("providers_tf"),
                    "versions.tf": module.get("versions_tf"),
                    "locals.tf": module.get("locals_tf"),
                    "README.md": module.get("readme_md")
                }
                
                for filename, content in files_to_save.items():
                    if content:
                        file_path = output_dir / filename
                        with open(file_path, 'w') as f:
                            f.write(content)
                        print(f"💾 Saved: {file_path}")
                
                # Save examples
                examples = module.get("examples", {})
                if examples:
                    examples_dir = output_dir / "examples"
                    examples_dir.mkdir(exist_ok=True)
                    
                    for example_name, example_content in examples.items():
                        example_file = examples_dir / f"{example_name}.tf"
                        with open(example_file, 'w') as f:
                            f.write(example_content)
                        print(f"💾 Saved: {example_file}")
                
                print()
                print(f"📁 All files saved to: {output_dir}")
                print()
                print("🎉 Example completed successfully!")
                print()
                print("Next steps:")
                print("1. Review the generated files")
                print("2. Customize variables as needed")
                print("3. Run 'terraform init' in the output directory")
                print("4. Run 'terraform plan' to see what will be created")
            
        else:
            print("❌ Workflow failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            
            if result.get("errors"):
                print("\nDetailed errors:")
                for error in result["errors"]:
                    print(f"  • {error}")
    
    except Exception as e:
        print(f"❌ Example failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 