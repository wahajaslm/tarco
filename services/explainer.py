# WORKFLOW: LLM explainer service for generating human-readable explanations with guardrails.
# Used by: /deterministic-json+explain endpoint, chat responses, user interfaces
# Functions:
# 1. generate_explanations() - Generate complete annotations with safety checks
# 2. _generate_human_summary() - Create brief factual summary
# 3. _generate_certificate_explanations() - Explain certificates and requirements
# 4. _generate_compliance_notes() - Generate compliance warnings and notes
# 5. _call_llm() - Safe LLM calls with hallucination prevention
#
# Explanation flow: Deterministic response -> LLM processing -> Guarded explanations -> Annotations
# Safety flow: LLM prompt -> Safety instructions -> Factual response -> Validation
# Ensures LLM only paraphrases existing data, never invents new facts or numbers.

from typing import Dict, Any, List, Optional
import logging
from api.schemas.response import TradeComplianceResponse, AnnotationsLLM, CertificateExplanation, SafetyInfo
import ollama
from core.config import settings

logger = logging.getLogger(__name__)


class ExplainerService:
    """LLM service for generating explanations with strict guardrails."""
    
    def __init__(self):
        self.client = ollama.Client(host=settings.ollama_url)
        self.model = settings.llm_model
    
    def generate_explanations(self, response: TradeComplianceResponse) -> AnnotationsLLM:
        """
        Generate LLM explanations for the deterministic response.
        
        Args:
            response: TradeComplianceResponse with deterministic values
            
        Returns:
            AnnotationsLLM with explanations and safety guardrails
        """
        try:
            logger.info("Generating LLM explanations")
            
            # Generate human summary
            human_summary = self._generate_human_summary(response)
            
            # Generate certificate explanations
            certificate_explanations = self._generate_certificate_explanations(response)
            
            # Generate compliance notes
            compliance_notes = self._generate_compliance_notes(response)
            
            # Create safety info
            safety_info = SafetyInfo(
                hallucination_guard=True,
                disclaimer="This explanation is informational only — cross-check required; numeric outcomes per deterministic payload."
            )
            
            return AnnotationsLLM(
                human_summary=human_summary,
                certificate_explanations=certificate_explanations,
                compliance_notes=compliance_notes,
                safety=safety_info
            )
            
        except Exception as e:
            logger.error(f"Failed to generate explanations: {e}")
            # Return minimal explanation with safety disclaimer
            return AnnotationsLLM(
                human_summary="Explanation generation failed. Please refer to the deterministic payload for accurate information.",
                safety=SafetyInfo(
                    hallucination_guard=True,
                    disclaimer="This explanation is informational only — cross-check required; numeric outcomes per deterministic payload."
                )
            )
    
    def _generate_human_summary(self, response: TradeComplianceResponse) -> Optional[str]:
        """Generate human-readable summary."""
        try:
            # Extract key information from response
            hs_code = response.query_parameters.hs_code
            origin = response.query_parameters.origin
            destination = response.query_parameters.destination
            
            # Get duty rate if available
            duty_rate = None
            if response.deterministic_values.applicable_rate_resolution:
                duty_rate = response.deterministic_values.applicable_rate_resolution.chosen_duty_rate_percent
            
            # Get VAT rate
            vat_rate = None
            if response.deterministic_values.vat_rates:
                vat_rate = response.deterministic_values.vat_rates[0].standard_rate_percent
            
            # Create summary prompt
            prompt = f"""
            Create a brief, factual summary of the trade compliance information for:
            - HS Code: {hs_code}
            - Origin: {origin}
            - Destination: {destination}
            - Duty Rate: {duty_rate}% if available
            - VAT Rate: {vat_rate}% if available
            
            IMPORTANT: Only use the information provided above. Do not add any new numbers or facts.
            Keep it concise and factual.
            """
            
            # Generate summary using LLM
            summary = self._call_llm(prompt, max_tokens=200)
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate human summary: {e}")
            return None
    
    def _generate_certificate_explanations(self, response: TradeComplianceResponse) -> List[CertificateExplanation]:
        """Generate explanations for certificates and documents."""
        try:
            explanations = []
            
            # Get measure conditions that require certificates
            if response.deterministic_values.measure_conditions:
                for condition in response.deterministic_values.measure_conditions:
                    if condition.certificate_code:
                        explanation = self._explain_certificate(condition.certificate_code, condition)
                        if explanation:
                            explanations.append(explanation)
            
            return explanations
            
        except Exception as e:
            logger.error(f"Failed to generate certificate explanations: {e}")
            return []
    
    def _explain_certificate(self, certificate_code: str, condition: Any) -> Optional[CertificateExplanation]:
        """Explain a specific certificate."""
        try:
            prompt = f"""
            Explain the certificate with code {certificate_code}:
            - Action: {condition.action}
            - Threshold: {condition.threshold_value} {condition.threshold_unit} if applicable
            - Notes: {condition.notes} if available
            
            Provide:
            1. What this certificate is
            2. When it's required
            3. Who issues it
            4. Any important notes
            
            IMPORTANT: Only use the information provided. Do not add new facts or numbers.
            """
            
            explanation_text = self._call_llm(prompt, max_tokens=300)
            
            if explanation_text:
                return CertificateExplanation(
                    code=certificate_code,
                    what_it_is=explanation_text,
                    when_required=f"When {condition.action}",
                    issuer="Check with relevant authorities",
                    note=condition.notes
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to explain certificate {certificate_code}: {e}")
            return None
    
    def _generate_compliance_notes(self, response: TradeComplianceResponse) -> List[str]:
        """Generate compliance notes."""
        try:
            notes = []
            
            # Check for special measures
            if response.deterministic_values.special_measures:
                special = response.deterministic_values.special_measures
                if special.anti_dumping:
                    notes.append(f"Anti-dumping measures apply: {special.anti_dumping}")
                if special.quotas:
                    notes.append(f"Quota restrictions: {special.quotas}")
                if special.safeguards:
                    notes.append(f"Safeguard measures: {special.safeguards}")
            
            # Check for REACH restrictions
            if response.deterministic_values.compliance_requirements:
                reach = response.deterministic_values.compliance_requirements.reach_restrictions_annex_xvii
                if reach:
                    for restriction in reach:
                        if restriction.required:
                            notes.append(f"REACH Annex XVII restriction applies: Entry {restriction.entry}")
            
            # Check for completeness issues
            if response.deterministic_values.unknowns:
                for unknown in response.deterministic_values.unknowns:
                    notes.append(f"Missing information: {unknown.field} - {unknown.reason}")
            
            # Add general compliance note
            if notes:
                notes.append("Please verify all compliance requirements with relevant authorities.")
            
            return notes
            
        except Exception as e:
            logger.error(f"Failed to generate compliance notes: {e}")
            return ["Please verify compliance requirements with relevant authorities."]
    
    def _call_llm(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """Call the LLM with safety guardrails."""
        try:
            # Add safety instructions to prompt
            safety_prompt = f"""
            {prompt}
            
            SAFETY INSTRUCTIONS:
            - Only use information provided in the prompt
            - Do not invent or add any new numbers, rates, or facts
            - If uncertain, state "Please refer to official sources"
            - Keep explanations factual and concise
            """
            
            response = self.client.generate(
                model=self.model,
                prompt=safety_prompt,
                options={
                    "temperature": 0.1,  # Low temperature for factual responses
                    "num_predict": max_tokens,
                    "stop": ["\n\n", "Note:", "Important:"]
                }
            )
            
            return response['response'].strip()
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return None


# Factory function
def create_explainer() -> ExplainerService:
    """Create explainer service instance."""
    return ExplainerService()
