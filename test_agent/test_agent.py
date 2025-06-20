"""Sample test agent that demonstrates multiple input handling.

This agent shows how to handle different types of inputs:
- String inputs
- Dictionary inputs
- Object inputs (with dynamic imports)
- Mixed input types
"""

import logging
from typing import Any, List, Dict, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AgentResponse:
    """Response from the test agent."""
    message: str
    confidence: float
    metadata: Dict[str, Any]

class TestAgent:
    """Sample test agent that handles multiple inputs."""
    
    def __init__(self):
        """Initialize the test agent."""
        self.name = "TestAgent"
        self.version = "1.0.0"
        logger.info(f"Initialized {self.name} v{self.version}")
    
    def run(self, *inputs: Any) -> AgentResponse:
        """Run the agent with multiple inputs.
        
        Args:
            *inputs: Variable number of inputs of different types
            
        Returns:
            AgentResponse containing the processed result
        """
        logger.info(f"Processing {len(inputs)} input(s)")
        
        # Process each input based on its type
        processed_inputs = []
        input_types = []
        
        for i, input_item in enumerate(inputs):
            input_type = type(input_item).__name__
            input_types.append(input_type)
            
            if isinstance(input_item, str):
                processed_inputs.append(f"String input {i+1}: {input_item}")
            elif isinstance(input_item, dict):
                processed_inputs.append(f"Dict input {i+1}: {input_item}")
            elif hasattr(input_item, 'to_dict'):
                # Handle object inputs that have a to_dict method
                processed_inputs.append(f"Object input {i+1}: {input_item.to_dict()}")
            else:
                processed_inputs.append(f"Unknown input {i+1}: {input_item}")
        
        # Generate response based on input types
        if len(inputs) == 0:
            message = "No inputs provided"
            confidence = 0.0
        elif len(inputs) == 1:
            message = f"Processed single {input_types[0]} input: {processed_inputs[0]}"
            confidence = 0.8
        else:
            message = f"Processed {len(inputs)} inputs of types: {', '.join(input_types)}"
            confidence = 0.9
        
        # Create metadata
        metadata = {
            'input_count': len(inputs),
            'input_types': input_types,
            'processed_inputs': processed_inputs,
            'agent_name': self.name,
            'agent_version': self.version
        }
        
        logger.info(f"Generated response: {message}")
        return AgentResponse(message=message, confidence=confidence, metadata=metadata)
    
    def process_chemistry_query(self, *inputs: Any) -> AgentResponse:
        """Process chemistry-related queries with multiple inputs.
        
        Args:
            *inputs: Variable number of inputs (feedback, context, query, etc.)
            
        Returns:
            AgentResponse containing chemistry analysis
        """
        logger.info(f"Processing chemistry query with {len(inputs)} input(s)")
        
        # Extract different types of inputs
        feedback = None
        context = None
        query = None
        compound_data = None
        
        for input_item in inputs:
            if hasattr(input_item, 'text') and hasattr(input_item, 'tags'):
                # Likely a ChemistFeedback object
                feedback = input_item
            elif isinstance(input_item, dict) and 'temperature' in input_item:
                # Likely experimental context
                context = input_item
            elif isinstance(input_item, str) and '?' in input_item:
                # Likely a query string
                query = input_item
            elif hasattr(input_item, 'name') and hasattr(input_item, 'molecular_weight'):
                # Likely compound data
                compound_data = input_item
        
        # Generate chemistry-specific response
        if feedback and context and query:
            message = f"Chemistry analysis: Based on feedback '{feedback.text}' and context {context}, responding to query: {query}"
            confidence = 0.95
        elif query and compound_data:
            message = f"Compound analysis: Analyzing {compound_data.name} (MW: {compound_data.molecular_weight}) for query: {query}"
            confidence = 0.9
        else:
            message = f"General chemistry processing with {len(inputs)} inputs"
            confidence = 0.7
        
        metadata = {
            'input_count': len(inputs),
            'feedback_provided': feedback is not None,
            'context_provided': context is not None,
            'query_provided': query is not None,
            'compound_data_provided': compound_data is not None,
            'agent_name': self.name,
            'agent_version': self.version
        }
        
        return AgentResponse(message=message, confidence=confidence, metadata=metadata)
    
    def analyze_experiment(self, *inputs: Any) -> AgentResponse:
        """Analyze experimental data with multiple inputs.
        
        Args:
            *inputs: Variable number of inputs (context, data, parameters, etc.)
            
        Returns:
            AgentResponse containing experiment analysis
        """
        logger.info(f"Analyzing experiment with {len(inputs)} input(s)")
        
        # Process experimental inputs
        analysis_parts = []
        for i, input_item in enumerate(inputs):
            if isinstance(input_item, dict):
                analysis_parts.append(f"Data {i+1}: {input_item}")
            elif hasattr(input_item, 'to_dict'):
                analysis_parts.append(f"Object {i+1}: {input_item.to_dict()}")
            else:
                analysis_parts.append(f"Input {i+1}: {input_item}")
        
        message = f"Experiment analysis: {'; '.join(analysis_parts)}"
        confidence = 0.85
        
        metadata = {
            'input_count': len(inputs),
            'analysis_parts': analysis_parts,
            'agent_name': self.name,
            'agent_version': self.version
        }
        
        return AgentResponse(message=message, confidence=confidence, metadata=metadata)

# Create a global instance for testing
test_agent = TestAgent() 