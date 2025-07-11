"""Augment CLI command for adding test cases to existing YAML files.

This module provides a CLI command for augmenting test YAML files by generating
additional test cases using Gemini AI. The command parses existing test cases
and generates new ones to reach a target total count.

Example:
    >>> from kaizen.cli.commands.augment import augment
    >>> augment(
    ...     config_path="test.yaml",
    ...     total=10,
    ...     better_ai=True
    ... )
"""

# Standard library imports
import logging
import os
from io import StringIO
from pathlib import Path
from typing import List, Dict, Any, Optional

# Third-party imports
import click
import google.generativeai as genai
from rich.console import Console
from rich.logging import RichHandler
from ruamel.yaml import YAML

# Local application imports
from .config import ConfigurationManager
from .errors import ConfigurationError

def analyze_test_structure(tests: List[Dict]) -> Dict[str, Any]:
    """Analyze the structure of existing test cases to understand the pattern.
    
    Args:
        tests: List of test cases
        
    Returns:
        Dictionary containing structure analysis
    """
    if not tests:
        return {}
    
    # Analyze the first test to understand structure
    first_test = tests[0]
    
    # Dynamically discover all fields in the test
    structure = {
        'test_fields': list(first_test.keys()),
        'input_fields': {},
        'input_structure': {}
    }
    
    # Analyze input structure if present
    if 'input' in first_test:
        input_data = first_test['input']
        if isinstance(input_data, dict):
            structure['input_fields'] = list(input_data.keys())
            
            # Analyze input parameters if present
            if 'input' in input_data:
                input_params = input_data['input']
                if isinstance(input_params, list):
                    param_analysis = []
                    for param in input_params:
                        if isinstance(param, dict):
                            param_analysis.append({
                                'fields': list(param.keys()),
                                'has_name': 'name' in param,
                                'has_type': 'type' in param,
                                'has_value': 'value' in param
                            })
                    structure['input_structure'] = {
                        'is_list': True,
                        'param_count': len(input_params),
                        'param_analysis': param_analysis
                    }
    
    return structure

def extract_agent_context(tests: List[Dict]) -> Dict[str, Any]:
    """Extract context about the agent's purpose and functionality from test cases.
    
    Args:
        tests: List of test cases
        
    Returns:
        Dictionary containing agent context information
    """
    if not tests:
        return {}
    
    context = {
        'input_types': set(),
        'input_names': set(),
        'output_patterns': set(),
        'test_scenarios': [],
        'agent_purpose': 'unknown'
    }
    
    for test in tests:
        # Extract test scenario from name and description
        test_name = test.get('name', '').lower()
        test_desc = test.get('description', '').lower()
        context['test_scenarios'].append({
            'name': test.get('name', ''),
            'description': test.get('description', ''),
            'scenario_type': 'unknown'
        })
        
        # Analyze input structure
        if 'input' in test:
            input_data = test['input']
            if isinstance(input_data, dict) and 'input' in input_data:
                input_params = input_data['input']
                if isinstance(input_params, list):
                    for param in input_params:
                        if isinstance(param, dict):
                            param_name = param.get('name', '').lower()
                            param_value = param.get('value')
                            param_type = param.get('type', 'unknown')
                            
                            context['input_names'].add(param_name)
                            context['input_types'].add(param_type)
                            
                            # Infer agent purpose from input names and values
                            if 'feedback' in param_name or 'evaluation' in param_name:
                                context['agent_purpose'] = 'evaluation'
                            elif 'summarize' in param_name or 'summary' in param_name:
                                context['agent_purpose'] = 'summarization'
                            elif 'question' in param_name or 'query' in param_name:
                                context['agent_purpose'] = 'question_answering'
                            elif 'transform' in param_name or 'convert' in param_name:
                                context['agent_purpose'] = 'transformation'
                            elif 'analyze' in param_name or 'analysis' in param_name:
                                context['agent_purpose'] = 'analysis'
            
            # Analyze expected output patterns
            if 'expected_output' in input_data:
                expected_output = input_data['expected_output']
                if isinstance(expected_output, dict):
                    for key, value in expected_output.items():
                        context['output_patterns'].add(f"{key}: {type(value).__name__}")
    
    # Convert sets to lists for JSON serialization
    context['input_types'] = list(context['input_types'])
    context['input_names'] = list(context['input_names'])
    context['output_patterns'] = list(context['output_patterns'])
    
    return context

