"""Example script demonstrating how to use the memory inspection tools.

This script shows various ways to inspect and understand the ExecutionMemory
data structure. Run this to see how the memory system works.

Usage:
    python -m kaizen.cli.commands.memory_example
"""

from memory import ExecutionMemory
from memory_inspector import MemoryInspector, quick_inspect, detailed_inspect


def create_sample_memory():
    """Create a sample memory with mock data for demonstration."""
    memory = ExecutionMemory()
    
    # Start an execution
    memory.start_execution("example_test_123", config=None)
    
    # Add some mock test runs
    mock_test_results = {
        'test_cases': [
            {
                'name': 'test_addition',
                'status': 'passed',
                'input': {'a': 2, 'b': 3},
                'expected_output': 5,
                'actual_output': 5
            },
            {
                'name': 'test_subtraction',
                'status': 'failed',
                'input': {'a': 5, 'b': 3},
                'expected_output': 2,
                'actual_output': 8,
                'error_message': 'AssertionError: Expected 2, got 8'
            }
        ],
        'summary': {
            'total_tests': 2,
            'passed_tests': 1,
            'failed_tests': 1,
            'error_tests': 0,
            'success_rate': 0.5
        },
        'result': {'overall_status': 'failed'},
        'failed_test_cases': [
            {
                'name': 'test_subtraction',
                'status': 'failed',
                'input': {'a': 5, 'b': 3},
                'expected_output': 2,
                'actual_output': 8,
                'error_message': 'AssertionError: Expected 2, got 8'
            }
        ],
        'passed_test_cases': [
            {
                'name': 'test_addition',
                'status': 'passed',
                'input': {'a': 2, 'b': 3},
                'expected_output': 5,
                'actual_output': 5
            }
        ],
        'error_test_cases': [],
        'timing_analysis': {'total_execution_time': 0.5},
        'error_analysis': {'most_common_error': 'AssertionError'}
    }
    
    memory.log_test_run("calculator.py", mock_test_results)
    
    # Add some LLM interactions
    memory.log_llm_interaction(
        "calculator.py",
        "code_fixing",
        "Fix the subtraction function that's returning wrong results",
        "I'll analyze the code and fix the subtraction logic",
        reasoning="The issue is in the subtraction function where it's adding instead of subtracting",
        metadata={'model': 'gpt-4', 'temperature': 0.1}
    )
    
    # Add a fix attempt
    from memory import LLMInteraction
    
    llm_interaction = LLMInteraction(
        interaction_type="code_fixing",
        prompt="Fix the subtraction function",
        response="I'll change the + operator to - operator",
        reasoning="The function is using addition instead of subtraction"
    )
    
    memory.log_fix_attempt(
        "calculator.py",
        1,
        "def subtract(a, b): return a + b",  # Original code
        "def subtract(a, b): return a - b",  # Fixed code
        True,  # Success
        {'passed': 1, 'failed': 1},  # Before
        {'passed': 2, 'failed': 0},  # After
        "Fixed the subtraction operator",
        "Changed + to - in the return statement",
        "The function was using addition instead of subtraction",
        llm_interaction,
        "Always check the operator in mathematical functions",
        None,  # why_approach_failed
        None   # what_worked_partially
    )
    
    return memory


def demonstrate_inspection():
    """Demonstrate various inspection methods."""
    print("Creating sample memory data...")
    memory = create_sample_memory()
    
    print("\n" + "="*60)
    print("DEMONSTRATING MEMORY INSPECTION TOOLS")
    print("="*60)
    
    # 1. Quick overview
    print("\n1. QUICK OVERVIEW:")
    quick_inspect(memory)
    
    # 2. Detailed inspection
    print("\n2. DETAILED INSPECTION:")
    inspector = MemoryInspector(memory)
    inspector.show_detailed_structure(max_items=3)
    
    # 3. Summary statistics
    print("\n3. SUMMARY STATISTICS:")
    inspector.show_summary()
    
    # 4. Schema information
    print("\n4. MEMORY SCHEMA:")
    inspector.show_schema()
    
    # 5. Get specific data
    print("\n5. SPECIFIC DATA ACCESS:")
    test_runs = inspector.get_test_runs()
    print(f"   - Test runs: {len(test_runs)}")
    
    fix_attempts = inspector.get_fix_attempts()
    print(f"   - Fix attempts: {len(fix_attempts)}")
    
    llm_interactions = inspector.get_llm_interactions()
    print(f"   - LLM interactions: {len(llm_interactions)}")
    
    failed_cases = inspector.get_failed_test_cases()
    print(f"   - Failed test cases: {len(failed_cases)}")
    
    learning_context = inspector.get_learning_context("calculator.py")
    print(f"   - Learning context keys: {list(learning_context.keys())}")
    
    # 6. Export to file
    print("\n6. EXPORTING TO FILE:")
    inspector.export_to_file("sample_memory_dump.json", "json")
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE!")
    print("="*60)


