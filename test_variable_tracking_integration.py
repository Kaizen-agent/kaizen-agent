#!/usr/bin/env python3
"""Integration test to verify variable tracking works end-to-end."""

import yaml
import tempfile
import os
import sys
from pathlib import Path

# Add the kaizen package to the path
sys.path.insert(0, str(Path(__file__).parent))

# Test configuration with variable tracking
test_config = """
name: Variable Tracking Integration Test
agent_type: dynamic_region
file_path: test_agent.py
description: Test variable tracking functionality end-to-end

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

def test_variable_tracking_integration():
    """Test the complete variable tracking integration."""
    
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
        
        # Load configuration
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        print("\n=== Testing TestRunner Integration ===")
        
        try:
            from kaizen.autofix.test.runner import TestRunner
            
            # Create test runner
            runner = TestRunner(config)
            runner.config_file_path = config_file
            
            # Run the tests
            results = runner.run_tests(agent_file)
            
            print(f"Test results: {results}")
            
            # Check if variable tracking worked
            if 'Test Variable Tracking' in results:
                test_result = results['Test Variable Tracking']
                tracked_values = test_result.get('test_cases', [{}])[0].get('tracked_values')
                
                print(f"\nTracked values: {tracked_values}")
                
                if tracked_values:
                    if 'summary_text' in tracked_values:
                        print("✅ summary_text was tracked!")
                        print(f"   Value: {tracked_values['summary_text']}")
                    else:
                        print("❌ summary_text was NOT tracked!")
                    
                    if 'safety_recommendations' in tracked_values:
                        print("✅ safety_recommendations was tracked!")
                        print(f"   Value: {tracked_values['safety_recommendations']}")
                    else:
                        print("❌ safety_recommendations was NOT tracked!")
                    
                    if 'return' in tracked_values:
                        print("✅ return value was tracked!")
                        print(f"   Value: {tracked_values['return']}")
                    else:
                        print("❌ return value was NOT tracked!")
                else:
                    print("❌ No tracked values found!")
                    
                # Check LLM evaluation
                llm_evaluation = test_result.get('test_cases', [{}])[0].get('llm_evaluation', {})
                print(f"\nLLM Evaluation: {llm_evaluation}")
                
                if llm_evaluation.get('status') == 'passed':
                    print("✅ LLM evaluation passed!")
                else:
                    print(f"❌ LLM evaluation failed: {llm_evaluation.get('reasoning', 'Unknown error')}")
                    
            else:
                print("❌ Test case not found in results!")
                
        except Exception as e:
            print(f"❌ Error running integration test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_variable_tracking_integration() 