# examples/analysis_example.py
"""
Example: Terraform Code Analysis using Well-Architected Framework
Demonstrates the modernized analysis agent inspired by AWS Well-Architected IaC Analyzer
"""

import asyncio
from pathlib import Path

from src.workflows.analysis_workflow import (
    TerraformAnalysisWorkflowManager, 
    WorkflowMode
)
from src.agents.analyzer import AnalysisCategory, SeverityLevel


# Example Terraform code with various issues for demonstration
EXAMPLE_TERRAFORM_CODE = """
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

# S3 Bucket with security issues (for demonstration)
resource "aws_s3_bucket" "example" {
  bucket = "my-example-bucket-${var.environment}"
  
  # Missing: encryption configuration
  # Missing: public access block
  # Missing: versioning
}

# Security Group with overly permissive rules
resource "aws_security_group" "web" {
  name_prefix = "web-sg"
  description = "Security group for web servers"
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Too permissive
  }
  
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Critical security issue
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # Missing: proper tags
}

# EC2 Instance with performance and reliability issues
resource "aws_instance" "web" {
  ami           = "ami-0c02fb55956c7d316"  # Hardcoded AMI
  instance_type = "t2.micro"               # Not EBS optimized
  
  vpc_security_group_ids = [aws_security_group.web.id]
  
  # Missing: monitoring
  # Missing: proper tags
  # Missing: user_data for configuration
}

# RDS Instance with reliability issues
resource "aws_db_instance" "database" {
  identifier = "myapp-db"
  
  engine         = "mysql"
  engine_version = "8.0"
  instance_class = "db.t3.micro"
  
  allocated_storage = 20
  storage_type      = "gp2"  # Not latest generation
  
  db_name  = "myapp"
  username = "admin"
  password = "password123"  # Hardcoded password - security issue
  
  # Missing: multi_az
  # Missing: backup_retention_period
  # Missing: encryption
  # Missing: proper tags
  
  skip_final_snapshot = true
}

# Load Balancer without HTTPS
resource "aws_lb" "main" {
  name               = "main-lb"
  internal           = false
  load_balancer_type = "application"
  
  # Missing: security_groups
  # Missing: subnets
  # Missing: proper tags
}

resource "aws_lb_listener" "web" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"  # Should be HTTPS
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

resource "aws_lb_target_group" "web" {
  name     = "web-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = "vpc-12345678"  # Hardcoded VPC ID
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/"
    matcher             = "200"
  }
  
  # Missing: proper tags
}
"""

# Example with better practices for comparison
IMPROVED_TERRAFORM_CODE = """
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = local.common_tags
  }
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
  validation {
    condition = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "AWS region must be in valid format (e.g., us-west-2)."
  }
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Name of the project"
  type        = string
}

locals {
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    CreatedBy   = "terraform-agent"
  }
}

# S3 Bucket with security best practices
resource "aws_s3_bucket" "example" {
  bucket = "${var.project_name}-${var.environment}-${random_id.bucket_suffix.hex}"
  
  tags = local.common_tags
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_versioning" "example" {
  bucket = aws_s3_bucket.example.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "example" {
  bucket = aws_s3_bucket.example.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "example" {
  bucket = aws_s3_bucket.example.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Security Group with restricted access
resource "aws_security_group" "web" {
  name_prefix = "${var.project_name}-web-sg"
  description = "Security group for web servers"
  vpc_id      = data.aws_vpc.default.id
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from anywhere"
  }
  
  ingress {
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
    description     = "SSH from bastion host only"
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-web-sg"
  })
}

# EC2 Instance with best practices
resource "aws_instance" "web" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.small"
  
  vpc_security_group_ids = [aws_security_group.web.id]
  subnet_id              = data.aws_subnet.public.id
  
  ebs_optimized = true
  monitoring    = true
  
  root_block_device {
    volume_type = "gp3"
    volume_size = 20
    encrypted   = true
  }
  
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    environment = var.environment
  }))
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-web-${var.environment}"
  })
}

# RDS Instance with reliability and security
resource "aws_db_instance" "database" {
  identifier = "${var.project_name}-db-${var.environment}"
  
  engine         = "mysql"
  engine_version = "8.0"
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true
  
  db_name  = "myapp"
  username = "admin"
  password = random_password.db_password.result
  
  multi_az               = var.environment == "prod"
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  vpc_security_group_ids = [aws_security_group.database.id]
  db_subnet_group_name   = aws_db_subnet_group.database.name
  
  skip_final_snapshot = var.environment != "prod"
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-db-${var.environment}"
  })
}

resource "random_password" "db_password" {
  length  = 16
  special = true
}

# Data sources
data "aws_vpc" "default" {
  default = true
}

data "aws_subnet" "public" {
  vpc_id            = data.aws_vpc.default.id
  availability_zone = "${var.aws_region}a"
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}
"""


