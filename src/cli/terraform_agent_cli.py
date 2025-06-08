"""
Terraform Code Generation Agent CLI
Following .cursorrules specifications
"""

import asyncio
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
import structlog

from ..workflows.terraform_workflow import terraform_workflow
from ..workflows.state_management import RequirementSpec

console = Console()
logger = structlog.get_logger()


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config', '-c', type=click.Path(exists=True), help='Configuration file path')
def terraform_agent(verbose: bool, config: Optional[str]):
    """Terraform Code Generation Agent CLI"""
    
    # Configure logging
    log_level = "DEBUG" if verbose else "INFO"
    structlog.configure(
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    if config:
        console.print(f"[green]Using configuration file: {config}[/green]")


@terraform_agent.command()
@click.option('--requirements', '-r', type=click.Path(exists=True), 
              help='Requirements file path (YAML or JSON)')
@click.option('--provider', '-p', default='aws', 
              type=click.Choice(['aws', 'azurerm', 'google', 'kubernetes']),
              help='Cloud provider')
@click.option('--environment', '-e', default='dev',
              type=click.Choice(['dev', 'staging', 'prod']),
              help='Environment name')
@click.option('--output', '-o', type=click.Path(), 
              help='Output directory for generated files')
@click.option('--input-code', type=click.Path(exists=True),
              help='Existing Terraform code to refine')
@click.option('--compliance', multiple=True,
              help='Compliance requirements (can be specified multiple times)')
@click.option('--interactive', '-i', is_flag=True,
              help='Interactive mode for requirements gathering')
def generate(requirements: Optional[str], 
            provider: str,
            environment: str, 
            output: Optional[str],
            input_code: Optional[str],
            compliance: tuple,
            interactive: bool):
    """Generate Terraform module from requirements"""
    
    console.print(Panel.fit(
        "[bold blue]Terraform Code Generation Agent[/bold blue]\n"
        "Generating infrastructure code with best practices",
        border_style="blue"
    ))
    
    try:
        # Load requirements
        if interactive:
            req_dict = _interactive_requirements_gathering(provider, environment)
        elif requirements:
            req_dict = _load_requirements_file(requirements)
        else:
            # Use minimal default requirements
            req_dict = {
                "provider": provider,
                "environment": environment,
                "resources": [{"type": "s3_bucket", "name": "example"}],
                "compliance_requirements": list(compliance)
            }
        
        # Load input code if provided
        input_terraform_code = ""
        if input_code:
            with open(input_code, 'r') as f:
                input_terraform_code = f.read()
            console.print(f"[green]Loaded existing code from: {input_code}[/green]")
        
        # Execute workflow
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Generating Terraform code...", total=None)
            
            result = asyncio.run(terraform_workflow.execute_workflow(
                requirements=req_dict,
                input_code=input_terraform_code
            ))
        
        if result["success"]:
            _display_generation_results(result)
            
            # Save files if output directory specified
            if output:
                _save_generated_files(result, output)
                console.print(f"\n[green]Files saved to: {output}[/green]")
        else:
            console.print(f"[red]Generation failed: {result.get('error', 'Unknown error')}[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.error("CLI generation failed", error=str(e))


@terraform_agent.command()
@click.argument('workflow_id')
def status(workflow_id: str):
    """Get workflow status"""
    
    try:
        result = asyncio.run(terraform_workflow.get_workflow_status(workflow_id))
        
        if "error" in result:
            console.print(f"[red]{result['error']}[/red]")
            return
        
        # Display status table
        table = Table(title=f"Workflow Status: {workflow_id}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Status", result["status"])
        table.add_row("Current Agent", result.get("current_agent", "N/A"))
        table.add_row("Iteration Count", str(result.get("iteration_count", 0)))
        
        if result.get("errors"):
            table.add_row("Errors", str(len(result["errors"])))
        
        if result.get("warnings"):
            table.add_row("Warnings", str(len(result["warnings"])))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error getting status: {str(e)}[/red]")


@terraform_agent.command()
@click.argument('workflow_id')
def cancel(workflow_id: str):
    """Cancel a running workflow"""
    
    try:
        result = asyncio.run(terraform_workflow.cancel_workflow(workflow_id))
        
        if "error" in result:
            console.print(f"[red]{result['error']}[/red]")
        else:
            console.print(f"[green]{result['message']}[/green]")
            
    except Exception as e:
        console.print(f"[red]Error cancelling workflow: {str(e)}[/red]")


@terraform_agent.command()
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
def list_workflows(format: str):
    """List active workflows"""
    
    try:
        from ..workflows.state_management import state_manager
        
        active_workflows = state_manager.get_active_workflows()
        
        if format == 'json':
            console.print(json.dumps(active_workflows, indent=2))
        else:
            if not active_workflows:
                console.print("[yellow]No active workflows[/yellow]")
                return
            
            table = Table(title="Active Workflows")
            table.add_column("Workflow ID", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Current Agent", style="yellow")
            
            for workflow_id in active_workflows:
                state = state_manager.get_state(workflow_id)
                if state:
                    table.add_row(
                        workflow_id,
                        state["status"].value if hasattr(state["status"], 'value') else str(state["status"]),
                        state.get("current_agent", "N/A")
                    )
            
            console.print(table)
            
    except Exception as e:
        console.print(f"[red]Error listing workflows: {str(e)}[/red]")


@terraform_agent.command()
@click.option('--provider', '-p', default='aws',
              type=click.Choice(['aws', 'azurerm', 'google', 'kubernetes']),
              help='Cloud provider to validate against')
@click.argument('terraform_file', type=click.Path(exists=True))
def validate(provider: str, terraform_file: str):
    """Validate existing Terraform code"""
    
    try:
        # Load Terraform code
        with open(terraform_file, 'r') as f:
            terraform_code = f.read()
        
        console.print(f"[blue]Validating Terraform code: {terraform_file}[/blue]")
        
        # Create minimal requirements for validation
        requirements = {
            "provider": provider,
            "environment": "dev",
            "resources": [],
            "compliance_requirements": ["security"]
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Running validation...", total=None)
            
            result = asyncio.run(terraform_workflow.execute_workflow(
                requirements=requirements,
                input_code=terraform_code
            ))
        
        # Display validation results
        _display_validation_results(result.get("validation_results", []))
        
    except Exception as e:
        console.print(f"[red]Validation error: {str(e)}[/red]")


@terraform_agent.command()
def init():
    """Initialize Terraform Agent configuration"""
    
    console.print("[blue]Initializing Terraform Agent...[/blue]")
    
    # Create default configuration
    config_dir = Path.home() / ".terraform-agent"
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "config.yaml"
    
    default_config = {
        "terraform": {
            "version": "1.12",
            "backend": "local"
        },
        "validation": {
            "max_iterations": 5,
            "fail_fast": False
        },
        "tools": {
            "tflint": {
                "enabled": True,
                "config_path": ".tflint.hcl"
            },
            "trivy": {
                "enabled": True,
                "severity": ["HIGH", "CRITICAL"]
            }
        },
        "langgraph_platform": {
            "checkpointer": "memory",
            "persistence": True,
            "thread_management": True
        }
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False)
    
    console.print(f"[green]Configuration initialized at: {config_file}[/green]")
    console.print("[yellow]Edit the configuration file to customize settings[/yellow]")


def _interactive_requirements_gathering(provider: str, environment: str) -> Dict[str, Any]:
    """Interactive requirements gathering"""
    
    console.print("[blue]Interactive Requirements Gathering[/blue]")
    
    project_name = click.prompt("Project name", default="my-project")
    
    resources = []
    console.print("\n[yellow]Add resources (press Enter with empty type to finish):[/yellow]")
    
    while True:
        resource_type = click.prompt("Resource type (e.g., s3_bucket, ec2_instance)", default="", show_default=False)
        if not resource_type:
            break
        
        resource_name = click.prompt("Resource name", default=f"{resource_type}_example")
        
        resources.append({
            "type": resource_type,
            "name": resource_name
        })
    
    if not resources:
        resources = [{"type": "s3_bucket", "name": "example"}]
    
    # Compliance requirements
    compliance_options = ["security", "reliability", "cost_optimization", "performance", "operational_excellence"]
    console.print(f"\n[yellow]Available compliance requirements: {', '.join(compliance_options)}[/yellow]")
    compliance_input = click.prompt("Compliance requirements (comma-separated)", default="security")
    compliance_requirements = [req.strip() for req in compliance_input.split(",") if req.strip()]
    
    return {
        "provider": provider,
        "environment": environment,
        "project_name": project_name,
        "resources": resources,
        "compliance_requirements": compliance_requirements
    }


def _load_requirements_file(file_path: str) -> Dict[str, Any]:
    """Load requirements from YAML or JSON file"""
    
    path = Path(file_path)
    
    with open(path, 'r') as f:
        if path.suffix.lower() in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif path.suffix.lower() == '.json':
            return json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")


def _display_generation_results(result: Dict[str, Any]):
    """Display generation results"""
    
    console.print("\n[green]✅ Generation Complete![/green]")
    
    # Summary table
    table = Table(title="Generation Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Workflow ID", result["workflow_id"])
    table.add_row("Status", result["status"])
    
    if result.get("execution_metrics"):
        metrics = result["execution_metrics"]
        if "total_execution_time" in metrics:
            table.add_row("Execution Time", f"{metrics['total_execution_time']:.2f}s")
    
    console.print(table)
    
    # Validation results
    if result.get("validation_results"):
        _display_validation_results(result["validation_results"])
    
    # Generated code preview
    if result.get("generated_code"):
        console.print("\n[blue]Generated Code Preview:[/blue]")
        syntax = Syntax(result["generated_code"][:1000] + "..." if len(result["generated_code"]) > 1000 else result["generated_code"], 
                       "hcl", theme="monokai", line_numbers=True)
        console.print(syntax)


def _display_validation_results(validation_results: list):
    """Display validation results"""
    
    if not validation_results:
        return
    
    console.print("\n[blue]Validation Results:[/blue]")
    
    table = Table()
    table.add_column("Tool", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Messages", style="yellow")
    table.add_column("Execution Time", style="magenta")
    
    for result in validation_results:
        status_color = "green" if result["passed"] else "red"
        status_text = f"[{status_color}]{result['status']}[/{status_color}]"
        
        messages = result.get("messages", [])
        errors = result.get("errors", [])
        all_messages = messages + errors
        
        table.add_row(
            result["tool"],
            status_text,
            "\n".join(all_messages[:3]) + ("..." if len(all_messages) > 3 else ""),
            f"{result.get('execution_time', 0):.2f}s"
        )
    
    console.print(table)


def _save_generated_files(result: Dict[str, Any], output_dir: str):
    """Save generated files to output directory"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    generated_module = result.get("generated_module")
    if not generated_module:
        console.print("[yellow]No generated module files to save[/yellow]")
        return
    
    # Save core Terraform files
    files_to_save = {
        "main.tf": generated_module.get("main_tf", ""),
        "variables.tf": generated_module.get("variables_tf", ""),
        "outputs.tf": generated_module.get("outputs_tf", ""),
        "providers.tf": generated_module.get("providers_tf", ""),
        "versions.tf": generated_module.get("versions_tf", ""),
        "locals.tf": generated_module.get("locals_tf", ""),
        "README.md": generated_module.get("readme_md", "")
    }
    
    for filename, content in files_to_save.items():
        if content:
            file_path = output_path / filename
            with open(file_path, 'w') as f:
                f.write(content)
            console.print(f"[green]Saved: {filename}[/green]")
    
    # Save examples
    examples = generated_module.get("examples", {})
    if examples:
        examples_dir = output_path / "examples"
        examples_dir.mkdir(exist_ok=True)
        
        for example_name, example_content in examples.items():
            example_file = examples_dir / f"{example_name}.tf"
            with open(example_file, 'w') as f:
                f.write(example_content)
            console.print(f"[green]Saved: examples/{example_name}.tf[/green]")


if __name__ == "__main__":
    terraform_agent() 