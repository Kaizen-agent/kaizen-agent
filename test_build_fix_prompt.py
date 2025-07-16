#!/usr/bin/env python3
"""
Test script to verify build_fix_prompt works properly with new input types.
"""

import sys
import os
from typing import Dict, Any, Optional

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
            },
            {
                'attempt_number': 2,
                'approach_taken': 'Fixed method signature',
                'code_changes_made': 'Changed return type and parameters',
                'llm_reasoning': 'Method signature mismatch causing TypeError',
                'why_it_failed': 'Method now exists but logic is wrong',
                'test_results_after': {'passed': 1, 'failed': 1},
                'lessons_learned': 'Fixed signature but need to fix implementation logic'
            }
        ],
        'failed_approaches_to_avoid': [
            'Added error handling to main method: Still getting TypeError on line 45',
            'Fixed method signature: Method now exists but logic is wrong'
        ],
        'successful_patterns_to_build_on': [
            'Fixed method signature: Method now exists but logic is wrong'
        ],
        'what_not_to_try_again': [
            {
                'failed_approach': 'Added error handling to main method',
                'why_failed': 'Still getting TypeError on line 45',
                'lesson': 'Need to fix the root cause, not just add error handling'
            },
            {
                'failed_approach': 'Fixed method signature',
                'why_failed': 'Method now exists but logic is wrong',
                'lesson': 'Fixed signature but need to fix implementation logic'
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
            'key_learnings': ['Fix root cause before adding error handling', 'Method signatures matter'],
            'successful_patterns': ['Method signature fixes'],
            'failed_patterns': ['Adding error handling without fixing root cause']
        },
        'configuration_factors': {
            'current_config': {'max_retries': 3, 'language': 'python'},
            'config_influence_on_attempts': {'retry_count': 2, 'language_specific': True}
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
            'success_rate': 0.5,
            'attempt_number': 2,
            'approach_description': 'Fixed method signature'
        },
        'regression_analysis': {
            'new_failures': 0,
            'fixed_failures': 1,
            'remaining_failures': 1
        }
    }

def create_sample_config() -> Dict[str, Any]:
    """Create a sample test configuration."""
    class MockConfig:
        def __init__(self):
            self.name = "Test Agent Configuration"
            self.description = "Test configuration for agent functionality"
            self.goal = "Fix agent class issues"
            self.language = "python"
            self.metadata = {"language": "python"}
            
            class MockEvaluation:
                def __init__(self):
                    self.criteria = ["functionality", "robustness"]
                    self.evaluation_targets = [
                        MockEvaluationTarget("test_agent_functionality", "test", "pass", "Agent functionality test", 1.0),
                        MockEvaluationTarget("test_agent_initialization", "test", "pass", "Agent initialization test", 1.0)
                    ]
            
            self.evaluation = MockEvaluation()
    
    class MockEvaluationTarget:
        def __init__(self, name, source, criteria, description, weight):
            self.name = name
            self.source = source
            self.criteria = criteria
            self.description = description
            self.weight = weight
        
        def to_dict(self):
            return {
                'name': self.name,
                'source': self.source,
                'criteria': self.criteria,
                'description': self.description,
                'weight': self.weight
            }
    
    return MockConfig()