async def analyze_terraform_code_example():
    """Example: Basic Terraform code analysis"""
    print("🔍 Terraform Code Analysis Example")
    print("=" * 50)
    
    # Initialize the workflow manager
    workflow_manager = TerraformAnalysisWorkflowManager()
    
    # Analyze the example code
    print("\n📋 Analyzing Terraform code with security and reliability issues...")
    
    analysis_report = await workflow_manager.analyze_terraform_code(
        terraform_code=EXAMPLE_TERRAFORM_CODE,
        mode=WorkflowMode.ANALYSIS_ONLY,
        file_paths=["main.tf"]
    )
    
    if analysis_report:
        print(f"\n📊 Analysis Results:")
        print(f"   Overall Score: {analysis_report.score:.1f}/100")
        print(f"   Total Issues: {analysis_report.summary['total_issues']}")
        print(f"   Critical: {analysis_report.summary['critical']}")
        print(f"   High: {analysis_report.summary['high']}")
        print(f"   Medium: {analysis_report.summary['medium']}")
        print(f"   Low: {analysis_report.summary['low']}")
        
        # Show issues by category
        print(f"\n🔍 Issues by Category:")
        category_counts = {}
        for issue in analysis_report.issues:
            category = issue.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        for category, count in category_counts.items():
            print(f"   {category.replace('_', ' ').title()}: {count}")
        
        # Show top 5 critical/high issues
        critical_high_issues = [
            issue for issue in analysis_report.issues 
            if issue.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]
        ]
        
        if critical_high_issues:
            print(f"\n🚨 Top Critical/High Severity Issues:")
            for i, issue in enumerate(critical_high_issues[:5], 1):
                print(f"   {i}. [{issue.severity.value.upper()}] {issue.title}")
                print(f"      Resource: {issue.resource_type}.{issue.resource_name}")
                print(f"      Category: {issue.category.value}")
                print(f"      Recommendation: {issue.recommendation}")
                print()
        
        # Show recommendations
        if analysis_report.recommendations:
            print(f"📝 Recommendations:")
            for i, rec in enumerate(analysis_report.recommendations, 1):
                print(f"   {i}. {rec}")
    
    else:
        print("❌ Analysis failed to complete")


async def analyze_with_fixes_example():
    """Example: Analyze code and generate automated fixes"""
    print("\n🔧 Terraform Code Analysis with Automated Fixes")
    print("=" * 50)
    
    workflow_manager = TerraformAnalysisWorkflowManager()
    
    print("\n🔄 Analyzing code and generating automated fixes...")
    
    result = await workflow_manager.analyze_with_fixes(
        terraform_code=EXAMPLE_TERRAFORM_CODE,
        file_paths=["main.tf"]
    )
    
    analysis_report = result.get("analysis_report")
    fixed_code = result.get("fixed_code")
    fixes_applied = result.get("fixes_applied", [])
    
    if analysis_report:
        print(f"\n📊 Analysis Results:")
        print(f"   Issues Found: {len(analysis_report.issues)}")
        print(f"   Fixes Applied: {len(fixes_applied)}")
        
        if fixes_applied:
            print(f"\n🔧 Applied Fixes:")
            for fix in fixes_applied:
                print(f"   - {fix}")
        
        if fixed_code:
            print(f"\n📄 Fixed code generated (showing first 500 characters):")
            print(f"   {fixed_code[:500]}...")
    
    else:
        print("❌ Analysis with fixes failed to complete")


