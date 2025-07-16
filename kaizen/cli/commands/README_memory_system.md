# Kaizen Memory System

The Kaizen Memory System provides comprehensive tracking and learning capabilities for test execution, LLM interactions, and code fixing attempts. It's designed to enable surgical code fixing with learning from previous attempts.

## Quick Start

```python
from kaizen.cli.commands.memory import ExecutionMemory
from kaizen.cli.commands.memory_inspector import MemoryInspector

# Create memory instance
memory = ExecutionMemory()

# Start tracking an execution
memory.start_execution("my_test_123", config=my_config)

# Log test results
memory.log_test_run("file.py", test_results)

# Log LLM interactions
memory.log_llm_interaction("file.py", "code_fixing", prompt, response)

# Log fix attempts
memory.log_fix_attempt("file.py", 1, original, fixed, success, ...)

# Inspect memory
inspector = MemoryInspector(memory)
inspector.show_overview()
```

## Data Structure Overview

The memory system stores data in a hierarchical structure:

### 1. Execution Level (Top Level)
- `execution_id`: Unique identifier for each test execution
- `start_time`: When execution started
- `config`: Complete configuration object
- `configuration_context`: Serialized config with metadata
- `test_runs`: All test execution attempts
- `llm_interactions`: All LLM conversations
- `fix_attempts`: All code fix attempts
- `original_code_sections`: Original code before fixes
- `learning_history`: Cumulative learning data

### 2. Test Run Level (TestRun dataclass)
- `test_run_id`: Unique run identifier
- `attempt_number`: Which attempt this is
- `timestamp`: When run occurred
- `test_cases`: Individual test case details
- `summary`: Test summary statistics
- `result`: Overall result info
- `failed_test_cases`: Failed tests only
- `passed_test_cases`: Passed tests only
- `error_test_cases`: Error tests only
- `timing_analysis`: Execution timing data
- `error_analysis`: Error pattern analysis

### 3. Fix Attempt Level (FixAttempt dataclass)
- `attempt_number`: Which fix attempt
- `approach_description`: What was tried
- `code_changes_made`: Specific changes
- `original_code`: Code before fix
- `modified_code`: Code after fix
- `test_results_before`: Test results before fix
- `test_results_after`: Test results after fix
- `success`: Whether fix worked
- `llm_interaction`: Complete LLM data
- `lessons_learned`: Key insights
- `why_approach_failed`: Failure analysis
- `what_worked_partially`: Partial successes

### 4. LLM Interaction Level (LLMInteraction dataclass)
- `interaction_type`: Type of interaction
- `prompt`: Complete prompt sent
- `response`: Complete LLM response
- `reasoning`: Step-by-step reasoning
- `metadata`: Model details, tokens, etc.
- `timestamp`: When interaction occurred

### 5. Test Case Level (TestCase dataclass)
- `test_name`: Name of the test
- `status`: 'passed', 'failed', 'error'
- `input`: Test input data
- `expected_output`: Expected result
- `actual_output`: Actual result
- `error_message`: Error details if failed
- `failing_function`: Function that failed
- `failing_line`: Line number of failure

## Key Methods

### Core Methods
- `start_execution()`: Initialize new execution tracking
- `log_test_run()`: Store complete test execution data
- `log_llm_interaction()`: Store LLM conversation data
- `log_fix_attempt()`: Store code fix attempt with learning

### Inspection Methods
- `inspect_structure()`: Debug method to see complete structure
- `get_memory_summary()`: Get summary statistics
- `get_memory_schema()`: Get complete schema description
- `export_memory_to_json()`: Export to JSON format

### Context Methods
- `get_previous_attempts_insights()`: Extract learning for next attempt
- `get_failure_analysis_data()`: Get surgical fix targeting data
- `get_failed_cases_latest_run()`: Get failed test cases from latest run
- `all_tests_passed_latest_run()`: Check if all tests passed

### Analysis Methods
- `find_best_attempt()`: Find attempt with highest success rate
- `detect_regressions_from_last_attempt()`: Compare runs for regressions
- `get_comprehensive_test_analysis()`: Get detailed test analysis
- `should_continue_fixing()`: Determine if should continue auto-fix

### Configuration Methods
- `get_complete_configuration()`: Get complete config object
- `get_configuration_summary()`: Get config summary
- `get_config_value()`: Get specific config value
- `get_config_property()`: Get config property using dot notation
- `has_config_value()`: Check if config value exists
- `create_mock_config()`: Create mock config from memory data

## Memory Inspector

The `MemoryInspector` class provides easy ways to inspect and understand the memory data:

```python
from kaizen.cli.commands.memory_inspector import MemoryInspector

# Create inspector
inspector = MemoryInspector(memory)

# Quick overview
inspector.show_overview()

# Detailed inspection
inspector.show_detailed_structure()

# Show schema
inspector.show_schema()

# Show summary statistics
inspector.show_summary()

# Export to file
inspector.export_to_file("memory_dump.json")

# Get specific data
test_runs = inspector.get_test_runs()
fix_attempts = inspector.get_fix_attempts()
llm_interactions = inspector.get_llm_interactions()
failed_cases = inspector.get_failed_test_cases()
learning_context = inspector.get_learning_context("file.py")
```

## Quick Inspection Functions

For immediate use, you can use these quick functions:

```python
from kaizen.cli.commands.memory_inspector import quick_inspect, detailed_inspect

# Quick overview
quick_inspect(memory)

# Detailed inspection
detailed_inspect(memory)
```

## Example Usage

See `memory_example.py` for a complete demonstration of how to use the memory system.

## Learning Context for LLM

The memory system provides comprehensive learning context for LLMs:

```python
# Get learning context for surgical fixing
learning_context = memory.get_previous_attempts_insights("file.py")

# This includes:
# - Failed test cases from latest run
# - Previous attempts history
# - Failed approaches to avoid
# - Successful patterns to build on
# - LLM reasoning insights
# - Original code sections
# - Configuration context
```

## Export and Analysis

You can export memory data for external analysis:

```python
# Export to JSON
json_data = memory.export_memory_to_json(file_path="memory_dump.json")

# Get summary statistics
summary = memory.get_memory_summary()

# Get comprehensive analysis
analysis = memory.get_comprehensive_test_analysis()
```

## Schema Information

To understand the complete data structure:

```python
# Get complete schema
schema = memory.get_memory_schema()

# Show schema using inspector
inspector = MemoryInspector(memory)
inspector.show_schema()
```

## Best Practices

1. **Always start execution**: Call `start_execution()` before logging any data
2. **Log comprehensive data**: Use the detailed logging methods to capture all context
3. **Use learning context**: Extract learning context before making LLM calls
4. **Inspect regularly**: Use the inspector tools to understand what data is available
5. **Export for analysis**: Export memory data for external analysis and debugging

## Troubleshooting

If you're having trouble understanding the memory structure:

1. Use `memory.inspect_structure()` to see the complete structure
2. Use `MemoryInspector(memory).show_overview()` for a quick overview
3. Use `memory.get_memory_schema()` to understand the data types
4. Export to JSON and examine the file structure
5. Check the example script for usage patterns

## Integration

The memory system integrates with the rest of the Kaizen framework:

- **Test Execution**: Automatically logs test results
- **LLM Interactions**: Captures all LLM conversations
- **Code Fixing**: Tracks all fix attempts and learning
- **Configuration**: Stores complete configuration context
- **Learning**: Provides learning context for improved fixing

This comprehensive memory system enables the Kaizen agent to learn from previous attempts and perform surgical code fixing with full context awareness. 