def validate_test_structure(tests: List[Dict]) -> None:
    """Validate that all test cases follow a consistent structure.
    
    Args:
        tests: List of test cases to validate
        
    Raises:
        ValueError: If any test case doesn't follow the expected structure
    """
    if not tests:
        return
    
    # Get the structure of the first test as the reference
    reference_test = tests[0]
    reference_fields = set(reference_test.keys())
    reference_input_fields = set(reference_test.get('input', {}).keys()) if 'input' in reference_test else set()
    
    for i, test in enumerate(tests):
        if not isinstance(test, dict):
            raise ValueError(f"Test case {i} is not a dictionary")
        
        # Check if test has the same top-level fields as reference
        test_fields = set(test.keys())
        if test_fields != reference_fields:
            missing_fields = reference_fields - test_fields
            extra_fields = test_fields - reference_fields
            if missing_fields:
                raise ValueError(f"Test case {i} missing fields: {missing_fields}")
            if extra_fields:
                raise ValueError(f"Test case {i} has extra fields: {extra_fields}")
        
        # Validate input structure if present
        if 'input' in test:
            input_data = test['input']
            if not isinstance(input_data, dict):
                raise ValueError(f"Test case {i} 'input' field is not a dictionary")
            
            # Check if input has the same fields as reference
            test_input_fields = set(input_data.keys())
            if test_input_fields != reference_input_fields:
                missing_input_fields = reference_input_fields - test_input_fields
                extra_input_fields = test_input_fields - reference_input_fields
                if missing_input_fields:
                    raise ValueError(f"Test case {i} input missing fields: {missing_input_fields}")
                if extra_input_fields:
                    raise ValueError(f"Test case {i} input has extra fields: {extra_input_fields}")
            
            # Validate input parameters if present
            if 'input' in input_data:
                input_params = input_data['input']
                if not isinstance(input_params, list):
                    raise ValueError(f"Test case {i} 'input.input' field is not a list")
                
                # Validate each input parameter has required fields
                for j, param in enumerate(input_params):
                    if not isinstance(param, dict):
                        raise ValueError(f"Test case {i} input parameter {j} is not a dictionary")
                    
                    # Check for required fields in parameters
                    if 'name' not in param:
                        raise ValueError(f"Test case {i} input parameter {j} missing 'name' field")
                    if 'value' not in param:
                        raise ValueError(f"Test case {i} input parameter {j} missing 'value' field")

# Configure rich logging
console = Console()

