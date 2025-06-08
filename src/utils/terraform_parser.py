"""
Terraform HCL Parser Utility
Parses Terraform configuration files and extracts resource information
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

try:
    import python_hcl2 as hcl2
except ImportError:
    # Fallback parser implementation
    hcl2 = None


@dataclass
class TerraformResource:
    """Represents a parsed Terraform resource"""
    type: str
    name: str
    config: Dict[str, Any]
    file_path: str
    line_number: int


@dataclass
class TerraformVariable:
    """Represents a Terraform variable"""
    name: str
    type: str
    description: str
    default: Any
    validation: List[Dict[str, Any]]
    file_path: str
    line_number: int


@dataclass
class TerraformOutput:
    """Represents a Terraform output"""
    name: str
    value: Any
    description: str
    sensitive: bool
    file_path: str
    line_number: int


@dataclass
class ParsedTerraform:
    """Complete parsed Terraform configuration"""
    resources: List[TerraformResource]
    variables: List[TerraformVariable]
    outputs: List[TerraformOutput]
    locals: Dict[str, Any]
    providers: Dict[str, Any]
    terraform_config: Dict[str, Any]
    raw_data: Dict[str, Any]


class TerraformParser:
    """
    Terraform HCL parser with fallback implementation
    """
    
    def __init__(self):
        self.use_hcl2 = hcl2 is not None
    
    def parse_file(self, file_path: str) -> ParsedTerraform:
        """Parse a single Terraform file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            return self.parse_hcl(content, file_path)
            
        except Exception as e:
            raise ValueError(f"Failed to parse Terraform file {file_path}: {e}")
    
    def parse_directory(self, directory_path: str) -> ParsedTerraform:
        """Parse all Terraform files in a directory"""
        directory = Path(directory_path)
        terraform_files = list(directory.glob("*.tf"))
        
        if not terraform_files:
            raise ValueError(f"No Terraform files found in {directory_path}")
        
        # Parse all files and merge results
        all_resources = []
        all_variables = []
        all_outputs = []
        all_locals = {}
        all_providers = {}
        terraform_config = {}
        raw_data = {}
        
        for tf_file in terraform_files:
            parsed = self.parse_file(str(tf_file))
            
            all_resources.extend(parsed.resources)
            all_variables.extend(parsed.variables)
            all_outputs.extend(parsed.outputs)
            all_locals.update(parsed.locals)
            all_providers.update(parsed.providers)
            terraform_config.update(parsed.terraform_config)
            raw_data[str(tf_file)] = parsed.raw_data
        
        return ParsedTerraform(
            resources=all_resources,
            variables=all_variables,
            outputs=all_outputs,
            locals=all_locals,
            providers=all_providers,
            terraform_config=terraform_config,
            raw_data=raw_data
        )
    
    def parse_hcl(self, content: str, file_path: str = "main.tf") -> ParsedTerraform:
        """Parse HCL content"""
        if self.use_hcl2:
            return self._parse_with_hcl2(content, file_path)
        else:
            return self._parse_with_regex(content, file_path)
    
    def _parse_with_hcl2(self, content: str, file_path: str) -> ParsedTerraform:
        """Parse using python-hcl2 library"""
        try:
            parsed_data = hcl2.loads(content)
            return self._extract_terraform_elements(parsed_data, file_path, content)
            
        except Exception as e:
            # Fallback to regex parser
            print(f"HCL2 parsing failed, falling back to regex parser: {e}")
            return self._parse_with_regex(content, file_path)
    
    def _parse_with_regex(self, content: str, file_path: str) -> ParsedTerraform:
        """Fallback regex-based parser"""
        
        # Remove comments
        content_no_comments = self._remove_comments(content)
        
        # Parse different sections
        resources = self._parse_resources_regex(content_no_comments, file_path)
        variables = self._parse_variables_regex(content_no_comments, file_path)
        outputs = self._parse_outputs_regex(content_no_comments, file_path)
        locals_dict = self._parse_locals_regex(content_no_comments, file_path)
        providers = self._parse_providers_regex(content_no_comments, file_path)
        terraform_config = self._parse_terraform_config_regex(content_no_comments, file_path)
        
        return ParsedTerraform(
            resources=resources,
            variables=variables,
            outputs=outputs,
            locals=locals_dict,
            providers=providers,
            terraform_config=terraform_config,
            raw_data={"content": content}
        )
    
    def _extract_terraform_elements(self, parsed_data: Dict[str, Any], file_path: str, content: str) -> ParsedTerraform:
        """Extract Terraform elements from parsed HCL data"""
        
        resources = []
        variables = []
        outputs = []
        locals_dict = {}
        providers = {}
        terraform_config = {}
        
        # Extract resources
        if "resource" in parsed_data:
            for resource_type, resource_instances in parsed_data["resource"].items():
                for resource_name, resource_config in resource_instances.items():
                    line_number = self._find_line_number(content, f'resource "{resource_type}" "{resource_name}"')
                    
                    resources.append(TerraformResource(
                        type=resource_type,
                        name=resource_name,
                        config=resource_config,
                        file_path=file_path,
                        line_number=line_number
                    ))
        
        # Extract variables
        if "variable" in parsed_data:
            for var_name, var_config in parsed_data["variable"].items():
                line_number = self._find_line_number(content, f'variable "{var_name}"')
                
                variables.append(TerraformVariable(
                    name=var_name,
                    type=var_config.get("type", "string"),
                    description=var_config.get("description", ""),
                    default=var_config.get("default"),
                    validation=var_config.get("validation", []),
                    file_path=file_path,
                    line_number=line_number
                ))
        
        # Extract outputs
        if "output" in parsed_data:
            for output_name, output_config in parsed_data["output"].items():
                line_number = self._find_line_number(content, f'output "{output_name}"')
                
                outputs.append(TerraformOutput(
                    name=output_name,
                    value=output_config.get("value"),
                    description=output_config.get("description", ""),
                    sensitive=output_config.get("sensitive", False),
                    file_path=file_path,
                    line_number=line_number
                ))
        
        # Extract locals
        if "locals" in parsed_data:
            locals_dict = parsed_data["locals"]
        
        # Extract providers
        if "terraform" in parsed_data and "required_providers" in parsed_data["terraform"]:
            providers = parsed_data["terraform"]["required_providers"]
        
        # Extract terraform configuration
        if "terraform" in parsed_data:
            terraform_config = parsed_data["terraform"]
        
        return ParsedTerraform(
            resources=resources,
            variables=variables,
            outputs=outputs,
            locals=locals_dict,
            providers=providers,
            terraform_config=terraform_config,
            raw_data=parsed_data
        )
    
    def _remove_comments(self, content: str) -> str:
        """Remove comments from HCL content"""
        # Remove single-line comments
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        return content
    
    def _parse_resources_regex(self, content: str, file_path: str) -> List[TerraformResource]:
        """Parse resources using regex"""
        resources = []
        
        # Pattern to match resource blocks
        resource_pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        
        for match in re.finditer(resource_pattern, content, re.DOTALL):
            resource_type = match.group(1)
            resource_name = match.group(2)
            resource_body = match.group(3)
            
            # Parse resource configuration
            config = self._parse_block_content(resource_body)
            
            line_number = content[:match.start()].count('\n') + 1
            
            resources.append(TerraformResource(
                type=resource_type,
                name=resource_name,
                config=config,
                file_path=file_path,
                line_number=line_number
            ))
        
        return resources
    
    def _parse_variables_regex(self, content: str, file_path: str) -> List[TerraformVariable]:
        """Parse variables using regex"""
        variables = []
        
        # Pattern to match variable blocks
        variable_pattern = r'variable\s+"([^"]+)"\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        
        for match in re.finditer(variable_pattern, content, re.DOTALL):
            var_name = match.group(1)
            var_body = match.group(2)
            
            # Parse variable configuration
            config = self._parse_block_content(var_body)
            
            line_number = content[:match.start()].count('\n') + 1
            
            variables.append(TerraformVariable(
                name=var_name,
                type=config.get("type", "string"),
                description=config.get("description", ""),
                default=config.get("default"),
                validation=config.get("validation", []),
                file_path=file_path,
                line_number=line_number
            ))
        
        return variables
    
    def _parse_outputs_regex(self, content: str, file_path: str) -> List[TerraformOutput]:
        """Parse outputs using regex"""
        outputs = []
        
        # Pattern to match output blocks
        output_pattern = r'output\s+"([^"]+)"\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        
        for match in re.finditer(output_pattern, content, re.DOTALL):
            output_name = match.group(1)
            output_body = match.group(2)
            
            # Parse output configuration
            config = self._parse_block_content(output_body)
            
            line_number = content[:match.start()].count('\n') + 1
            
            outputs.append(TerraformOutput(
                name=output_name,
                value=config.get("value"),
                description=config.get("description", ""),
                sensitive=config.get("sensitive", False),
                file_path=file_path,
                line_number=line_number
            ))
        
        return outputs
    
    def _parse_locals_regex(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse locals using regex"""
        locals_dict = {}
        
        # Pattern to match locals blocks
        locals_pattern = r'locals\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        
        for match in re.finditer(locals_pattern, content, re.DOTALL):
            locals_body = match.group(1)
            locals_config = self._parse_block_content(locals_body)
            locals_dict.update(locals_config)
        
        return locals_dict
    
    def _parse_providers_regex(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse provider configurations using regex"""
        providers = {}
        
        # Pattern to match terraform required_providers block
        terraform_pattern = r'terraform\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        
        for match in re.finditer(terraform_pattern, content, re.DOTALL):
            terraform_body = match.group(1)
            
            # Look for required_providers within terraform block
            providers_pattern = r'required_providers\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
            providers_match = re.search(providers_pattern, terraform_body, re.DOTALL)
            
            if providers_match:
                providers_body = providers_match.group(1)
                providers = self._parse_block_content(providers_body)
        
        return providers
    
    def _parse_terraform_config_regex(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse terraform configuration using regex"""
        terraform_config = {}
        
        # Pattern to match terraform blocks
        terraform_pattern = r'terraform\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        
        for match in re.finditer(terraform_pattern, content, re.DOTALL):
            terraform_body = match.group(1)
            config = self._parse_block_content(terraform_body)
            terraform_config.update(config)
        
        return terraform_config
    
    def _parse_block_content(self, content: str) -> Dict[str, Any]:
        """Parse the content of a block (simplified implementation)"""
        config = {}
        
        # Simple key-value parsing
        # This is a simplified implementation - a full parser would handle nested blocks, lists, etc.
        
        # Pattern for simple key = value assignments
        kv_pattern = r'(\w+)\s*=\s*([^=\n]+)'
        
        for match in re.finditer(kv_pattern, content):
            key = match.group(1).strip()
            value = match.group(2).strip()
            
            # Clean up the value
            value = value.rstrip(',').strip()
            
            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            
            # Try to convert to appropriate type
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            elif value.isdigit():
                value = int(value)
            elif value.replace('.', '').isdigit():
                value = float(value)
            
            config[key] = value
        
        return config
    
    def _find_line_number(self, content: str, search_string: str) -> int:
        """Find the line number of a string in content"""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if search_string in line:
                return i + 1
        return 0
    
    def get_resource_dependencies(self, parsed: ParsedTerraform) -> Dict[str, List[str]]:
        """Extract resource dependencies"""
        dependencies = {}
        
        for resource in parsed.resources:
            resource_key = f"{resource.type}.{resource.name}"
            dependencies[resource_key] = []
            
            # Look for references to other resources in the configuration
            config_str = json.dumps(resource.config)
            
            # Find references like aws_instance.example or var.example
            ref_pattern = r'(\w+\.\w+)'
            refs = re.findall(ref_pattern, config_str)
            
            for ref in refs:
                if ref != resource_key and not ref.startswith('var.'):
                    dependencies[resource_key].append(ref)
        
        return dependencies
    
    def validate_syntax(self, content: str) -> Tuple[bool, List[str]]:
        """Basic syntax validation"""
        errors = []
        
        # Check for balanced braces
        open_braces = content.count('{')
        close_braces = content.count('}')
        
        if open_braces != close_braces:
            errors.append(f"Unbalanced braces: {open_braces} opening, {close_braces} closing")
        
        # Check for balanced quotes
        quote_count = content.count('"')
        if quote_count % 2 != 0:
            errors.append("Unbalanced quotes")
        
        # Check for basic block structure
        required_blocks = ['resource', 'variable', 'output', 'terraform']
        has_terraform_content = any(block in content for block in required_blocks)
        
        if not has_terraform_content:
            errors.append("No recognizable Terraform blocks found")
        
        return len(errors) == 0, errors
    
    def extract_provider_requirements(self, parsed: ParsedTerraform) -> Dict[str, str]:
        """Extract provider version requirements"""
        requirements = {}
        
        # From terraform configuration
        if parsed.terraform_config.get("required_providers"):
            for provider, config in parsed.terraform_config["required_providers"].items():
                if isinstance(config, dict) and "version" in config:
                    requirements[provider] = config["version"]
                elif isinstance(config, str):
                    requirements[provider] = config
        
        # Infer from resource types
        for resource in parsed.resources:
            provider = resource.type.split('_')[0]
            if provider not in requirements:
                requirements[provider] = "~> 1.0"  # Default version constraint
        
        return requirements 