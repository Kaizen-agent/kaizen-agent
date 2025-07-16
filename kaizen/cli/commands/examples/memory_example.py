"""Example demonstrating the memory system with learning capabilities.

This example shows how the ExecutionMemory class tracks test execution,
LLM interactions, and provides learning context for intelligent code fixing.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Import the memory system
from ..memory import ExecutionMemory, LLMInteraction, TestCase, FixAttempt


def demonstrate_memory_system():
    """Demonstrate the comprehensive memory system functionality."""
    
    # Initialize memory
    memory = ExecutionMemory()
    execution_id = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Start execution tracking
    config = {
        'name': 'demo_test',
        'file_path': 'example.py',
        'auto_fix': True,
        'max_retries': 3
    }
    memory.start_execution(execution_id, config)
    
    print("🧠 Memory System Demo")
    print("=" * 50)
    
    # 1. Save original code
    original_code = """
def validate_input(data):
    if not isinstance(data, str):
        return False
    return len(data) > 0

def process_data(data):
    result = data.upper()
    return result
"""
    
    relevant_sections = {
        'validate_input': 'def validate_input(data):\n    if not isinstance(data, str):\n        return False\n    return len(data) > 0',
        'process_data': 'def process_data(data):\n    result = data.upper()\n    return result'
    }
    memory.save_original_relevant_code('example.py', relevant_sections)
    print("✅ Saved original code sections")
    
    # 2. Log test run
    test_results = {
        'inputs': [{'data': 'hello'}, {'data': 123}, {'data': ''}],
        'outputs': [
            {'status': 'passed', 'test_name': 'test_valid_string'},
            {'status': 'failed', 'test_name': 'test_invalid_type', 'error_message': 'TypeError in validate_input'},
            {'status': 'failed', 'test_name': 'test_empty_string', 'error_message': 'ValueError in validate_input'}
        ],
        'llm_logs': {},
        'attempt_outcome': {
            'success': False,
            'total_tests': 3,
            'passed_tests': 1,
            'failed_tests': 2
        }
    }
    memory.log_test_run('example.py', test_results)
    print("✅ Logged test run with 2 failures")
    
    # 3. Simulate first fix attempt
    llm_interaction_1 = LLMInteraction(
        interaction_type='code_fixing',
        prompt='Fix the validate_input function to handle type errors',
        response='I will add type checking to handle non-string inputs',
        reasoning='The function fails when given non-string inputs, so I need to add proper type validation',
        metadata={'attempt_number': 1, 'model': 'gpt-4'}
    )
    
    memory.log_llm_interaction('example.py', 'code_fixing', 
                              'Fix the validate_input function', 
                              'I will add type checking', 
                              'The function fails with non-string inputs',
                              {'attempt_number': 1})
    
    # Log the fix attempt
    memory.log_fix_attempt(
        file_path='example.py',
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
        test_results_before={'passed': 1, 'failed': 2},
        test_results_after={'passed': 1, 'failed': 2},
        approach_description='Added type checking with exception',
        code_changes='Changed return False to raise TypeError',
        llm_interaction=llm_interaction_1,
        why_approach_failed='Exception breaks test expectations',
        lessons_learned='Should return False instead of raising exceptions'
    )
    print("✅ Logged first fix attempt (failed)")
    
    # 4. Simulate second fix attempt
    llm_interaction_2 = LLMInteraction(
        interaction_type='code_fixing',
        prompt='Fix the validate_input function - previous attempt failed because it raised exceptions',
        response='I will return False for invalid inputs instead of raising exceptions',
        reasoning='Previous attempt failed because it raised exceptions, but tests expect False for invalid inputs',
        metadata={'attempt_number': 2, 'model': 'gpt-4'}
    )
    
    memory.log_llm_interaction('example.py', 'code_fixing',
                              'Fix validate_input - previous attempt failed',
                              'I will return False for invalid inputs',
                              'Previous attempt raised exceptions but tests expect False',
                              {'attempt_number': 2})
    
    memory.log_fix_attempt(
        file_path='example.py',
        attempt_number=2,
        original_code=original_code,
        fixed_code="""
def validate_input(data):
    if not isinstance(data, str):
        return False
    if len(data) == 0:
        return False
    return True

def process_data(data):
    result = data.upper()
    return result
