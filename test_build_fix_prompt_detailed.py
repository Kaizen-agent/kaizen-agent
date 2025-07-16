#!/usr/bin/env python3
"""
Detailed test script to verify build_fix_prompt output content.
"""

import sys
import os
from typing import Dict, Any

# Add the kaizen package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'kaizen'))

from kaizen.autofix.code.llm_fixer import PromptBuilder

def create_sample_learning_context() -> Dict[str, Any]:
    """Create a sample learning context from get_previous_attempts_insights."""
    return {
        'failed_cases_current': [
            {
                'name': 'test_agent_functionality',
                'status': 'failed',
                'error_message': 'TypeError: NoneType object is not callable'
            },
            {
                'name': 'test_agent_initialization',
                'status': 'failed',
                'error_message': 'AttributeError: AgentClass has no attribute process_input'
            }
        ],
        'previous_attempts_history': [
            {
                'attempt_number': 1,
                'approach_taken': 'Added error handling to main method',
                'code_changes_made': 'Added try-catch blocks',
                'llm_reasoning': 'Error handling needed for robustness',
                'why_it_failed': 'Still getting TypeError on line 45',
                'test_results_after': {'passed': 0, 'failed': 2},
                'lessons_learned': 'Need to fix the root cause, not just add error handling'
            }
        ],
        'failed_approaches_to_avoid': [
            'Added error handling to main method: Still getting TypeError on line 45'
        ],
        'successful_patterns_to_build_on': [
            'Fixed method signature: Method now exists but logic is wrong'
        ],
        'what_not_to_try_again': [
            {
                'failed_approach': 'Added error handling to main method',
                'why_failed': 'Still getting TypeError on line 45',
                'lesson': 'Need to fix the root cause, not just add error handling'
            }
        ],
        'insights_from_llm_reasoning': [],  # Removed - not currently used
        'original_code_sections': {
            'AgentClass': {
                'line_start': 10,
                'line_end': 50,
                'content': 'class AgentClass:\n    def process_input(self, data):\n        # ...'
            }
        },
        'digested_knowledge_summary': {
            'key_learnings': ['Fix root cause before adding error handling'],
            'successful_patterns': ['Method signature fixes'],
            'failed_patterns': ['Adding error handling without fixing root cause']
        },
        'configuration_factors': {
            'current_config': {'max_retries': 3, 'language': 'python'},
            'config_influence_on_attempts': {'retry_count': 1, 'language_specific': True}
        }
    }

def create_sample_targeting_context() -> Dict[str, Any]:
    """Create a sample targeting context from get_failure_analysis_data."""
    return {
        'original_relevant_sections': {
            'AgentClass.process_input': {
                'line_start': 15,
                'line_end': 35,
                'content': 'def process_input(self, data):\n    # ...'
            },
            'AgentClass.__init__': {
                'line_start': 10,
                'line_end': 14,
                'content': 'def __init__(self):\n    # ...'
            }
        },
        'failing_functions': ['process_input', '__init__'],
        'failing_lines': [15, 22, 25, 30],
        'test_names': ['test_agent_functionality', 'test_agent_initialization'],
        'error_messages': [
            'TypeError: NoneType object is not callable on line 22',
            'AttributeError: AgentClass has no attribute process_input on line 15'
        ],
        'error_types': ['TypeError', 'AttributeError'],
        'failed_test_cases': [
            {
                'test_name': 'test_agent_functionality',
                'status': 'failed',
                'error_message': 'TypeError: NoneType object is not callable on line 22'
            },
            {
                'test_name': 'test_agent_initialization',
                'status': 'failed',
                'error_message': 'AttributeError: AgentClass has no attribute process_input on line 15'
            }
        ],
        'best_attempt_so_far': {
            'success_rate': 0.0,
            'attempt_number': 1,
            'approach_description': 'Added error handling'
        },
        'regression_analysis': {
            'new_failures': 0,
            'fixed_failures': 0,
            'remaining_failures': 2
        }
    }

def create_sample_config():
    """Create a sample test configuration."""
    class MockConfig:
        def __init__(self):
            self.name = "Test Agent Configuration"
            self.description = "Test configuration for agent functionality"
            self.goal = "Fix agent class issues"
            self.language = "python"
            self.metadata = {"language": "python"}
    
    return MockConfig()

