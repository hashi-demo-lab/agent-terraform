"""
Analysis Rules Engine - Defines Well-Architected Framework inspired rules
for analyzing Terraform code across multiple categories
"""

from typing import Dict, List, Any
from enum import Enum
import yaml
import json


class AnalysisCategory(Enum):
    """Analysis categories inspired by Well-Architected Framework"""
    SECURITY = "security"
    RELIABILITY = "reliability"
    PERFORMANCE = "performance"
    COST_OPTIMIZATION = "cost_optimization"
    OPERATIONAL_EXCELLENCE = "operational_excellence"
    SUSTAINABILITY = "sustainability"


class AnalysisRuleEngine:
    """
    Rule engine for Terraform code analysis
    Inspired by AWS Well-Architected Framework but cloud-agnostic
    """
    
    def __init__(self):
        self.rules = self._load_default_rules()
    
    def get_rules_for_category(self, category: AnalysisCategory) -> List[Dict[str, Any]]:
        """Get all rules for a specific analysis category"""
        return self.rules.get(category.value, [])
    
    def get_rules_for_resource_type(self, resource_type: str) -> List[Dict[str, Any]]:
        """Get all rules that apply to a specific resource type"""
        applicable_rules = []
        
        for category_rules in self.rules.values():
            for rule in category_rules:
                resource_types = rule.get("resource_types", [])
                if not resource_types or resource_type in resource_types:
                    applicable_rules.append(rule)
        
        return applicable_rules
    
    def _load_default_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load default analysis rules"""
        return {
            "security": self._get_security_rules(),
            "reliability": self._get_reliability_rules(),
            "performance": self._get_performance_rules(),
            "cost_optimization": self._get_cost_optimization_rules(),
            "operational_excellence": self._get_operational_excellence_rules(),
            "sustainability": self._get_sustainability_rules()
        }
    
    def _get_security_rules(self) -> List[Dict[str, Any]]:
        """Security-focused analysis rules"""
        return [
            {
                "id": "SEC-001",
                "type": "encryption",
                "title": "Encryption at Rest Required",
                "description": "All storage resources must have encryption at rest enabled",
                "severity": "high",
                "resource_types": [
                    "aws_s3_bucket",
                    "aws_ebs_volume",
                    "aws_rds_instance",
                    "azurerm_storage_account",
                    "google_storage_bucket"
                ],
                "encryption_attributes": ["server_side_encryption_configuration", "encrypted", "encryption"],
                "recommendation": "Enable encryption at rest for all storage resources",
                "references": [
                    "https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-encryption.html",
                    "https://docs.microsoft.com/en-us/azure/storage/common/storage-service-encryption"
                ]
            },
            {
                "id": "SEC-002",
                "type": "security_group",
                "title": "Restrict Inbound Traffic",
                "description": "Security groups should not allow unrestricted inbound traffic",
                "severity": "critical",
                "resource_types": ["aws_security_group", "azurerm_network_security_group"],
                "recommendation": "Restrict CIDR blocks to specific IP ranges instead of 0.0.0.0/0",
                "references": [
                    "https://docs.aws.amazon.com/vpc/latest/userguide/VPC_SecurityGroups.html"
                ]
            },
            {
                "id": "SEC-003",
                "type": "forbidden_attribute",
                "title": "Public Access Blocked",
                "description": "Storage buckets should not allow public read/write access",
                "severity": "critical",
                "resource_types": ["aws_s3_bucket", "google_storage_bucket"],
                "attribute": "public_read_write",
                "recommendation": "Remove public access permissions and use IAM policies instead",
                "references": [
                    "https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html"
                ]
            },
            {
                "id": "SEC-004",
                "type": "required_attribute",
                "title": "MFA Delete Required",
                "description": "S3 buckets should have MFA delete enabled for additional security",
                "severity": "medium",
                "resource_types": ["aws_s3_bucket"],
                "attribute": "mfa_delete",
                "recommendation": "Enable MFA delete for S3 buckets containing sensitive data",
                "remediation_code": "mfa_delete = true",
                "references": [
                    "https://docs.aws.amazon.com/AmazonS3/latest/userguide/MultiFactorAuthenticationDelete.html"
                ]
            },
            {
                "id": "SEC-005",
                "type": "attribute_value",
                "title": "HTTPS Only Access",
                "description": "Load balancers should redirect HTTP traffic to HTTPS",
                "severity": "high",
                "resource_types": ["aws_lb_listener", "azurerm_lb_rule"],
                "attribute": "protocol",
                "expected_value": "HTTPS",
                "recommendation": "Configure load balancer listeners to use HTTPS protocol",
                "references": [
                    "https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-https-listener.html"
                ]
            }
        ]
    
    def _get_reliability_rules(self) -> List[Dict[str, Any]]:
        """Reliability-focused analysis rules"""
        return [
            {
                "id": "REL-001",
                "type": "required_attribute",
                "title": "Multi-AZ Deployment",
                "description": "Database instances should be deployed across multiple availability zones",
                "severity": "high",
                "resource_types": ["aws_rds_instance", "aws_elasticache_cluster"],
                "attribute": "multi_az",
                "recommendation": "Enable multi-AZ deployment for high availability",
                "remediation_code": "multi_az = true",
                "references": [
                    "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.MultiAZ.html"
                ]
            },
            {
                "id": "REL-002",
                "type": "required_attribute",
                "title": "Backup Configuration",
                "description": "Database instances must have automated backups enabled",
                "severity": "high",
                "resource_types": ["aws_rds_instance", "azurerm_sql_database"],
                "attribute": "backup_retention_period",
                "recommendation": "Configure automated backups with appropriate retention period",
                "remediation_code": "backup_retention_period = 7",
                "references": [
                    "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html"
                ]
            },
            {
                "id": "REL-003",
                "type": "required_attribute",
                "title": "Versioning Enabled",
                "description": "Storage buckets should have versioning enabled",
                "severity": "medium",
                "resource_types": ["aws_s3_bucket", "google_storage_bucket"],
                "attribute": "versioning",
                "recommendation": "Enable versioning to protect against accidental deletion",
                "remediation_code": """versioning {
    enabled = true
  }""",
                "references": [
                    "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html"
                ]
            },
            {
                "id": "REL-004",
                "type": "attribute_value",
                "title": "Auto Scaling Configuration",
                "description": "Auto scaling groups should have appropriate min/max capacity",
                "severity": "medium",
                "resource_types": ["aws_autoscaling_group"],
                "attribute": "min_size",
                "expected_value": 2,
                "recommendation": "Set minimum capacity to at least 2 for high availability",
                "references": [
                    "https://docs.aws.amazon.com/autoscaling/ec2/userguide/AutoScalingGroup.html"
                ]
            }
        ]
    
    def _get_performance_rules(self) -> List[Dict[str, Any]]:
        """Performance-focused analysis rules"""
        return [
            {
                "id": "PERF-001",
                "type": "attribute_value",
                "title": "Instance Type Optimization",
                "description": "Use appropriate instance types for workload requirements",
                "severity": "medium",
                "resource_types": ["aws_instance", "azurerm_virtual_machine"],
                "attribute": "instance_type",
                "recommendation": "Choose instance types based on CPU, memory, and network requirements",
                "references": [
                    "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html"
                ]
            },
            {
                "id": "PERF-002",
                "type": "required_attribute",
                "title": "EBS Optimization",
                "description": "EC2 instances should have EBS optimization enabled",
                "severity": "medium",
                "resource_types": ["aws_instance"],
                "attribute": "ebs_optimized",
                "recommendation": "Enable EBS optimization for better storage performance",
                "remediation_code": "ebs_optimized = true",
                "references": [
                    "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-optimized.html"
                ]
            },
            {
                "id": "PERF-003",
                "type": "attribute_value",
                "title": "Storage Type Optimization",
                "description": "Use appropriate storage types for performance requirements",
                "severity": "low",
                "resource_types": ["aws_ebs_volume"],
                "attribute": "type",
                "expected_value": "gp3",
                "recommendation": "Use gp3 volumes for better price-performance ratio",
                "references": [
                    "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ebs-volume-types.html"
                ]
            }
        ]
    
    def _get_cost_optimization_rules(self) -> List[Dict[str, Any]]:
        """Cost optimization analysis rules"""
        return [
            {
                "id": "COST-001",
                "type": "tagging",
                "title": "Cost Allocation Tags",
                "description": "Resources must have cost allocation tags for billing tracking",
                "severity": "medium",
                "resource_types": ["*"],  # Applies to all resources
                "required_tags": ["Environment", "Project", "Owner", "CostCenter"],
                "recommendation": "Add required tags for cost tracking and allocation",
                "references": [
                    "https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html"
                ]
            },
            {
                "id": "COST-002",
                "type": "attribute_value",
                "title": "Reserved Instance Usage",
                "description": "Consider using reserved instances for predictable workloads",
                "severity": "info",
                "resource_types": ["aws_instance"],
                "recommendation": "Evaluate reserved instance options for cost savings",
                "references": [
                    "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-reserved-instances.html"
                ]
            },
            {
                "id": "COST-003",
                "type": "required_attribute",
                "title": "Lifecycle Configuration",
                "description": "Storage buckets should have lifecycle policies to manage costs",
                "severity": "medium",
                "resource_types": ["aws_s3_bucket"],
                "attribute": "lifecycle_configuration",
                "recommendation": "Configure lifecycle policies to transition objects to cheaper storage classes",
                "references": [
                    "https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html"
                ]
            }
        ]
    
    def _get_operational_excellence_rules(self) -> List[Dict[str, Any]]:
        """Operational excellence analysis rules"""
        return [
            {
                "id": "OPS-001",
                "type": "tagging",
                "title": "Operational Tags",
                "description": "Resources must have operational tags for management",
                "severity": "medium",
                "resource_types": ["*"],
                "required_tags": ["Environment", "Application", "Owner", "ManagedBy"],
                "recommendation": "Add operational tags for resource management and automation",
                "references": [
                    "https://docs.aws.amazon.com/general/latest/gr/aws_tagging.html"
                ]
            },
            {
                "id": "OPS-002",
                "type": "required_attribute",
                "title": "Monitoring Configuration",
                "description": "Resources should have monitoring and logging enabled",
                "severity": "medium",
                "resource_types": ["aws_instance", "aws_rds_instance", "aws_lb"],
                "attribute": "monitoring",
                "recommendation": "Enable detailed monitoring for operational visibility",
                "remediation_code": "monitoring = true",
                "references": [
                    "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-cloudwatch.html"
                ]
            },
            {
                "id": "OPS-003",
                "type": "best_practice",
                "title": "Resource Naming Convention",
                "description": "Resources should follow consistent naming conventions",
                "severity": "low",
                "resource_types": ["*"],
                "recommendation": "Use consistent naming patterns for all resources",
                "references": [
                    "https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html"
                ]
            }
        ]
    
    def _get_sustainability_rules(self) -> List[Dict[str, Any]]:
        """Sustainability-focused analysis rules"""
        return [
            {
                "id": "SUS-001",
                "type": "attribute_value",
                "title": "Energy Efficient Instance Types",
                "description": "Use energy-efficient instance types when possible",
                "severity": "low",
                "resource_types": ["aws_instance"],
                "recommendation": "Consider using Graviton-based instances for better energy efficiency",
                "references": [
                    "https://aws.amazon.com/ec2/graviton/"
                ]
            },
            {
                "id": "SUS-002",
                "type": "required_attribute",
                "title": "Auto Scaling for Efficiency",
                "description": "Use auto scaling to optimize resource utilization",
                "severity": "medium",
                "resource_types": ["aws_autoscaling_group"],
                "attribute": "target_group_arns",
                "recommendation": "Implement auto scaling to reduce resource waste",
                "references": [
                    "https://docs.aws.amazon.com/autoscaling/ec2/userguide/what-is-amazon-ec2-auto-scaling.html"
                ]
            },
            {
                "id": "SUS-003",
                "type": "best_practice",
                "title": "Right-Sizing Resources",
                "description": "Ensure resources are appropriately sized for their workload",
                "severity": "medium",
                "resource_types": ["aws_instance", "aws_rds_instance"],
                "recommendation": "Regularly review and right-size resources to minimize waste",
                "references": [
                    "https://docs.aws.amazon.com/cost-management/latest/userguide/ce-rightsizing.html"
                ]
            }
        ]
    
    def add_custom_rule(self, category: str, rule: Dict[str, Any]) -> None:
        """Add a custom analysis rule"""
        if category not in self.rules:
            self.rules[category] = []
        self.rules[category].append(rule)
    
    def load_rules_from_file(self, file_path: str) -> None:
        """Load rules from a YAML or JSON file"""
        try:
            with open(file_path, 'r') as file:
                if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                    custom_rules = yaml.safe_load(file)
                else:
                    custom_rules = json.load(file)
                
                # Merge custom rules with existing rules
                for category, rules in custom_rules.items():
                    if category in self.rules:
                        self.rules[category].extend(rules)
                    else:
                        self.rules[category] = rules
        except Exception as e:
            print(f"Failed to load rules from {file_path}: {e}")
    
    def export_rules_to_file(self, file_path: str) -> None:
        """Export current rules to a YAML file"""
        try:
            with open(file_path, 'w') as file:
                yaml.dump(self.rules, file, default_flow_style=False, indent=2)
        except Exception as e:
            print(f"Failed to export rules to {file_path}: {e}")
    
    def validate_rule(self, rule: Dict[str, Any]) -> bool:
        """Validate that a rule has required fields"""
        required_fields = ["id", "type", "title", "description", "severity"]
        return all(field in rule for field in required_fields)
    
    def get_rule_by_id(self, rule_id: str) -> Dict[str, Any]:
        """Get a specific rule by its ID"""
        for category_rules in self.rules.values():
            for rule in category_rules:
                if rule.get("id") == rule_id:
                    return rule
        return None 