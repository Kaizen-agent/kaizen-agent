"""Test script for the memory system.

This script tests the basic functionality of the memory system to ensure
it works correctly and can be integrated with the existing test system.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import the memory system
sys.path.insert(0, str(Path(__file__).parent))

from memory import ExecutionMemory, LLMInteraction, TestCase, FixAttempt
from utils.code_extractor import extract_relevant_functions, create_surgical_context


def test_memory_basic_functionality():
    """Test basic memory system functionality."""
    print("🧪 Testing Memory System Basic Functionality")
    print("=" * 50)
    
    # Initialize memory
    memory = ExecutionMemory()
    execution_id = "test_execution_001"
    
    # Test 1: Start execution
    config = {'name': 'test_config', 'auto_fix': True}
    memory.start_execution(execution_id, config)
    print("✅ Execution started successfully")
    
    # Test 2: Save original code
    original_code = """
def validate_input(data):
    if not isinstance(data, str):
        return False
    return len(data) > 0

def process_data(data):
    result = data.upper()
    return result
"""
    
    relevant_sections = extract_relevant_functions(original_code)
    memory.save_original_relevant_code('test_file.py', relevant_sections)
    print(f"✅ Saved original code sections: {list(relevant_sections.keys())}")
    
    # Test 3: Log test run
    test_results = {
        'inputs': [{'data': 'hello'}, {'data': 123}],
        'outputs': [
            {'status': 'passed', 'test_name': 'test_valid_string'},
            {'status': 'failed', 'test_name': 'test_invalid_type', 'error_message': 'TypeError in validate_input'}
        ],
        'llm_logs': {},
        'attempt_outcome': {
            'success': False,
            'total_tests': 2,
            'passed_tests': 1,
            'failed_tests': 1
        }
    }
    memory.log_test_run('test_file.py', test_results)
    print("✅ Test run logged successfully")
    
    # Test 4: Log LLM interaction
    memory.log_llm_interaction(
        file_path='test_file.py',
        interaction_type='code_fixing',
        prompt='Fix the validate_input function',
        response='I will add type checking',
        reasoning='The function fails with non-string inputs',
        metadata={'attempt_number': 1, 'model': 'gpt-4'}
    )
    print("✅ LLM interaction logged successfully")
    
    # Test 5: Log fix attempt
    llm_interaction = LLMInteraction(
        interaction_type='code_fixing',
        prompt='Fix the validate_input function',
        response='I will add type checking',
        reasoning='The function fails with non-string inputs',
        metadata={'attempt_number': 1, 'model': 'gpt-4'}
    )
    
    memory.log_fix_attempt(
        file_path='test_file.py',
        attempt_number=1,
        original_code=original_code,
        fixed_code="""
def validate_input(data):
    if not isinstance(data, str):
        raise TypeError("Input must be a string")
    return len(data) > 0

def process_data(data):
    result = data.upper()
    return result
""",
        success=False,
        test_results_before={'passed': 1, 'failed': 1},
        test_results_after={'passed': 1, 'failed': 1},
        approach_description='Added type checking with exception',
        code_changes='Changed return False to raise TypeError',
        llm_interaction=llm_interaction,
        why_approach_failed='Exception breaks test expectations',
        lessons_learned='Should return False instead of raising exceptions'
    )
    print("✅ Fix attempt logged successfully")
    
    # Test 6: Get failed cases
    failed_cases = memory.get_failed_cases_latest_run('test_file.py')
    print(f"✅ Retrieved {len(failed_cases)} failed cases")
    
    # Test 7: Check if all tests passed
    all_passed = memory.all_tests_passed_latest_run('test_file.py')
    print(f"✅ All tests passed check: {all_passed}")
    
    # Test 8: Get learning context
    learning_context = memory.get_previous_attempts_insights('test_file.py')
    print(f"✅ Retrieved learning context with {len(learning_context['previous_attempts_history'])} previous attempts")
    
    # Test 9: Get targeting context
    targeting_context = memory.get_failure_analysis_data('test_file.py')
    print(f"✅ Retrieved targeting context with {len(targeting_context['failing_functions'])} failing functions")
    
    # Test 10: Get incremental learning data
    incremental_data = memory.get_incremental_learning_prompt_data('test_file.py')
    print(f"✅ Retrieved incremental learning data with {len(incremental_data['learning_from_history']['what_has_been_tried'])} tried approaches")
    
    # Test 11: Check if should continue fixing
    should_continue = memory.should_continue_fixing('test_file.py')
    print(f"✅ Should continue fixing: {should_continue['should_continue']} - {should_continue['reason']}")
    
    # Test 12: Find best attempt
    best_attempt = memory.find_best_attempt('test_file.py')
    print(f"✅ Best attempt: {best_attempt}")
    
    # Test 13: Detect regressions
    regressions = memory.detect_regressions_from_last_attempt('test_file.py')
    print(f"✅ Regression analysis: {regressions}")
    
    # Test 14: Compare attempts
    comparison = memory.compare_attempts('test_file.py')
    print(f"✅ Attempt comparison: {comparison}")
    
    print("\n✅ All basic functionality tests passed!")
    return memory


def test_code_extractor():
    """Test the code extractor utilities."""
    print("\n🧪 Testing Code Extractor")
    print("=" * 30)
    
    # Test code content
    code_content = """