async def compare_code_quality_example():
    """Example: Compare code quality between original and improved versions"""
    print("\n📊 Code Quality Comparison Example")
    print("=" * 50)
    
    workflow_manager = TerraformAnalysisWorkflowManager()
    
    print("\n🔍 Analyzing original code...")
    original_analysis = await workflow_manager.analyze_terraform_code(
        terraform_code=EXAMPLE_TERRAFORM_CODE,
        mode=WorkflowMode.ANALYSIS_ONLY
    )
    
    print("\n🔍 Analyzing improved code...")
    improved_analysis = await workflow_manager.analyze_terraform_code(
        terraform_code=IMPROVED_TERRAFORM_CODE,
        mode=WorkflowMode.ANALYSIS_ONLY
    )
    
    if original_analysis and improved_analysis:
        print(f"\n📊 Quality Comparison:")
        print(f"   Original Code Score: {original_analysis.score:.1f}/100")
        print(f"   Improved Code Score: {improved_analysis.score:.1f}/100")
        print(f"   Improvement: +{improved_analysis.score - original_analysis.score:.1f} points")
        
        print(f"\n📈 Issue Reduction:")
        print(f"   Original Issues: {original_analysis.summary['total_issues']}")
        print(f"   Improved Issues: {improved_analysis.summary['total_issues']}")
        print(f"   Reduction: {original_analysis.summary['total_issues'] - improved_analysis.summary['total_issues']} issues")
        
        # Category-wise comparison
        print(f"\n🔍 Issues by Severity:")
        severities = ['critical', 'high', 'medium', 'low']
        for severity in severities:
            original_count = original_analysis.summary.get(severity, 0)
            improved_count = improved_analysis.summary.get(severity, 0)
            reduction = original_count - improved_count
            print(f"   {severity.title()}: {original_count} → {improved_count} (-{reduction})")


async def full_workflow_example():
    """Example: Full generation workflow with analysis"""
    print("\n🚀 Full Generation Workflow Example")
    print("=" * 50)
    
    workflow_manager = TerraformAnalysisWorkflowManager()
    
    # Define requirements for new infrastructure
    requirements = {
        "provider": "aws",
        "resources": [
            {
                "type": "s3_bucket",
                "name": "data_storage",
                "encryption": True,
                "versioning": True,
                "public_access": False
            },
            {
                "type": "ec2_instance",
                "name": "web_server",
                "instance_type": "t3.medium",
                "monitoring": True,
                "ebs_optimized": True
            }
        ],
        "environment": "production",
        "compliance": ["security", "reliability", "cost_optimization"]
    }
    
    print(f"\n📋 Generating infrastructure with requirements:")
    for key, value in requirements.items():
        if key != "resources":
            print(f"   {key}: {value}")
    
    print(f"   resources: {len(requirements['resources'])} resources defined")
    
    result = await workflow_manager.full_generation_workflow(
        requirements=requirements,
        existing_code=None  # Start from scratch
    )
    
    analysis_report = result.get("analysis_report")
    generated_code = result.get("generated_code")
    documentation = result.get("documentation")
    
    if generated_code:
        print(f"\n✅ Code generation completed")
        print(f"   Generated code length: {len(generated_code)} characters")
        
        if analysis_report:
            print(f"   Analysis score: {analysis_report.score:.1f}/100")
            print(f"   Issues found: {analysis_report.summary['total_issues']}")
        
        if documentation:
            print(f"   Documentation generated: {len(documentation)} characters")
    
    else:
        print("❌ Full workflow failed to complete")


async def category_specific_analysis_example():
    """Example: Analyze specific Well-Architected categories"""
    print("\n🎯 Category-Specific Analysis Example")
    print("=" * 50)
    
    workflow_manager = TerraformAnalysisWorkflowManager()
    
    # Analyze each category separately
    categories = [
        AnalysisCategory.SECURITY,
        AnalysisCategory.RELIABILITY,
        AnalysisCategory.PERFORMANCE,
        AnalysisCategory.COST_OPTIMIZATION
    ]
    
    for category in categories:
        print(f"\n🔍 Analyzing {category.value.replace('_', ' ').title()} category...")
        
        # In a real implementation, you would modify the analyzer to focus on specific categories
        analysis_report = await workflow_manager.analyze_terraform_code(
            terraform_code=EXAMPLE_TERRAFORM_CODE,
            mode=WorkflowMode.ANALYSIS_ONLY
        )
        
        if analysis_report:
            # Filter issues for this category
            category_issues = [
                issue for issue in analysis_report.issues 
                if issue.category == category
            ]
            
            print(f"   Issues found: {len(category_issues)}")
            
            if category_issues:
                severity_counts = {}
                for issue in category_issues:
                    severity = issue.severity.value
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                for severity, count in severity_counts.items():
                    print(f"   {severity}: {count}")


async def main():
    """Run all examples"""
    print("🏗️  Terraform Well-Architected Analysis Examples")
    print("Inspired by AWS Well-Architected IaC Analyzer")
    print("Modernized with LangGraph, LangMem, and MCP")
    print("=" * 60)
    
    try:
        # Run examples
        await analyze_terraform_code_example()
        await analyze_with_fixes_example()
        await compare_code_quality_example()
        await category_specific_analysis_example()
        await full_workflow_example()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 