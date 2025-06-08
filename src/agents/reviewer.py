# src/agents/reviewer.py
"""
Reviewer Agent - Final quality assurance (LangGraph node)
Following .cursorrules specifications
"""

import asyncio
from typing import Dict, List, Any
import structlog

from langchain_core.messages import BaseMessage, AIMessage
from langgraph.platform import LangGraphPlatform

from ..workflows.state_management import TerraformState, context_manager

logger = structlog.get_logger()


class ReviewerAgent:
    """
    Final quality assurance agent
    LangGraph node implementation following .cursorrules
    """
    
    def __init__(self, platform: LangGraphPlatform):
        self.platform = platform
    
    def __call__(self, state: TerraformState) -> TerraformState:
        """Main reviewer entry point - LangGraph node implementation"""
        return asyncio.run(self._review_final_output(state))
    
    async def _review_final_output(self, state: TerraformState) -> TerraformState:
        """Perform final quality assurance review"""
        
        logger.info("Starting final quality review", 
                   workflow_id=state["workflow_id"],
                   current_agent="reviewer")
        
        state["current_agent"] = "reviewer"
        
        try:
            # Perform comprehensive review
            review_results = await self._conduct_comprehensive_review(state)
            
            # Store review results in context
            context_manager.store_context(
                state["workflow_id"],
                "review_results",
                review_results
            )
            
            # Generate final review message
            review_message = self._generate_review_message(review_results)
            state["messages"].append(AIMessage(content=review_message))
            
            # Update final status based on review
            if review_results["overall_quality"] >= 80:
                final_status = "completed_successfully"
            elif review_results["overall_quality"] >= 60:
                final_status = "completed_with_warnings"
            else:
                final_status = "completed_with_issues"
            
            # Store final status
            state["final_review_status"] = final_status
            
            logger.info("Final quality review completed",
                       workflow_id=state["workflow_id"],
                       quality_score=review_results["overall_quality"],
                       status=final_status)
            
        except Exception as e:
            error_msg = f"Final review failed: {str(e)}"
            logger.error("Final review failed", 
                        workflow_id=state["workflow_id"],
                        error=str(e))
            state["errors"].append(error_msg)
            state["messages"].append(AIMessage(content=f"Review Error: {error_msg}"))
        
        return state
    
    async def _conduct_comprehensive_review(self, state: TerraformState) -> Dict[str, Any]:
        """Conduct comprehensive quality review"""
        
        review_results = {
            "code_quality": 0,
            "security_compliance": 0,
            "documentation_quality": 0,
            "validation_status": 0,
            "best_practices": 0,
            "overall_quality": 0,
            "recommendations": [],
            "strengths": [],
            "areas_for_improvement": []
        }
        
        # Review code quality
        code_quality_score = self._review_code_quality(state)
        review_results["code_quality"] = code_quality_score
        
        # Review security compliance
        security_score = self._review_security_compliance(state)
        review_results["security_compliance"] = security_score
        
        # Review documentation quality
        doc_score = self._review_documentation_quality(state)
        review_results["documentation_quality"] = doc_score
        
        # Review validation status
        validation_score = self._review_validation_status(state)
        review_results["validation_status"] = validation_score
        
        # Review best practices adherence
        best_practices_score = self._review_best_practices(state)
        review_results["best_practices"] = best_practices_score
        
        # Calculate overall quality score
        scores = [code_quality_score, security_score, doc_score, validation_score, best_practices_score]
        review_results["overall_quality"] = sum(scores) / len(scores)
        
        # Generate recommendations
        review_results["recommendations"] = self._generate_recommendations(review_results, state)
        
        # Identify strengths
        review_results["strengths"] = self._identify_strengths(review_results, state)
        
        # Identify areas for improvement
        review_results["areas_for_improvement"] = self._identify_improvements(review_results, state)
        
        return review_results
    
    def _review_code_quality(self, state: TerraformState) -> float:
        """Review code quality aspects"""
        
        score = 0
        max_score = 100
        
        generated_code = state.get("generated_code", "")
        
        if not generated_code:
            return 0
        
        # Check code structure (20 points)
        if "resource" in generated_code:
            score += 10
        if "variable" in generated_code:
            score += 5
        if "output" in generated_code:
            score += 5
        
        # Check for proper formatting (20 points)
        lines = generated_code.split('\n')
        properly_indented = sum(1 for line in lines if line.startswith('  ') or not line.strip())
        if len(lines) > 0:
            indentation_ratio = properly_indented / len(lines)
            score += int(20 * indentation_ratio)
        
        # Check for comments and documentation (20 points)
        comment_lines = sum(1 for line in lines if line.strip().startswith('#'))
        if comment_lines > 0:
            score += min(20, comment_lines * 5)
        
        # Check for consistent naming (20 points)
        import re
        snake_case_pattern = re.compile(r'^[a-z][a-z0-9_]*$')
        resource_names = re.findall(r'resource\s+"[^"]+"\s+"([^"]+)"', generated_code)
        
        if resource_names:
            valid_names = sum(1 for name in resource_names if snake_case_pattern.match(name))
            naming_ratio = valid_names / len(resource_names)
            score += int(20 * naming_ratio)
        else:
            score += 10  # Partial credit if no resources found
        
        # Check for security best practices (20 points)
        security_keywords = ['encryption', 'versioning', 'public_access_block', 'tags']
        found_security = sum(1 for keyword in security_keywords if keyword in generated_code.lower())
        score += int(20 * (found_security / len(security_keywords)))
        
        return min(score, max_score)
    
    def _review_security_compliance(self, state: TerraformState) -> float:
        """Review security compliance"""
        
        validation_results = state.get("validation_results", [])
        
        # Check security validation tools
        security_tools = ['trivy', 'tflint_avm']
        security_results = [r for r in validation_results if r.tool in security_tools]
        
        if not security_results:
            return 50  # Partial score if no security validation
        
        passed_security = sum(1 for r in security_results if r.passed)
        security_score = (passed_security / len(security_results)) * 100
        
        # Bonus points for specific security features
        generated_code = state.get("generated_code", "")
        security_features = [
            'public_access_block',
            'server_side_encryption',
            'versioning',
            'backup_retention',
            'multi_az'
        ]
        
        found_features = sum(1 for feature in security_features if feature in generated_code)
        bonus_score = min(20, found_features * 4)
        
        return min(security_score + bonus_score, 100)
    
    def _review_documentation_quality(self, state: TerraformState) -> float:
        """Review documentation quality"""
        
        documentation = state.get("documentation", "")
        
        if not documentation:
            return 0
        
        score = 0
        
        # Check for essential sections (60 points)
        essential_sections = [
            '## Description',
            '## Usage',
            '## Variables',
            '## Outputs',
            '## Security',
            '## Architecture'
        ]
        
        found_sections = sum(1 for section in essential_sections if section in documentation)
        score += (found_sections / len(essential_sections)) * 60
        
        # Check documentation length (20 points)
        if len(documentation) > 1000:
            score += 20
        elif len(documentation) > 500:
            score += 15
        elif len(documentation) > 200:
            score += 10
        
        # Check for code examples (20 points)
        if '```hcl' in documentation or '```bash' in documentation:
            score += 20
        elif '```' in documentation:
            score += 10
        
        return min(score, 100)
    
    def _review_validation_status(self, state: TerraformState) -> float:
        """Review validation status"""
        
        validation_results = state.get("validation_results", [])
        
        if not validation_results:
            return 0
        
        passed_validations = sum(1 for r in validation_results if r.passed)
        total_validations = len(validation_results)
        
        base_score = (passed_validations / total_validations) * 100
        
        # Penalty for critical failures
        critical_failures = sum(1 for r in validation_results 
                              if not r.passed and any('critical' in str(error).lower() 
                                                     for error in r.errors))
        
        penalty = min(30, critical_failures * 10)
        
        return max(0, base_score - penalty)
    
    def _review_best_practices(self, state: TerraformState) -> float:
        """Review adherence to best practices"""
        
        score = 0
        generated_code = state.get("generated_code", "")
        
        # Check for proper module structure (25 points)
        required_files = ['main.tf', 'variables.tf', 'outputs.tf', 'providers.tf']
        generated_module = context_manager.retrieve_context(state["workflow_id"], "generated_module")
        
        if generated_module:
            found_files = sum(1 for file in required_files 
                            if getattr(generated_module, file.replace('.tf', '_tf'), None))
            score += (found_files / len(required_files)) * 25
        
        # Check for proper tagging (25 points)
        if 'tags' in generated_code and 'Environment' in generated_code:
            score += 25
        elif 'tags' in generated_code:
            score += 15
        
        # Check for variable validation (25 points)
        if 'validation {' in generated_code:
            score += 25
        
        # Check for output descriptions (25 points)
        if 'description =' in generated_code:
            score += 25
        
        return min(score, 100)
    
    def _generate_recommendations(self, review_results: Dict[str, Any], state: TerraformState) -> List[str]:
        """Generate recommendations based on review"""
        
        recommendations = []
        
        if review_results["code_quality"] < 80:
            recommendations.append("Improve code formatting and add more comments")
        
        if review_results["security_compliance"] < 80:
            recommendations.append("Address security validation issues and add security features")
        
        if review_results["documentation_quality"] < 80:
            recommendations.append("Enhance documentation with more sections and examples")
        
        if review_results["validation_status"] < 80:
            recommendations.append("Fix validation errors before deployment")
        
        if review_results["best_practices"] < 80:
            recommendations.append("Follow Terraform best practices for module structure")
        
        # Add specific recommendations based on validation results
        validation_results = state.get("validation_results", [])
        failed_tools = [r.tool for r in validation_results if not r.passed]
        
        if 'terraform_fmt' in failed_tools:
            recommendations.append("Run 'terraform fmt' to fix formatting issues")
        
        if 'trivy' in failed_tools:
            recommendations.append("Review and fix security vulnerabilities")
        
        if 'tflint_avm' in failed_tools:
            recommendations.append("Address TFLint warnings for better code quality")
        
        return recommendations
    
    def _identify_strengths(self, review_results: Dict[str, Any], state: TerraformState) -> List[str]:
        """Identify strengths in the generated code"""
        
        strengths = []
        
        if review_results["code_quality"] >= 80:
            strengths.append("High code quality with proper structure and formatting")
        
        if review_results["security_compliance"] >= 80:
            strengths.append("Strong security compliance with best practices")
        
        if review_results["documentation_quality"] >= 80:
            strengths.append("Comprehensive documentation with clear examples")
        
        if review_results["validation_status"] >= 80:
            strengths.append("Passes validation checks successfully")
        
        if review_results["best_practices"] >= 80:
            strengths.append("Follows Terraform and cloud provider best practices")
        
        # Check for specific good practices
        generated_code = state.get("generated_code", "")
        
        if 'validation {' in generated_code:
            strengths.append("Includes variable validation for input safety")
        
        if 'description =' in generated_code:
            strengths.append("Well-documented variables and outputs")
        
        if 'tags' in generated_code:
            strengths.append("Implements proper resource tagging")
        
        return strengths
    
    def _identify_improvements(self, review_results: Dict[str, Any], state: TerraformState) -> List[str]:
        """Identify areas for improvement"""
        
        improvements = []
        
        if review_results["code_quality"] < 60:
            improvements.append("Code structure and formatting need significant improvement")
        
        if review_results["security_compliance"] < 60:
            improvements.append("Security posture requires immediate attention")
        
        if review_results["documentation_quality"] < 60:
            improvements.append("Documentation is insufficient for production use")
        
        if review_results["validation_status"] < 60:
            improvements.append("Multiple validation failures need resolution")
        
        if review_results["best_practices"] < 60:
            improvements.append("Does not follow established best practices")
        
        return improvements
    
    def _generate_review_message(self, review_results: Dict[str, Any]) -> str:
        """Generate final review message"""
        
        quality_score = review_results["overall_quality"]
        
        # Determine quality level
        if quality_score >= 90:
            quality_level = "Excellent"
            emoji = "🌟"
        elif quality_score >= 80:
            quality_level = "Good"
            emoji = "✅"
        elif quality_score >= 70:
            quality_level = "Satisfactory"
            emoji = "⚠️"
        elif quality_score >= 60:
            quality_level = "Needs Improvement"
            emoji = "⚠️"
        else:
            quality_level = "Poor"
            emoji = "❌"
        
        message_lines = [
            f"{emoji} Final Quality Review Complete",
            f"",
            f"📊 Overall Quality Score: {quality_score:.1f}/100 ({quality_level})",
            f"",
            f"📈 Detailed Scores:",
            f"   • Code Quality: {review_results['code_quality']:.1f}/100",
            f"   • Security Compliance: {review_results['security_compliance']:.1f}/100",
            f"   • Documentation Quality: {review_results['documentation_quality']:.1f}/100",
            f"   • Validation Status: {review_results['validation_status']:.1f}/100",
            f"   • Best Practices: {review_results['best_practices']:.1f}/100"
        ]
        
        # Add strengths
        if review_results["strengths"]:
            message_lines.extend([
                f"",
                f"💪 Strengths:"
            ])
            for strength in review_results["strengths"][:5]:
                message_lines.append(f"   • {strength}")
        
        # Add recommendations
        if review_results["recommendations"]:
            message_lines.extend([
                f"",
                f"💡 Recommendations:"
            ])
            for rec in review_results["recommendations"][:5]:
                message_lines.append(f"   • {rec}")
        
        # Add areas for improvement
        if review_results["areas_for_improvement"]:
            message_lines.extend([
                f"",
                f"🔧 Areas for Improvement:"
            ])
            for improvement in review_results["areas_for_improvement"][:3]:
                message_lines.append(f"   • {improvement}")
        
        # Add final verdict
        if quality_score >= 80:
            message_lines.extend([
                f"",
                f"🎉 **Ready for Production Deployment**",
                f"The generated Terraform module meets quality standards and is ready for use."
            ])
        elif quality_score >= 60:
            message_lines.extend([
                f"",
                f"⚠️ **Ready with Caution**",
                f"The module is functional but consider addressing recommendations before production use."
            ])
        else:
            message_lines.extend([
                f"",
                f"❌ **Requires Improvement**",
                f"The module needs significant improvements before production deployment."
            ])
        
        return "\n".join(message_lines) 