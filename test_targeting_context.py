#!/usr/bin/env python3
"""
Simple test to verify targeting context generation.
"""

import sys
import os

# Add the kaizen package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'kaizen'))

from kaizen.autofix.code.llm_fixer import PromptBuilder

def test_targeting_context():
    """Test targeting context generation."""
    print("🎯 Testing targeting context generation...\n")
    
    content = "class TestClass:\n    pass"
    file_path = "test.py"
    targeting_context = {
        'original_relevant_sections': {
            'TestClass.method1': {
                'line_start': 10,
                'line_end': 20,
                'content': 'def method1(self):\n    pass'
            }
        },
        'failing_functions': ['method1'],
        'failing_lines': [12, 15],
        'test_names': ['test_method1'],
        'error_messages': ['TypeError: test error'],
        'error_types': ['TypeError'],
        'failed_test_cases': [
            {
                'test_name': 'test_method1',
                'status': 'failed',
                'error_message': 'TypeError: test error'
            }
        ],
        'best_attempt_so_far': {
            'success_rate': 0.0,
            'attempt_number': 1
        },
        'regression_analysis': {
            'new_failures': 0,
            'fixed_failures': 0,
            'remaining_failures': 1
        }
    }
    
    try:
        prompt = PromptBuilder.build_fix_prompt(
            content=content,
            file_path=file_path,
            learning_context=None,
            targeting_context=targeting_context,
            config=None,
            context_files=None
        )
        
        # Find the targeting context section
        if "TARGETING CONTEXT FOR FAILURE ANALYSIS:" in prompt:
            start_idx = prompt.find("TARGETING CONTEXT FOR FAILURE ANALYSIS:")
            end_idx = prompt.find("\n\n", start_idx)
            if end_idx == -1:
                end_idx = len(prompt)
            
            targeting_section = prompt[start_idx:end_idx]
            
            print("📋 TARGETING CONTEXT SECTION:")
            print("=" * 60)
            print(targeting_section)
            print("=" * 60)
            
            # Verify all expected content
            expected_content = [
                "🔴 CRITICAL: SURGICAL TARGETING REQUIREMENTS",
                "ONLY fix code in the following relevant sections:",
                "TestClass.method1 (lines 10-20)",
                "DO NOT modify any code outside these sections",
                "Failing functions to fix: method1",
                "Specific failing line numbers: 12, 15",
                "Failing test names: test_method1",
                "Specific error messages to address:",
                "Error types to fix: TypeError",
                "Failed test cases: 1 cases",
                "Best attempt so far:",
                "Success rate: 0.00%",
                "Regression analysis:"
            ]
            
            print("\n✅ VERIFICATION:")
            for check in expected_content:
                if check in targeting_section:
                    print(f"  ✅ Found: {check}")
                else:
                    print(f"  ❌ Missing: {check}")
            
            return True
        else:
            print("❌ Targeting context section not found")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    if test_targeting_context():
        print("\n🎉 Targeting context test passed!")
        sys.exit(0)
    else:
        print("\n❌ Targeting context test failed!")
        sys.exit(1) 