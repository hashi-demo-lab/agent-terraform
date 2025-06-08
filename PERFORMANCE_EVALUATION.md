# Terraform Code Generation Agent - Performance Evaluation Framework

## Overview

This document outlines a comprehensive approach to evaluate the performance of the Terraform Code Generation Agent across multiple dimensions including code quality, workflow efficiency, validation accuracy, and user experience.

## Table of Contents

- [Evaluation Dimensions](#evaluation-dimensions)
- [Metrics and KPIs](#metrics-and-kpis)
- [Evaluation Methods](#evaluation-methods)
- [Benchmarking Framework](#benchmarking-framework)
- [Automated Testing Pipeline](#automated-testing-pipeline)
- [Performance Monitoring](#performance-monitoring)
- [Evaluation Tools](#evaluation-tools)
- [Reporting and Analytics](#reporting-and-analytics)

## Evaluation Dimensions

### 1. Code Quality Metrics

#### Terraform Code Standards
- **Syntax Correctness**: `terraform validate` pass rate
- **Formatting Compliance**: `terraform fmt` consistency score
- **AVM Compliance**: TFLint AVM ruleset pass rate
- **Security Standards**: Trivy security scan results
- **Best Practices**: Adherence to HashiCorp and AVM guidelines

#### Code Structure Quality
- **Module Organization**: Proper file structure (main.tf, variables.tf, outputs.tf, etc.)
- **Variable Validation**: Comprehensive input validation implementation
- **Output Completeness**: All necessary outputs with proper descriptions
- **Documentation Quality**: README.md completeness and accuracy
- **Resource Naming**: Consistent naming conventions

### 2. Functional Accuracy

#### Requirements Fulfillment
- **Requirement Coverage**: Percentage of user requirements implemented
- **Resource Accuracy**: Correct AWS/Azure/GCP resource selection
- **Configuration Correctness**: Proper resource configuration parameters
- **Dependency Management**: Correct resource dependencies and ordering

#### Validation Pipeline Performance
- **Validation Accuracy**: False positive/negative rates in validation
- **Error Detection**: Ability to identify and report issues
- **Refinement Effectiveness**: Success rate of automated code improvements
- **Iteration Efficiency**: Average iterations needed for successful validation

### 3. Workflow Performance

#### LangGraph Platform Metrics
- **Execution Time**: End-to-end workflow completion time
- **State Management**: Proper state persistence and recovery
- **Agent Coordination**: Smooth transitions between workflow nodes
- **Error Handling**: Graceful failure recovery and retry mechanisms

#### Scalability Metrics
- **Concurrent Workflows**: Performance under multiple simultaneous requests
- **Resource Utilization**: CPU, memory, and I/O efficiency
- **Throughput**: Modules generated per hour/day
- **Response Time**: Time from request to first response

### 4. User Experience

#### Usability Metrics
- **Time to Value**: Time from request to usable Terraform module
- **User Satisfaction**: Subjective quality ratings
- **Learning Curve**: Ease of use for new users
- **Error Recovery**: User ability to resolve issues with agent assistance

#### Integration Experience
- **CLI Integration**: Seamless command-line interface usage
- **IDE Integration**: Cursor/VS Code extension performance
- **CI/CD Integration**: Pipeline integration success rate

## Metrics and KPIs

### Primary KPIs

```yaml
code_quality:
  terraform_validate_pass_rate: ">= 95%"
  tflint_avm_pass_rate: ">= 90%"
  trivy_security_pass_rate: ">= 95%"
  documentation_completeness: ">= 90%"

functional_accuracy:
  requirement_coverage: ">= 95%"
  first_attempt_success_rate: ">= 80%"
  validation_accuracy: ">= 95%"
  false_positive_rate: "<= 5%"

performance:
  avg_generation_time: "<= 60 seconds"
  p95_generation_time: "<= 120 seconds"
  concurrent_workflow_capacity: ">= 10"
  system_uptime: ">= 99.5%"

user_experience:
  user_satisfaction_score: ">= 4.5/5"
  time_to_first_success: "<= 5 minutes"
  error_resolution_rate: ">= 90%"
```

### Secondary Metrics

```yaml
efficiency:
  code_reuse_rate: ">= 70%"
  template_utilization: ">= 80%"
  iteration_reduction: ">= 30%"

reliability:
  workflow_failure_rate: "<= 2%"
  data_consistency_score: ">= 99%"
  recovery_time: "<= 30 seconds"

innovation:
  new_pattern_detection: "Monthly tracking"
  best_practice_adoption: ">= 85%"
  community_contribution: "Quarterly review"
```

## Evaluation Methods

### 1. Automated Testing

#### Unit Testing
```python
# tests/performance/test_code_quality.py
import pytest
from src.agents.generator import GeneratorAgent
from src.evaluation.metrics import CodeQualityMetrics

class TestCodeQuality:
    @pytest.fixture
    def generator_agent(self):
        return GeneratorAgent()
    
    @pytest.fixture
    def quality_metrics(self):
        return CodeQualityMetrics()
    
    def test_terraform_validation_rate(self, generator_agent, quality_metrics):
        """Test that generated code passes terraform validate at required rate"""
        test_cases = load_test_requirements()
        results = []
        
        for requirement in test_cases:
            code = generator_agent.generate_module(requirement)
            validation_result = quality_metrics.validate_terraform_syntax(code)
            results.append(validation_result.passed)
        
        pass_rate = sum(results) / len(results)
        assert pass_rate >= 0.95, f"Terraform validation pass rate {pass_rate} below threshold"
    
    def test_avm_compliance_rate(self, generator_agent, quality_metrics):
        """Test AVM compliance rate meets requirements"""
        test_cases = load_avm_test_cases()
        results = []
        
        for requirement in test_cases:
            code = generator_agent.generate_module(requirement)
            avm_result = quality_metrics.validate_avm_compliance(code)
            results.append(avm_result.passed)
        
        pass_rate = sum(results) / len(results)
        assert pass_rate >= 0.90, f"AVM compliance rate {pass_rate} below threshold"
```

#### Integration Testing
```python
# tests/performance/test_workflow_performance.py
import asyncio
import time
from src.workflows.terraform_workflow import TerraformWorkflowManager

class TestWorkflowPerformance:
    @pytest.mark.asyncio
    async def test_end_to_end_performance(self):
        """Test complete workflow performance"""
        workflow_manager = TerraformWorkflowManager()
        requirements = load_performance_test_requirements()
        
        start_time = time.time()
        
        async for event in workflow_manager.execute_workflow(
            requirements, 
            thread_id="perf_test_001"
        ):
            if event.get("reviewer", {}).get("status") == "complete":
                end_time = time.time()
                execution_time = end_time - start_time
                
                assert execution_time <= 60, f"Workflow took {execution_time}s, exceeds 60s limit"
                break
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_capacity(self):
        """Test system performance under concurrent load"""
        workflow_manager = TerraformWorkflowManager()
        concurrent_requests = 10
        
        tasks = []
        for i in range(concurrent_requests):
            task = workflow_manager.execute_workflow(
                load_test_requirement(i),
                thread_id=f"concurrent_test_{i}"
            )
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        success_rate = success_count / concurrent_requests
        
        assert success_rate >= 0.90, f"Concurrent success rate {success_rate} below threshold"
        assert end_time - start_time <= 120, "Concurrent execution exceeded time limit"
```

### 2. Benchmark Testing

#### Standard Test Suite
```python
# tests/benchmarks/terraform_benchmarks.py
class TerraformBenchmarkSuite:
    """Standardized benchmark tests for consistent evaluation"""
    
    def __init__(self):
        self.test_cases = {
            "simple_s3_bucket": self.load_simple_s3_case(),
            "complex_vpc_setup": self.load_complex_vpc_case(),
            "multi_tier_application": self.load_multi_tier_case(),
            "security_hardened_infrastructure": self.load_security_case(),
            "cost_optimized_setup": self.load_cost_optimized_case()
        }
    
    async def run_full_benchmark(self) -> BenchmarkResults:
        """Run complete benchmark suite"""
        results = BenchmarkResults()
        
        for test_name, test_case in self.test_cases.items():
            print(f"Running benchmark: {test_name}")
            
            # Measure generation time
            start_time = time.time()
            generated_code = await self.generate_terraform_module(test_case)
            generation_time = time.time() - start_time
            
            # Measure validation performance
            validation_results = await self.run_validation_pipeline(generated_code)
            
            # Measure quality metrics
            quality_score = self.calculate_quality_score(generated_code, test_case)
            
            results.add_test_result(test_name, {
                "generation_time": generation_time,
                "validation_results": validation_results,
                "quality_score": quality_score,
                "requirement_coverage": self.calculate_coverage(generated_code, test_case)
            })
        
        return results
```

### 3. A/B Testing Framework

#### Version Comparison
```python
# tests/evaluation/ab_testing.py
class ABTestingFramework:
    """Compare different versions or configurations of the agent"""
    
    def __init__(self):
        self.test_configurations = {
            "baseline": self.load_baseline_config(),
            "experimental": self.load_experimental_config()
        }
    
    async def run_ab_test(self, test_cases: List[dict], metrics: List[str]) -> ABTestResults:
        """Run A/B test comparing configurations"""
        results = {}
        
        for config_name, config in self.test_configurations.items():
            agent = self.create_agent_with_config(config)
            config_results = []
            
            for test_case in test_cases:
                result = await self.evaluate_single_case(agent, test_case, metrics)
                config_results.append(result)
            
            results[config_name] = config_results
        
        return ABTestResults(results)
    
    def calculate_statistical_significance(self, results: ABTestResults) -> dict:
        """Calculate statistical significance of differences"""
        from scipy import stats
        
        baseline_scores = results.get_metric_values("baseline", "quality_score")
        experimental_scores = results.get_metric_values("experimental", "quality_score")
        
        t_stat, p_value = stats.ttest_ind(baseline_scores, experimental_scores)
        
        return {
            "t_statistic": t_stat,
            "p_value": p_value,
            "significant": p_value < 0.05,
            "improvement": np.mean(experimental_scores) - np.mean(baseline_scores)
        }
```

## Benchmarking Framework

### Test Case Categories

#### 1. Complexity Levels
```yaml
simple_cases:
  - single_s3_bucket
  - basic_ec2_instance
  - simple_rds_database

medium_cases:
  - vpc_with_subnets
  - load_balanced_application
  - multi_az_deployment

complex_cases:
  - full_three_tier_architecture
  - microservices_infrastructure
  - enterprise_security_setup

expert_cases:
  - multi_cloud_deployment
  - disaster_recovery_setup
  - compliance_heavy_infrastructure
```

#### 2. Provider Coverage
```yaml
aws_cases:
  - ec2_auto_scaling
  - lambda_api_gateway
  - ecs_fargate_cluster

azure_cases:
  - app_service_deployment
  - aks_cluster_setup
  - storage_account_configuration

gcp_cases:
  - gke_cluster_deployment
  - cloud_function_setup
  - cloud_storage_configuration
```

### Performance Baselines

#### Reference Implementation Times
```yaml
baseline_performance:
  simple_cases:
    generation_time: "15-30 seconds"
    validation_time: "5-10 seconds"
    total_time: "20-40 seconds"
  
  medium_cases:
    generation_time: "30-60 seconds"
    validation_time: "10-20 seconds"
    total_time: "40-80 seconds"
  
  complex_cases:
    generation_time: "60-120 seconds"
    validation_time: "20-40 seconds"
    total_time: "80-160 seconds"
```

## Automated Testing Pipeline

### CI/CD Integration

#### GitHub Actions Workflow
```yaml
# .github/workflows/performance_evaluation.yml
name: Performance Evaluation

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  performance_tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run performance benchmarks
      run: |
        pytest tests/benchmarks/ -v --benchmark-json=benchmark_results.json
    
    - name: Run quality metrics tests
      run: |
        pytest tests/performance/ -v --cov=src --cov-report=xml
    
    - name: Generate performance report
      run: |
        python scripts/generate_performance_report.py
    
    - name: Upload results
      uses: actions/upload-artifact@v3
      with:
        name: performance-results
        path: |
          benchmark_results.json
          performance_report.html
          coverage.xml
```

### Continuous Monitoring

#### Performance Monitoring Script
```python
# scripts/continuous_monitoring.py
import asyncio
import json
import time
from datetime import datetime
from src.evaluation.performance_monitor import PerformanceMonitor

class ContinuousMonitor:
    def __init__(self):
        self.monitor = PerformanceMonitor()
        self.monitoring_interval = 3600  # 1 hour
    
    async def run_continuous_monitoring(self):
        """Run continuous performance monitoring"""
        while True:
            try:
                # Run performance tests
                results = await self.monitor.run_performance_suite()
                
                # Log results
                self.log_performance_results(results)
                
                # Check for performance degradation
                if self.detect_performance_regression(results):
                    await self.send_alert(results)
                
                # Wait for next monitoring cycle
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    def detect_performance_regression(self, current_results: dict) -> bool:
        """Detect if performance has regressed beyond acceptable thresholds"""
        historical_baseline = self.load_historical_baseline()
        
        for metric, current_value in current_results.items():
            baseline_value = historical_baseline.get(metric)
            if baseline_value:
                regression_threshold = baseline_value * 1.2  # 20% degradation threshold
                if current_value > regression_threshold:
                    return True
        
        return False
    
    async def send_alert(self, results: dict):
        """Send performance regression alert"""
        alert_message = f"""
        Performance Regression Detected!
        
        Timestamp: {datetime.now().isoformat()}
        Affected Metrics: {self.get_regressed_metrics(results)}
        
        Current Results: {json.dumps(results, indent=2)}
        """
        
        # Send to monitoring system (Slack, email, etc.)
        await self.send_notification(alert_message)
```

## Performance Monitoring

### Real-time Metrics Collection

#### Metrics Collection System
```python
# src/evaluation/metrics_collector.py
from dataclasses import dataclass
from typing import Dict, List
import time
import psutil
from prometheus_client import Counter, Histogram, Gauge

@dataclass
class PerformanceMetrics:
    generation_time: float
    validation_time: float
    memory_usage: float
    cpu_usage: float
    success_rate: float
    error_count: int

class MetricsCollector:
    def __init__(self):
        # Prometheus metrics
        self.generation_time_histogram = Histogram(
            'terraform_generation_time_seconds',
            'Time spent generating Terraform code'
        )
        self.validation_time_histogram = Histogram(
            'terraform_validation_time_seconds',
            'Time spent validating Terraform code'
        )
        self.success_counter = Counter(
            'terraform_generation_success_total',
            'Total successful Terraform generations'
        )
        self.error_counter = Counter(
            'terraform_generation_errors_total',
            'Total Terraform generation errors',
            ['error_type']
        )
        self.memory_gauge = Gauge(
            'terraform_agent_memory_usage_bytes',
            'Memory usage of Terraform agent'
        )
    
    def record_generation_metrics(self, 
                                generation_time: float,
                                validation_time: float,
                                success: bool,
                                error_type: str = None):
        """Record metrics for a generation cycle"""
        
        # Record timing metrics
        self.generation_time_histogram.observe(generation_time)
        self.validation_time_histogram.observe(validation_time)
        
        # Record success/failure
        if success:
            self.success_counter.inc()
        else:
            self.error_counter.labels(error_type=error_type or 'unknown').inc()
        
        # Record system metrics
        self.memory_gauge.set(psutil.Process().memory_info().rss)
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics snapshot"""
        process = psutil.Process()
        
        return PerformanceMetrics(
            generation_time=self._get_avg_generation_time(),
            validation_time=self._get_avg_validation_time(),
            memory_usage=process.memory_info().rss,
            cpu_usage=process.cpu_percent(),
            success_rate=self._calculate_success_rate(),
            error_count=self._get_error_count()
        )
```

### Dashboard and Visualization

#### Grafana Dashboard Configuration
```json
{
  "dashboard": {
    "title": "Terraform Agent Performance",
    "panels": [
      {
        "title": "Generation Time",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(terraform_generation_time_seconds_sum[5m]) / rate(terraform_generation_time_seconds_count[5m])",
            "legendFormat": "Average Generation Time"
          }
        ]
      },
      {
        "title": "Success Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(terraform_generation_success_total[5m]) / (rate(terraform_generation_success_total[5m]) + rate(terraform_generation_errors_total[5m]))",
            "legendFormat": "Success Rate"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "terraform_agent_memory_usage_bytes",
            "legendFormat": "Memory Usage"
          }
        ]
      }
    ]
  }
}
```

## Evaluation Tools

### Performance Testing CLI

#### Command Line Interface
```python
# scripts/performance_cli.py
import click
import asyncio
from src.evaluation.benchmark_suite import TerraformBenchmarkSuite
from src.evaluation.performance_analyzer import PerformanceAnalyzer

@click.group()
def performance_cli():
    """Terraform Agent Performance Evaluation CLI"""
    pass

@performance_cli.command()
@click.option('--suite', default='full', help='Benchmark suite to run')
@click.option('--output', default='results.json', help='Output file for results')
@click.option('--verbose', is_flag=True, help='Verbose output')
def benchmark(suite, output, verbose):
    """Run performance benchmarks"""
    click.echo(f"Running {suite} benchmark suite...")
    
    benchmark_suite = TerraformBenchmarkSuite()
    results = asyncio.run(benchmark_suite.run_benchmark(suite))
    
    # Save results
    with open(output, 'w') as f:
        json.dump(results.to_dict(), f, indent=2)
    
    if verbose:
        click.echo(f"Results saved to {output}")
        click.echo(f"Summary: {results.get_summary()}")

@performance_cli.command()
@click.option('--baseline', required=True, help='Baseline results file')
@click.option('--current', required=True, help='Current results file')
@click.option('--threshold', default=0.05, help='Significance threshold')
def compare(baseline, current, threshold):
    """Compare performance results"""
    analyzer = PerformanceAnalyzer()
    
    comparison = analyzer.compare_results(baseline, current)
    significance = analyzer.statistical_significance(comparison, threshold)
    
    click.echo("Performance Comparison Results:")
    click.echo(f"Improvement: {comparison.improvement:.2%}")
    click.echo(f"Statistical Significance: {significance.significant}")
    click.echo(f"P-value: {significance.p_value:.4f}")

@performance_cli.command()
@click.option('--duration', default=3600, help='Monitoring duration in seconds')
@click.option('--interval', default=60, help='Monitoring interval in seconds')
def monitor(duration, interval):
    """Run continuous performance monitoring"""
    click.echo(f"Starting performance monitoring for {duration} seconds...")
    
    monitor = ContinuousMonitor()
    asyncio.run(monitor.run_monitoring_session(duration, interval))

if __name__ == '__main__':
    performance_cli()
```

### Usage Examples

#### Running Benchmarks
```bash
# Run full benchmark suite
python scripts/performance_cli.py benchmark --suite full --output benchmark_results.json

# Run specific test category
python scripts/performance_cli.py benchmark --suite aws_simple --verbose

# Compare results
python scripts/performance_cli.py compare --baseline baseline_results.json --current current_results.json

# Start monitoring
python scripts/performance_cli.py monitor --duration 7200 --interval 30
```

## Reporting and Analytics

### Performance Report Generation

#### Automated Report Generator
```python
# src/evaluation/report_generator.py
from jinja2 import Template
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime

class PerformanceReportGenerator:
    def __init__(self):
        self.report_template = self.load_report_template()
    
    def generate_comprehensive_report(self, results: dict) -> str:
        """Generate comprehensive performance report"""
        
        # Calculate summary statistics
        summary_stats = self.calculate_summary_statistics(results)
        
        # Generate visualizations
        charts = self.generate_performance_charts(results)
        
        # Create trend analysis
        trends = self.analyze_performance_trends(results)
        
        # Generate recommendations
        recommendations = self.generate_recommendations(results)
        
        # Render report
        report_html = self.report_template.render(
            timestamp=datetime.now().isoformat(),
            summary=summary_stats,
            charts=charts,
            trends=trends,
            recommendations=recommendations,
            detailed_results=results
        )
        
        return report_html
    
    def generate_performance_charts(self, results: dict) -> dict:
        """Generate performance visualization charts"""
        charts = {}
        
        # Generation time distribution
        generation_times = [r['generation_time'] for r in results['test_results']]
        plt.figure(figsize=(10, 6))
        plt.hist(generation_times, bins=20, alpha=0.7)
        plt.title('Generation Time Distribution')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Frequency')
        plt.savefig('generation_time_dist.png')
        charts['generation_time_distribution'] = 'generation_time_dist.png'
        
        # Success rate by complexity
        complexity_success = self.group_by_complexity(results)
        plt.figure(figsize=(10, 6))
        plt.bar(complexity_success.keys(), complexity_success.values())
        plt.title('Success Rate by Complexity')
        plt.xlabel('Complexity Level')
        plt.ylabel('Success Rate')
        plt.savefig('success_by_complexity.png')
        charts['success_by_complexity'] = 'success_by_complexity.png'
        
        return charts
    
    def generate_recommendations(self, results: dict) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        # Analyze results and generate recommendations
        avg_generation_time = np.mean([r['generation_time'] for r in results['test_results']])
        if avg_generation_time > 60:
            recommendations.append(
                "Consider optimizing code generation algorithms - average generation time exceeds 60 seconds"
            )
        
        success_rate = results['summary']['overall_success_rate']
        if success_rate < 0.95:
            recommendations.append(
                f"Improve validation pipeline - success rate of {success_rate:.1%} is below 95% target"
            )
        
        memory_usage = results['summary']['avg_memory_usage']
        if memory_usage > 1024 * 1024 * 1024:  # 1GB
            recommendations.append(
                "Optimize memory usage - average memory consumption exceeds 1GB"
            )
        
        return recommendations
```

### Report Template

#### HTML Report Template
```html
<!-- templates/performance_report.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Terraform Agent Performance Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; }
        .metric { display: inline-block; margin: 10px; padding: 15px; background-color: #e8f4f8; border-radius: 5px; }
        .chart { margin: 20px 0; text-align: center; }
        .recommendation { background-color: #fff3cd; padding: 10px; margin: 5px 0; border-radius: 3px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Terraform Code Generation Agent - Performance Report</h1>
        <p>Generated: {{ timestamp }}</p>
    </div>
    
    <h2>Executive Summary</h2>
    <div class="metric">
        <strong>Overall Success Rate:</strong> {{ "%.1f%%" | format(summary.overall_success_rate * 100) }}
    </div>
    <div class="metric">
        <strong>Average Generation Time:</strong> {{ "%.1f seconds" | format(summary.avg_generation_time) }}
    </div>
    <div class="metric">
        <strong>Average Memory Usage:</strong> {{ "%.1f MB" | format(summary.avg_memory_usage / 1024 / 1024) }}
    </div>
    
    <h2>Performance Trends</h2>
    {% for trend in trends %}
    <p>{{ trend }}</p>
    {% endfor %}
    
    <h2>Performance Charts</h2>
    {% for chart_name, chart_path in charts.items() %}
    <div class="chart">
        <h3>{{ chart_name.replace('_', ' ').title() }}</h3>
        <img src="{{ chart_path }}" alt="{{ chart_name }}">
    </div>
    {% endfor %}
    
    <h2>Recommendations</h2>
    {% for recommendation in recommendations %}
    <div class="recommendation">{{ recommendation }}</div>
    {% endfor %}
    
    <h2>Detailed Results</h2>
    <table>
        <tr>
            <th>Test Case</th>
            <th>Generation Time (s)</th>
            <th>Validation Time (s)</th>
            <th>Success</th>
            <th>Quality Score</th>
        </tr>
        {% for result in detailed_results.test_results %}
        <tr>
            <td>{{ result.test_name }}</td>
            <td>{{ "%.2f" | format(result.generation_time) }}</td>
            <td>{{ "%.2f" | format(result.validation_time) }}</td>
            <td>{{ "✓" if result.success else "✗" }}</td>
            <td>{{ "%.1f" | format(result.quality_score) }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
```

This comprehensive performance evaluation framework provides:

1. **Multi-dimensional evaluation** covering code quality, functional accuracy, workflow performance, and user experience
2. **Automated testing pipeline** with CI/CD integration
3. **Benchmarking framework** with standardized test cases
4. **Real-time monitoring** with metrics collection and alerting
5. **Statistical analysis** including A/B testing capabilities
6. **Comprehensive reporting** with visualizations and recommendations

The framework ensures continuous performance monitoring and improvement of the Terraform Code Generation Agent across all critical dimensions. 