def show_memory_methods():
    """Show all available memory methods."""
    print("\n" + "="*60)
    print("AVAILABLE MEMORY METHODS")
    print("="*60)
    
    methods = [
        # Core methods
        ("start_execution()", "Initialize new execution tracking"),
        ("log_test_run()", "Store complete test execution data"),
        ("log_llm_interaction()", "Store LLM conversation data"),
        ("log_fix_attempt()", "Store code fix attempt with learning"),
        
        # Inspection methods
        ("inspect_structure()", "Debug method to see complete structure"),
        ("get_memory_summary()", "Get summary statistics"),
        ("get_memory_schema()", "Get complete schema description"),
        ("export_memory_to_json()", "Export to JSON format"),
        
        # Context methods
        ("get_previous_attempts_insights()", "Extract learning for next attempt"),
        ("get_failure_analysis_data()", "Get surgical fix targeting data"),
        ("get_failed_cases_latest_run()", "Get failed test cases from latest run"),
        ("all_tests_passed_latest_run()", "Check if all tests passed"),
        
        # Analysis methods
        ("find_best_attempt()", "Find attempt with highest success rate"),
        ("detect_regressions_from_last_attempt()", "Compare runs for regressions"),
        ("get_comprehensive_test_analysis()", "Get detailed test analysis"),
        ("should_continue_fixing()", "Determine if should continue auto-fix"),
        
        # Configuration methods
        ("get_complete_configuration()", "Get complete config object"),
        ("get_configuration_summary()", "Get config summary"),
        ("get_config_value()", "Get specific config value"),
        ("get_config_property()", "Get config property using dot notation"),
        ("has_config_value()", "Check if config value exists"),
        ("create_mock_config()", "Create mock config from memory data")
    ]
    
    for method_name, description in methods:
        print(f"📋 {method_name}")
        print(f"   {description}")
        print()


def show_inspector_methods():
    """Show all available inspector methods."""
    print("\n" + "="*60)
    print("AVAILABLE INSPECTOR METHODS")
    print("="*60)
    
    methods = [
        ("show_overview()", "Show quick overview of memory structure"),
        ("show_detailed_structure()", "Show detailed structure with examples"),
        ("show_schema()", "Show complete memory schema"),
        ("show_summary()", "Show comprehensive summary statistics"),
        ("export_to_file()", "Export memory data to file (JSON/TXT)"),
        
        # Data access methods
        ("get_test_runs()", "Get all test runs as dictionaries"),
        ("get_fix_attempts()", "Get all fix attempts as dictionaries"),
        ("get_llm_interactions()", "Get all LLM interactions as dictionaries"),
        ("get_failed_test_cases()", "Get failed test cases from latest run"),
        ("get_learning_context()", "Get learning context for specific file")
    ]
    
    for method_name, description in methods:
        print(f"🔍 {method_name}")
        print(f"   {description}")
        print()


if __name__ == "__main__":
    print("Kaizen Memory System - Inspection Demo")
    print("="*50)
    
    # Show available methods
    show_memory_methods()
    show_inspector_methods()
    
    # Demonstrate inspection
    demonstrate_inspection()
    
    print("\nTo use in your code:")
    print("from kaizen.cli.commands.memory import ExecutionMemory")
    print("from kaizen.cli.commands.memory_inspector import MemoryInspector")
    print()
    print("# Create memory instance")
    print("memory = ExecutionMemory()")
    print()
    print("# Inspect memory")
    print("inspector = MemoryInspector(memory)")
    print("inspector.show_overview()") 