def test_build_fix_prompt_with_new_inputs():
    """Test build_fix_prompt with the new learning_context and targeting_context inputs."""
    print("🧪 Testing build_fix_prompt with new input types...")
    
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
        # Test the build_fix_prompt method
        prompt = PromptBuilder.build_fix_prompt(
            content=content,
            file_path=file_path,
            learning_context=learning_context,
            targeting_context=targeting_context,
            config=config,
            context_files=context_files
        )
        
        print("✅ build_fix_prompt executed successfully!")
        
        # Verify the prompt contains expected sections
        expected_sections = [
            "SURGICAL TARGETING REQUIREMENTS",
            "LEARNING FROM PREVIOUS ATTEMPTS",
            "TARGETING CONTEXT FOR FAILURE ANALYSIS",
            "Configuration Context:",
            "Related Files (for context and dependencies):"
        ]
        
        missing_sections = []
        for section in expected_sections:
            if section not in prompt:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"❌ Missing expected sections: {missing_sections}")
            return False
        
        # Verify specific content from learning context
        learning_checks = [
            "Current failed test cases: 2 cases",
            "What worked in previous attempts:",
            "What didn't work:",
            "Detailed failure analysis:",
            "LLM reasoning insights:",
            "Key learnings summary:",
            "Configuration context:",
            "Original code context available for reference"
        ]
        
        learning_missing = []
        for check in learning_checks:
            if check not in prompt:
                learning_missing.append(check)
        
        if learning_missing:
            print(f"❌ Missing learning context content: {learning_missing}")
            return False
        
        # Verify specific content from targeting context
        targeting_checks = [
            "CRITICAL: SURGICAL TARGETING REQUIREMENTS",
            "ONLY fix code in the following relevant sections:",
            "AgentClass.process_input (lines 15-35)",
            "AgentClass.__init__ (lines 10-14)",
            "DO NOT modify any code outside these sections",
            "Failing functions to fix: process_input, __init__",
            "Specific failing line numbers: 15, 22, 25, 30",
            "Failing test names: test_agent_functionality, test_agent_initialization",
            "Specific error messages to address:",
            "Error types to fix: TypeError, AttributeError",
            "Failed test cases: 2 cases",
            "Best attempt so far:",
            "Success rate: 50.00%",
            "Regression analysis:"
        ]
        
        targeting_missing = []
        for check in targeting_checks:
            if check not in prompt:
                targeting_missing.append(check)
        
        if targeting_missing:
            print(f"❌ Missing targeting context content: {targeting_missing}")
            return False
        
        print("✅ All expected sections and content found in prompt!")
        
        # Test edge cases
        print("\n🧪 Testing edge cases...")
        
        # Test with empty learning context
        empty_learning_prompt = PromptBuilder.build_fix_prompt(
            content=content,
            file_path=file_path,
            learning_context={},
            targeting_context=targeting_context,
            config=config,
            context_files=context_files
        )
        
        if "LEARNING FROM PREVIOUS ATTEMPTS" in empty_learning_prompt:
            print("❌ Learning section should not appear with empty learning context")
            return False
        
        print("✅ Empty learning context handled correctly")
        
        # Test with empty targeting context
        empty_targeting_prompt = PromptBuilder.build_fix_prompt(
            content=content,
            file_path=file_path,
            learning_context=learning_context,
            targeting_context={},
            config=config,
            context_files=context_files
        )
        
        if "TARGETING CONTEXT FOR FAILURE ANALYSIS" in empty_targeting_prompt:
            print("❌ Targeting section should not appear with empty targeting context")
            return False
        
        print("✅ Empty targeting context handled correctly")
        
        # Test with None values
        none_prompt = PromptBuilder.build_fix_prompt(
            content=content,
            file_path=file_path,
            learning_context=None,
            targeting_context=None,
            config=None,
            context_files=None
        )
        
        if "LEARNING FROM PREVIOUS ATTEMPTS" in none_prompt or "TARGETING CONTEXT FOR FAILURE ANALYSIS" in none_prompt:
            print("❌ Sections should not appear with None values")
            return False
        
        print("✅ None values handled correctly")
        
        print("\n🎉 All tests passed! build_fix_prompt works correctly with new input types.")
        return True
        
    except Exception as e:
        print(f"❌ Error testing build_fix_prompt: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_build_fix_prompt_with_typescript():
    """Test build_fix_prompt with TypeScript configuration."""
    print("\n🧪 Testing build_fix_prompt with TypeScript...")
    
    content = """interface AgentInterface {
    processInput(data: any): any;
}

class AgentClass implements AgentInterface {
    private data: any;
    
    constructor() {
        this.data = null;
    }
    
    processInput(data: any): any {
        // This method has issues
        return this.data.process(data);  // TypeError here
    }
}
"""
    file_path = "test_agent.ts"
    
    # Create TypeScript config
    class MockTypeScriptConfig:
        def __init__(self):
            self.name = "TypeScript Agent Configuration"
            self.description = "Test configuration for TypeScript agent"
            self.goal = "Fix TypeScript agent class issues"
            self.language = "typescript"
            self.metadata = {"language": "typescript"}
    
    config = MockTypeScriptConfig()
    learning_context = create_sample_learning_context()
    targeting_context = create_sample_targeting_context()
    
    try:
        prompt = PromptBuilder.build_fix_prompt(
            content=content,
            file_path=file_path,
            learning_context=learning_context,
            targeting_context=targeting_context,
            config=config,
            context_files={}
        )
        
        # Check for TypeScript-specific content
        if "TypeScript" not in prompt or "```ts" not in prompt:
            print("❌ TypeScript-specific content not found in prompt")
            return False
        
        print("✅ TypeScript configuration handled correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error testing TypeScript build_fix_prompt: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting build_fix_prompt tests...\n")
    
    success = True
    
    # Test main functionality
    if not test_build_fix_prompt_with_new_inputs():
        success = False
    
    # Test TypeScript
    if not test_build_fix_prompt_with_typescript():
        success = False
    
    if success:
        print("\n🎉 All tests passed! build_fix_prompt is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1) 