def test_detailed_prompt_output():
    """Test and display the detailed prompt output."""
    print("🔍 Testing detailed prompt output...\n")
    
    # Create sample inputs
    content = """class AgentClass:
    def __init__(self):
        self.data = None
    
    def process_input(self, data):
        # This method has issues
        result = self.data.process(data)  # Line 22 - TypeError here
        return result
"""
    file_path = "test_agent.py"
    learning_context = create_sample_learning_context()
    targeting_context = create_sample_targeting_context()
    config = create_sample_config()
    context_files = {
        "utils.py": "def helper_function():\n    return 'helper'",
        "config.py": "MAX_RETRIES = 3"
    }
    
    try:
        # Generate the prompt
        prompt = PromptBuilder.build_fix_prompt(
            content=content,
            file_path=file_path,
            learning_context=learning_context,
            targeting_context=targeting_context,
            config=config,
            context_files=context_files
        )
        
        print("📋 Generated Prompt Preview:")
        print("=" * 80)
        
        # Show key sections
        sections = prompt.split('\n\n')
        for i, section in enumerate(sections):
            if i < 3:  # Show first 3 sections (base prompt)
                print(f"Section {i+1}:")
                print(section[:200] + "..." if len(section) > 200 else section)
                print("-" * 40)
            elif "LEARNING FROM PREVIOUS ATTEMPTS" in section:
                print("🧠 LEARNING CONTEXT SECTION:")
                print(section)
                print("-" * 40)
            elif "TARGETING CONTEXT FOR FAILURE ANALYSIS" in section:
                print("🎯 TARGETING CONTEXT SECTION:")
                print(section)
                print("-" * 40)
            elif "Configuration Context:" in section:
                print("⚙️ CONFIGURATION SECTION:")
                print(section)
                print("-" * 40)
            elif "Related Files" in section:
                print("📁 CONTEXT FILES SECTION:")
                print(section)
                print("-" * 40)
        
        # Verify key surgical targeting requirements
        surgical_checks = [
            "🔴 CRITICAL: SURGICAL TARGETING REQUIREMENTS",
            "ONLY fix code in the following relevant sections:",
            "AgentClass.process_input (lines 15-35)",
            "AgentClass.__init__ (lines 10-14)",
            "DO NOT modify any code outside these sections",
            "Focus ONLY on the specific agent class, methods used in that class, or imports needed by that class"
        ]
        
        print("\n✅ SURGICAL TARGETING VERIFICATION:")
        for check in surgical_checks:
            if check in prompt:
                print(f"  ✅ Found: {check}")
            else:
                print(f"  ❌ Missing: {check}")
        
        # Verify learning context
        learning_checks = [
            "LEARNING FROM PREVIOUS ATTEMPTS (Attempt 2 of 1):",
            "Current failed test cases: 2 cases",
            "What worked in previous attempts:",
            "What didn't work:",
            "Detailed failure analysis:",
            "LLM reasoning insights:",
            "Key learnings summary:",
            "Configuration context:",
            "Original code context available for reference"
        ]
        
        print("\n✅ LEARNING CONTEXT VERIFICATION:")
        for check in learning_checks:
            if check in prompt:
                print(f"  ✅ Found: {check}")
            else:
                print(f"  ❌ Missing: {check}")
        
        # Verify targeting context
        targeting_checks = [
            "Failing functions to fix: process_input, __init__",
            "Specific failing line numbers: 15, 22, 25, 30",
            "Failing test names: test_agent_functionality, test_agent_initialization",
            "Specific error messages to address:",
            "Error types to fix: TypeError, AttributeError",
            "Failed test cases: 2 cases",
            "Best attempt so far:",
            "Success rate: 0.00%",
            "Regression analysis:"
        ]
        
        print("\n✅ TARGETING CONTEXT VERIFICATION:")
        for check in targeting_checks:
            if check in prompt:
                print(f"  ✅ Found: {check}")
            else:
                print(f"  ❌ Missing: {check}")
        
        print(f"\n📊 Prompt Statistics:")
        print(f"  Total length: {len(prompt)} characters")
        print(f"  Number of lines: {len(prompt.split(chr(10)))}")
        print(f"  Contains surgical targeting: {'🔴 CRITICAL: SURGICAL TARGETING REQUIREMENTS' in prompt}")
        print(f"  Contains learning context: {'LEARNING FROM PREVIOUS ATTEMPTS' in prompt}")
        print(f"  Contains targeting context: {'TARGETING CONTEXT FOR FAILURE ANALYSIS' in prompt}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating detailed prompt: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting detailed build_fix_prompt test...\n")
    
    if test_detailed_prompt_output():
        print("\n🎉 Detailed test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Detailed test failed.")
        sys.exit(1) 