""",
        success=True,
        test_results_before={'passed': 1, 'failed': 2},
        test_results_after={'passed': 3, 'failed': 0},
        approach_description='Return False for invalid inputs',
        code_changes='Added empty string check and return False for invalid inputs',
        llm_interaction=llm_interaction_2,
        what_worked_partially='Returning False instead of exceptions worked',
        lessons_learned='Match test expectations by returning False for invalid inputs'
    )
    print("✅ Logged second fix attempt (successful)")
    
    # 5. Demonstrate learning context extraction
    print("\n📊 Learning Context Analysis")
    print("-" * 30)
    
    learning_context = memory.get_previous_attempts_insights('example.py')
    print(f"Failed cases: {len(learning_context['failed_cases_current'])}")
    print(f"Previous attempts: {len(learning_context['previous_attempts_history'])}")
    print(f"Failed approaches to avoid: {len(learning_context['failed_approaches_to_avoid'])}")
    print(f"Successful patterns: {len(learning_context['successful_patterns_to_build_on'])}")
    
    # 6. Show incremental learning data
    incremental_data = memory.get_incremental_learning_prompt_data('example.py')
    print(f"\n🎯 Strategic Guidance:")
    print(f"  - What has been tried: {len(incremental_data['learning_from_history']['what_has_been_tried'])} approaches")
    print(f"  - What definitely doesn't work: {len(incremental_data['learning_from_history']['what_definitely_doesnt_work'])} patterns")
    print(f"  - What shows promise: {len(incremental_data['learning_from_history']['what_shows_promise'])} patterns")
    
    # 7. Show targeting context
    targeting_context = memory.get_failure_analysis_data('example.py')
    print(f"\n🎯 Surgical Fixing Context:")
    print(f"  - Failing functions: {targeting_context['failing_functions']}")
    print(f"  - Error types: {targeting_context['error_types']}")
    print(f"  - Original code sections: {list(targeting_context['original_relevant_sections'].keys())}")
    
    # 8. Show analysis functions
    print(f"\n📈 Analysis Results:")
    print(f"  - All tests passed: {memory.all_tests_passed_latest_run('example.py')}")
    print(f"  - Best attempt: {memory.find_best_attempt('example.py')}")
    print(f"  - Regressions: {memory.detect_regressions_from_last_attempt('example.py')}")
    
    # 9. Show comparison
    comparison = memory.compare_attempts('example.py')
    print(f"  - Improvement trend: {comparison['improvement_trend']}")
    print(f"  - Successful patterns: {comparison['successful_patterns']}")
    print(f"  - Failed patterns: {comparison['failed_patterns']}")
    
    print("\n✅ Memory system demonstration completed!")
    return memory


def show_learning_prompt_example(memory: ExecutionMemory):
    """Show an example of the learning-enhanced prompt."""
    
    print("\n🧠 Learning-Enhanced Prompt Example")
    print("=" * 50)
    
    # Get learning context
    learning_context = memory.get_previous_attempts_insights('example.py')
    incremental_data = memory.get_incremental_learning_prompt_data('example.py')
    
    # Build example prompt
    failed_cases_text = '\n'.join([f"- {case.get('test_name', 'Unknown')}: {case.get('error_message', 'No error')}" for case in learning_context.get('failed_cases_current', [])])
    failed_approaches_text = '\n'.join(learning_context.get('failed_approaches_to_avoid', []))
    what_not_to_try_text = '\n'.join([f"- {approach['failed_approach']}: {approach['why_failed']}" for approach in learning_context.get('what_not_to_try_again', [])])
    successful_patterns_text = '\n'.join(learning_context.get('successful_patterns_to_build_on', []))
    attempts_analysis_text = '\n'.join([f"Attempt {attempt['attempt_number']}: Tried '{attempt['approach_taken']}' → Failed because: {attempt['why_it_failed']}" for attempt in learning_context.get('previous_attempts_history', [])])
    reasoning_improvements_text = ''  # Removed insights_from_llm_reasoning - not currently used
    original_code_text = '\n'.join([f"Function: {name}\n{code}\n" for name, code in learning_context.get('original_code_sections', {}).items()])
    
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
    
    print(prompt)
    print("\n✅ This prompt provides comprehensive learning context to the LLM!")


if __name__ == "__main__":
    # Run the demonstration
    memory = demonstrate_memory_system()
    
    # Show learning prompt example
    show_learning_prompt_example(memory) 