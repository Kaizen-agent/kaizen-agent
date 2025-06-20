"""Integration test for flexible evaluation system."""

import tempfile
import os
from pathlib import Path

def test_flexible_evaluation_integration():
    """Test the complete flexible evaluation flow."""
    
    # Create a simple test agent
    agent_code = '''
class TestAgent:
    def __init__(self):
        self.summary_text = ""
        self.recommendations = ""
    
    def process_query(self, query):
        # Set variables that will be tracked
        self.summary_text = "The compound shows moderate instability in ethanol."
        self.recommendations = "Try using dichloromethane as an alternative solvent."
        
        return {
            "status": "completed",
            "summary": self.summary_text,
            "recommendations": self.recommendations
        }
'''
    
    # Create test configuration
    test_config = {
        'name': 'Test Agent',
        'agent_type': 'dynamic_region',
        'file_path': 'test_agent.py',
        'evaluation': {
            'evaluation_targets': [
                {
                    'name': 'summary_text',
                    'source': 'variable',
                    'criteria': 'Should include clarification about stability'
                },
                {
                    'name': 'recommendations',
                    'source': 'variable',
                    'criteria': 'Should suggest alternative solvents'
                },
                {
                    'name': 'return',
                    'source': 'return',
                    'criteria': 'Should be a dictionary with status and summary keys'
                }
            ]
        },
        'regions': ['TestAgent'],
        'steps': [
            {
                'name': 'Test Step',
                'input': {
                    'file_path': 'test_agent.py',
                    'method': 'process_query',
                    'input': 'How stable is this compound?'
                }
            }
        ]
    }
    
    # Test the evaluation model parsing
    from kaizen.cli.commands.models.evaluation import TestEvaluation
    evaluation = TestEvaluation.from_dict(test_config['evaluation'])
    
    assert len(evaluation.evaluation_targets) == 3
    assert evaluation.evaluation_targets[0].name == 'summary_text'
    assert evaluation.evaluation_targets[0].source.value == 'variable'
    assert evaluation.evaluation_targets[1].name == 'recommendations'
    assert evaluation.evaluation_targets[1].source.value == 'variable'
    assert evaluation.evaluation_targets[2].name == 'return'
    assert evaluation.evaluation_targets[2].source.value == 'return'
    
    # Test variable tracking
    from kaizen.autofix.test.variable_tracker import VariableTracker, safe_serialize_value
    
    tracker = VariableTracker()
    tracker.start_tracking({'summary_text', 'recommendations'})
    
    # Simulate variable assignments
    test_namespace = {
        'summary_text': 'The compound shows moderate instability in ethanol.',
        'recommendations': 'Try using dichloromethane as an alternative solvent.'
    }
    
    # Mock frame for testing
    from unittest.mock import Mock
    mock_frame = Mock()
    mock_frame.f_locals = test_namespace
    mock_frame.f_lineno = 10
    
    tracker._track_line_variables(mock_frame)
    
    # Check tracked values
    assert tracker.get_variable_value('summary_text') == 'The compound shows moderate instability in ethanol.'
    assert tracker.get_variable_value('recommendations') == 'Try using dichloromethane as an alternative solvent.'
    
    # Test serialization
    serialized_summary = safe_serialize_value(tracker.get_variable_value('summary_text'))
    assert 'instability' in serialized_summary
    
    tracker.stop_tracking()
    
    print("✅ All integration tests passed!")

if __name__ == "__main__":
    test_flexible_evaluation_integration() 