def validate_input(data):
    if not isinstance(data, str):
        return False
    return len(data) > 0

def process_data(data):
    result = data.upper()
    return result

class DataProcessor:
    def __init__(self):
        self.data = []
    
    def add_data(self, item):
        self.data.append(item)
"""
    
    # Test 1: Extract relevant functions
    relevant_sections = extract_relevant_functions(code_content)
    print(f"✅ Extracted {len(relevant_sections)} relevant sections: {list(relevant_sections.keys())}")
    
    # Test 2: Create surgical context
    error_messages = [
        "TypeError in validate_input at line 3",
        "ValueError in process_data at line 8",
        "test_validation failed: expected True, got False"
    ]
    
    surgical_context = create_surgical_context(code_content, error_messages)
    print(f"✅ Created surgical context with {len(surgical_context['failing_functions'])} failing functions")
    print(f"   - Failing functions: {surgical_context['failing_functions']}")
    print(f"   - Error types: {surgical_context['error_types']}")
    print(f"   - Line numbers: {surgical_context['failing_lines']}")
    
    print("✅ Code extractor tests passed!")


def test_learning_prompt_generation(memory):
    """Test learning prompt generation."""
    print("\n🧪 Testing Learning Prompt Generation")
    print("=" * 40)
    
    # Get learning context
    learning_context = memory.get_previous_attempts_insights('test_file.py')
    incremental_data = memory.get_incremental_learning_prompt_data('test_file.py')
    
    # Build example prompt
    failed_cases_text = chr(10).join([f"- {case.get('test_name', 'Unknown')}: {case.get('error_message', 'No error')}" for case in learning_context.get('failed_cases_current', [])])
    failed_approaches_text = chr(10).join(learning_context.get('failed_approaches_to_avoid', []))
    what_not_to_try_text = chr(10).join([f"- {approach['failed_approach']}: {approach['why_failed']}" for approach in learning_context.get('what_not_to_try_again', [])])
    successful_patterns_text = chr(10).join(learning_context.get('successful_patterns_to_build_on', []))
    attempts_analysis_text = chr(10).join([f"Attempt {attempt['attempt_number']}: Tried '{attempt['approach_taken']}' → Failed because: {attempt['why_it_failed']}" for attempt in learning_context.get('previous_attempts_history', [])])
    reasoning_improvements_text = ''  # Removed insights_from_llm_reasoning - not currently used
    original_code_text = chr(10).join([f"Function: {name}\n{code}\n" for name, code in learning_context.get('original_code_sections', {}).items()])
    
    prompt = f"""🧠 LEARN FROM PREVIOUS ATTEMPTS - DO NOT REPEAT FAILURES:

CURRENT FAILURES TO FIX:
{failed_cases_text}

🚫 WHAT HAS ALREADY BEEN TRIED AND FAILED:
{failed_approaches_text}

❌ SPECIFIC APPROACHES TO NEVER TRY AGAIN:
{what_not_to_try_text}

✅ SUCCESSFUL PATTERNS TO BUILD ON:
{successful_patterns_text}

📊 PREVIOUS ATTEMPTS ANALYSIS:
{attempts_analysis_text}

🎯 STRATEGIC GUIDANCE BASED ON LEARNING:
- Recommended approach: {incremental_data.get('strategic_guidance', {}).get('recommended_next_approach', 'Use learning context')}
- Focus areas: {incremental_data.get('strategic_guidance', {}).get('areas_to_focus_on', ['Analyze root cause'])}
- Pitfalls to avoid: {incremental_data.get('strategic_guidance', {}).get('pitfalls_to_avoid', ['Repeating failed approaches'])}

💡 LLM REASONING IMPROVEMENTS NEEDED:
{reasoning_improvements_text}

🎯 SUCCESS TARGET:
Current best: {incremental_data.get('success_metrics', {}).get('best_attempt_so_far', 'No successful attempts yet')}
Target: {incremental_data.get('success_metrics', {}).get('improvement_target', 'Improve on previous attempts')}

ORIGINAL CODE TO PRESERVE:
{original_code_text}

LEARN AND EVOLVE: Use the above learning context to make a DIFFERENT and BETTER approach than previous attempts.

FULL FILE CONTENT:
[Current file content would go here]

FIX THE CODE BASED ON THE LEARNING CONTEXT ABOVE. DO NOT REPEAT FAILED APPROACHES.
"""
    
    print("✅ Learning prompt generated successfully")
    print(f"   - Prompt length: {len(prompt)} characters")
    print(f"   - Contains learning context: {'LEARN FROM PREVIOUS ATTEMPTS' in prompt}")
    print(f"   - Contains failed approaches: {'WHAT HAS ALREADY BEEN TRIED' in prompt}")
    print(f"   - Contains strategic guidance: {'STRATEGIC GUIDANCE' in prompt}")
    
    print("✅ Learning prompt generation tests passed!")


def main():
    """Run all memory system tests."""
    print("🧠 Kaizen Memory System Test Suite")
    print("=" * 50)
    
    try:
        # Test basic functionality
        memory = test_memory_basic_functionality()
        
        # Test code extractor
        test_code_extractor()
        
        # Test learning prompt generation
        test_learning_prompt_generation(memory)
        
        print("\n🎉 All memory system tests passed!")
        print("The memory system is ready for integration with the test system.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 