#!/usr/bin/env python3
"""Test script to demonstrate the variable tracking issue."""

import yaml
import tempfile
import os
from pathlib import Path

# Test configuration with variable tracking
test_config = """
name: Variable Tracking Test
agent_type: dynamic_region
file_path: test_agent.py
description: Test variable tracking functionality

evaluation:
  evaluation_targets:
    - name: summary_text
      source: variable
      criteria: "Should include clarification about the compound's instability"
      description: "The summary text should explain stability concerns"
      weight: 1.0

    - name: safety_recommendations
      source: variable
      criteria: "Should provide specific safety precautions"
      description: "Recommendations should be practical and safety-focused"
      weight: 1.0

    - name: return
      source: return
      criteria: "Should return a structured response"
      description: "Return value should be well-structured"
      weight: 1.0

regions:
  - TestAgent

max_retries: 2
files_to_fix:
  - test_agent.py

steps:
  - name: Test Variable Tracking
    description: Test handling of variable tracking
    input:
      file_path: test_agent.py
      method: analyze_compound
      input: "How stable is this compound in ethanol?"
    evaluation:
      type: llm
"""

# Test agent code
test_agent_code = """
class TestAgent:
    def __init__(self):
        self.summary_text = ""
        self.safety_recommendations = ""
    
    def analyze_compound(self, input_data):
        # Set variables that should be tracked
        self.summary_text = "The compound shows moderate instability in ethanol due to its polar nature."
        self.safety_recommendations = "Use appropriate PPE and work in a fume hood. Consider alternative solvents."
        
        # Return structured result
        return {
            "status": "completed",
            "analysis": self.summary_text,
            "recommendations": self.safety_recommendations
        }
"""

def test_variable_tracking():
    """Test the variable tracking functionality."""
    
    # Create temporary files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write test configuration
        config_file = temp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            f.write(test_config)
        
        # Write test agent
        agent_file = temp_path / "test_agent.py"
        with open(agent_file, 'w') as f:
            f.write(test_agent_code)
        
        print(f"Created test files in: {temp_path}")
        print(f"Config file: {config_file}")
        print(f"Agent file: {agent_file}")
        
        # Load and parse the configuration
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        print("\n=== Configuration Analysis ===")
        print(f"Config keys: {list(config.keys())}")
        
        if 'evaluation' in config:
            evaluation = config['evaluation']
            print(f"Evaluation keys: {list(evaluation.keys())}")
            
            if 'evaluation_targets' in evaluation:
                targets = evaluation['evaluation_targets']
                print(f"Found {len(targets)} evaluation targets:")
                
                for i, target in enumerate(targets):
                    print(f"  Target {i+1}:")
                    print(f"    name: {target.get('name')}")
                    print(f"    source: {target.get('source')}")
                    print(f"    criteria: {target.get('criteria')}")
                    
                    # Check if this should trigger variable tracking
                    if target.get('source') == 'variable':
                        print(f"    -> Should track variable: {target.get('name')}")
                    else:
                        print(f"    -> Should NOT track variable")
        
        # Test the TestCase.from_dict method
        print("\n=== TestCase.from_dict Analysis ===")
        try:
            from kaizen.autofix.test.test_case import TestCase
            
            # Create a test case from the first step
            step = config['steps'][0]
            test_case_data = {
                'name': step['name'],
                'input': step['input'],
                'evaluation_targets': config['evaluation']['evaluation_targets']
            }
            
            test_case = TestCase.from_dict(test_case_data)
            print(f"Test case evaluation_targets: {test_case.evaluation_targets}")
            
            # Check which variables should be tracked
            tracked_variables = set()
            for target in test_case.evaluation_targets:
                if target.get('source') == 'variable':
                    tracked_variables.add(target.get('name'))
            
            print(f"Variables that should be tracked: {tracked_variables}")
            
            if tracked_variables:
                print("✅ Variable tracking should work!")
            else:
                print("❌ Variable tracking will NOT work!")
                
        except Exception as e:
            print(f"Error testing TestCase.from_dict: {e}")
        
        # Test the CLI evaluation model
        print("\n=== CLI Evaluation Model Analysis ===")
        try:
            from kaizen.cli.commands.models.evaluation import TestEvaluation
            
            evaluation_model = TestEvaluation.from_dict(config['evaluation'])
            print(f"CLI evaluation targets: {len(evaluation_model.evaluation_targets)}")
            
            for i, target in enumerate(evaluation_model.evaluation_targets):
                print(f"  Target {i+1}: {target.name} (source: {target.source.value})")
                
        except Exception as e:
            print(f"Error testing CLI evaluation model: {e}")

if __name__ == "__main__":
    test_variable_tracking() 