def generate_additional_tests(existing_tests: List[Dict], target_total: int, use_better_ai: bool, full_config: Dict = None) -> List[Dict]:
    """Generate additional test cases using Gemini AI.
    
    Args:
        existing_tests: List of existing test cases from YAML
        target_total: Total number of test cases desired
        use_better_ai: Whether to use Gemini 2.5 Pro (better AI model)
        full_config: Complete YAML configuration for context
        
    Returns:
        List of new test cases in the same YAML format
    """
    # Calculate how many new tests we need
    existing_count = len(existing_tests)
    needed_count = target_total - existing_count
    
    if needed_count <= 0:
        return []
    
    # Initialize Gemini
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    genai.configure(api_key=api_key)
    
    # Select model based on better_ai flag
    if use_better_ai:
        model = genai.GenerativeModel('gemini-2.5-pro')
    else:
        model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
    
    # Analyze the structure of existing tests to understand the pattern
    test_structure = analyze_test_structure(existing_tests)
    
    # Extract agent context from the first test to help guide generation
    agent_context = extract_agent_context(existing_tests)
    
    # Initialize YAML for formatting
    yaml_formatter = YAML()
    yaml_formatter.indent(mapping=2, sequence=4, offset=2)
    yaml_formatter.preserve_quotes = True
    
    # Create prompt for generating additional test cases
    # Build the full context prompt
    full_context = ""
    if full_config:
        # Use StringIO to capture the YAML output
        yaml_output = StringIO()
        yaml_formatter.dump(full_config, yaml_output)
        full_context = f"""
Complete Agent Configuration:
{yaml_output.getvalue()}

This configuration shows:
- Agent name: {full_config.get('name', 'Unknown')}
- Agent type: {full_config.get('agent_type', 'Unknown')}
- File path: {full_config.get('file_path', 'Unknown')}
- Description: {full_config.get('description', 'No description')}
- Agent module: {full_config.get('agent', {}).get('module', 'Unknown')}
- Agent class: {full_config.get('agent', {}).get('class', 'Unknown')}
- Agent method: {full_config.get('agent', {}).get('method', 'Unknown')}
- Evaluation targets: {len(full_config.get('evaluation', {}).get('evaluation_targets', []))} targets
- Max retries: {full_config.get('max_retries', 'Unknown')}
- Files to fix: {full_config.get('files_to_fix', [])}
"""

    # Capture existing tests YAML output
    existing_tests_output = StringIO()
    yaml_formatter.dump(existing_tests, existing_tests_output)
    
    prompt = f"""You're helping improve test coverage for an LLM-powered agent. Based on the existing test cases and the agent's functionality, generate more cases to ensure reliability in diverse real-world scenarios.

Generate {needed_count} additional test cases in YAML format.{full_context}

Existing test cases:
{existing_tests_output.getvalue()}

Test structure analysis:
{test_structure}

Agent Context Analysis:
{agent_context}

CRITICAL REQUIREMENTS:
- Return ONLY a valid YAML array of test cases
- Follow the EXACT same YAML format as existing tests
- Maintain same structure and field names
- NO explanations, comments, or markdown formatting
- NO code blocks or ```yaml tags
- Ensure all YAML syntax is correct (proper indentation, quotes, etc.)

Test Coverage Strategy:
1. **Edge Cases**: Test boundary conditions, empty inputs, maximum values, minimum values
2. **Input Variations**: Slight modifications to existing inputs to test robustness
3. **Negative/Invalid Inputs**: Test how the agent handles malformed, unexpected, or invalid data
4. **Corner Cases**: Scenarios the original tests might miss (e.g., very long inputs, special characters, mixed data types)
5. **Real-world Scenarios**: Test cases that reflect actual usage patterns and potential failure points
6. **Context Understanding**: Generate tests that align with the agent's purpose (e.g., summarization, evaluation, transformation)

Guidelines for Test Generation:
- Use descriptive test names that clearly indicate the scenario being tested
- Vary input values significantly to test different aspects of the agent's functionality
- Consider the agent's domain and purpose when generating test cases
- Include both positive and negative test scenarios
- Test edge cases that could cause failures in production
- Generate realistic inputs that users might actually provide
- Consider error conditions and how the agent should handle them

Based on the agent's purpose ({agent_context.get('agent_purpose', 'unknown')}), focus on generating test cases that:
- Test the agent's core functionality thoroughly
- Cover edge cases specific to this type of agent
- Include realistic failure scenarios
- Validate the agent's ability to handle diverse inputs
- Ensure robust performance in real-world conditions

Generate {needed_count} diverse and comprehensive test cases in valid YAML format:"""
    
    try:
        # Generate response from Gemini
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,  # Moderate creativity
                max_output_tokens=4000,
                top_p=0.8,
                top_k=40,
            )
        )
        
        if not response.text:
            raise ValueError("Empty response from Gemini")
        
        # Parse the response as YAML
        try:
            # Try to extract YAML from the response (in case it's wrapped in markdown)
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```yaml'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # Parse as YAML using ruamel.yaml
            yaml_parser = YAML(typ='safe')
            new_tests = yaml_parser.load(response_text)
            
            # Ensure it's a list
            if not isinstance(new_tests, list):
                raise ValueError("Generated response is not a list")
            
            # Validate each test case has required fields
            for test in new_tests:
                if not isinstance(test, dict):
                    raise ValueError("Test case is not a dictionary")
                
                # Check that test has the same structure as existing tests
                if existing_tests:
                    reference_test = existing_tests[0]
                    reference_fields = set(reference_test.keys())
                    test_fields = set(test.keys())
                    
                    if test_fields != reference_fields:
                        missing_fields = reference_fields - test_fields
                        extra_fields = test_fields - reference_fields
                        if missing_fields:
                            raise ValueError(f"Generated test missing fields: {missing_fields}")
                        if extra_fields:
                            raise ValueError(f"Generated test has extra fields: {extra_fields}")
                
                # Validate input structure if present
                if 'input' in test:
                    input_data = test['input']
                    if not isinstance(input_data, dict):
                        raise ValueError("Test case 'input' field is not a dictionary")
                    
                    # Check input fields match reference
                    if existing_tests and 'input' in existing_tests[0]:
                        reference_input = existing_tests[0]['input']
                        reference_input_fields = set(reference_input.keys())
                        test_input_fields = set(input_data.keys())
                        
                        if test_input_fields != reference_input_fields:
                            missing_input_fields = reference_input_fields - test_input_fields
                            extra_input_fields = test_input_fields - reference_input_fields
                            if missing_input_fields:
                                raise ValueError(f"Generated test input missing fields: {missing_input_fields}")
                            if extra_input_fields:
                                raise ValueError(f"Generated test input has extra fields: {extra_input_fields}")
                    
                    # Validate input parameters if present
                    if 'input' in input_data:
                        input_params = input_data['input']
                        if not isinstance(input_params, list):
                            raise ValueError("Test case 'input.input' field is not a list")
                        
                        # Validate each input parameter
                        for param in input_params:
                            if not isinstance(param, dict):
                                raise ValueError("Input parameter is not a dictionary")
                            if 'name' not in param:
                                raise ValueError("Input parameter missing 'name' field")
                            if 'value' not in param:
                                raise ValueError("Input parameter missing 'value' field")
            
            return new_tests
            
        except Exception as e:
            logger.error(f"Generated YAML parsing error: {str(e)}")
            logger.error(f"Generated response: {response_text}")
            raise ValueError(f"Failed to parse generated YAML: {str(e)}")
            
    except Exception as e:
        raise RuntimeError(f"Failed to generate test cases: {str(e)}")

@click.command()
@click.argument('config_path', type=click.Path(exists=True))
@click.option('--total', type=int, required=True, help='Total number of test cases desired (original + new)')
@click.option('--better-ai', is_flag=True, help='Use Gemini 2.5 Pro for improved test generation')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed debug information')
def augment(config_path: str, total: int, better_ai: bool, verbose: bool) -> None:
    """Add additional test cases to an existing test YAML file.
    
    This command parses existing test cases from a YAML file and generates
    additional test cases using Gemini AI to reach the specified total count.
    
    Args:
        config_path: Path to the existing test YAML file
        total: Total number of test cases desired (original + new)
        better_ai: Whether to use Gemini 2.5 Pro for improved generation
        verbose: Whether to show detailed debug information
        
    Example:
        >>> augment(
        ...     config_path="test.yaml",
        ...     total=10,
        ...     better_ai=True
        ... )
    """
    # Set up logging
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(message)s",
            handlers=[RichHandler(rich_tracebacks=True)]
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[RichHandler(rich_tracebacks=True)]
        )
    
    logger = logging.getLogger("kaizen.augment")
    
    try:
        # Load the existing YAML file
        config_file = Path(config_path)
        logger.info(f"Loading existing test configuration from: {config_file}")
        
        # Initialize YAML parser with ruamel.yaml
        yaml_parser = YAML(typ='safe')
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml_parser.load(f)
        
        if not config_data:
            raise ValueError("Empty or invalid YAML file")
        
        # Extract existing test cases
        existing_tests = config_data.get('steps', [])
        if not existing_tests:
            raise ValueError("No 'steps' section found in YAML file")
        
        existing_count = len(existing_tests)
        logger.info(f"Found {existing_count} existing test cases")
        
        # Validate existing test structure
        try:
            validate_test_structure(existing_tests)
            logger.info("✅ Existing test structure is valid")
        except ValueError as e:
            raise ValueError(f"Invalid test structure: {str(e)}")
        
        # Analyze test structure
        structure = analyze_test_structure(existing_tests)
        logger.info(f"Test structure: {structure}")
        
        # Check if we need to generate more tests
        if existing_count >= total:
            logger.info(f"Already have {existing_count} test cases, which meets or exceeds the target of {total}")
            console.print(f"✅ No additional test cases needed. File already has {existing_count} test cases.")
            return
        
        needed_count = total - existing_count
        logger.info(f"Need to generate {needed_count} additional test cases")
        
        # Generate additional test cases
        console.print(f"🔄 Generating {needed_count} additional test cases using {'Gemini 2.5 Pro' if better_ai else 'Gemini 2.5 Flash'}...")
        
        new_tests = generate_additional_tests(existing_tests, total, better_ai, config_data)
        
        if not new_tests:
            raise ValueError("No new test cases were generated")
        
        logger.info(f"Generated {len(new_tests)} new test cases")
        
        # Combine existing and new test cases
        all_tests = existing_tests + new_tests
        
        # Create augmented configuration
        augmented_config = config_data.copy()
        augmented_config['steps'] = all_tests
        
        # Save to new file with proper formatting
        output_path = config_file.with_suffix('.augmented.yaml')
        
        # Initialize YAML formatter with proper indentation settings
        yaml_formatter = YAML()
        yaml_formatter.indent(mapping=2, sequence=4, offset=2)
        yaml_formatter.preserve_quotes = True
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml_formatter.dump(augmented_config, f)
        
        # Print success message
        console.print(f"✅ Added {len(new_tests)} test cases. Saved to {output_path}")
        console.print(f"📊 Total test cases: {len(all_tests)} (original: {existing_count}, new: {len(new_tests)})")
        
        # Show summary of new test cases
        if verbose:
            console.print("\n📋 New test cases generated:")
            for i, test in enumerate(new_tests, 1):
                name = test.get('name', f'Generated Test {i}')
                input_params = test.get('input', {}).get('input', [])
                param_summary = ", ".join([f"{param.get('name', 'unknown')}={param.get('value', 'unknown')}" 
                                        for param in input_params])
                console.print(f"  {i}. {name} - Inputs: {param_summary}")
        
    except Exception as e:
        logger.error(f"Error during augmentation: {str(e)}")
        console.print(f"❌ Error: {str(e)}")
        raise click.Abort() 