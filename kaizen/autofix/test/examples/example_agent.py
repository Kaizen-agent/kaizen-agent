"""Example agent for demonstrating flexible output evaluation."""

import json
from typing import Dict, Any, List

# kaizen:start:example_agent
class ExampleAgent:
    """Example agent that produces multiple outputs for testing flexible evaluation."""
    
    def __init__(self):
        """Initialize the example agent."""
        self.summary_text = ""
        self.recommended_action = ""
        self.analysis_results = {}
    
    def analyze_compound(self, query: str) -> Dict[str, Any]:
        """Analyze compound stability and return results.
        
        Args:
            query: Query about compound stability
            
        Returns:
            Dictionary with analysis results
        """
        # Set multiple outputs for evaluation
        self.summary_text = "The compound shows moderate instability in ethanol due to its polar nature. Consider using a less polar solvent."
        self.recommended_action = "Try using dichloromethane or ethyl acetate as alternative solvents. Run a small-scale test first."
        self.analysis_results = {
            "stability_score": 0.3,
            "risk_factors": ["polar solvent", "temperature sensitivity"],
            "recommendations": ["use less polar solvent", "maintain low temperature"]
        }
        
        return {
            "status": "completed",
            "summary": self.summary_text,
            "recommendations": self.recommended_action,
            "details": self.analysis_results
        }
    
    def suggest_alternatives(self, query: str) -> Dict[str, Any]:
        """Suggest alternative solvents for unstable compounds.
        
        Args:
            query: Query about alternative solvents
            
        Returns:
            Dictionary with alternative suggestions
        """
        # Set multiple outputs for evaluation
        self.summary_text = "Based on the instability in ethanol, several alternative solvents are recommended."
        self.recommended_action = "Test the compound in dichloromethane, ethyl acetate, or toluene. Monitor for precipitation or decomposition."
        self.analysis_results = {
            "alternatives": ["dichloromethane", "ethyl acetate", "toluene"],
            "testing_protocol": "Small-scale solubility test",
            "safety_notes": "Use fume hood, check compatibility"
        }
        
        return {
            "status": "completed",
            "summary": self.summary_text,
            "alternatives": self.analysis_results["alternatives"],
            "protocol": self.analysis_results["testing_protocol"]
        }
    
    def get_summary_text(self) -> str:
        """Get the current summary text."""
        return self.summary_text
    
    def get_recommended_action(self) -> str:
        """Get the current recommended action."""
        return self.recommended_action
# kaizen:end:example_agent 