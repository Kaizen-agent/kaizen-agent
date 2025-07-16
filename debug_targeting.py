#!/usr/bin/env python3
"""
Debug script to check targeting context processing.
"""

import sys
import os

# Add the kaizen package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'kaizen'))

from kaizen.autofix.code.llm_fixer import PromptBuilder

def debug_targeting_context():
    """Debug targeting context processing."""
    print("🔍 Debugging targeting context processing...\n")
    
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
    
    print("📋 Input targeting_context:")
    print(targeting_context)
    print("\n" + "="*60 + "\n")
    
    try:
        prompt = PromptBuilder.build_fix_prompt(
            content=content,
            file_path=file_path,
            learning_context=None,
            targeting_context=targeting_context,
            config=None,
            context_files=None
        )
        
        # Check if targeting context section exists
        if "TARGETING CONTEXT FOR FAILURE ANALYSIS:" in prompt:
            start_idx = prompt.find("TARGETING CONTEXT FOR FAILURE ANALYSIS:")
            
            # Find the end of the targeting section by looking for the next major section
            end_markers = [
                "\n\nConfiguration Context:",
                "\n\nRelated Files (for context and dependencies):",
                "\n\nFile:",
                "\n\nContent:"
            ]
            
            end_idx = len(prompt)
            for marker in end_markers:
                marker_idx = prompt.find(marker, start_idx)
                if marker_idx != -1 and marker_idx < end_idx:
                    end_idx = marker_idx
            
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
            
            print(f"\n📋 Targeting section length: {len(targeting_section)}")
            print(f"📋 Targeting section starts with: '{targeting_section[:50]}...'")
            print(f"📋 Targeting section ends with: '...{targeting_section[-50:]}'")
            
            print("\n✅ VERIFICATION:")
            all_found = True
            for check in expected_content:
                if check in targeting_section:
                    print(f"  ✅ Found: {check}")
                else:
                    print(f"  ❌ Missing: {check}")
                    all_found = False
            
            if all_found:
                print("\n🎉 All targeting context content found!")
                return True
            else:
                print("\n❌ Some targeting context content missing!")
                return False
        else:
            print("❌ Targeting context section not found at all!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if debug_targeting_context():
        print("\n🎉 Debug completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Debug found issues!")
        sys.exit(1) 