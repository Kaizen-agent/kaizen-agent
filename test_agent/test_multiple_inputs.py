"""Test script for multiple input functionality.

This script tests the new multiple input parsing and execution functionality
to ensure it works correctly with different input types and maintains
backward compatibility.
"""

import sys
import os
import logging
from pathlib import Path
import pickle

# Add the parent directory to the path so we can import the input parser
sys.path.insert(0, str(Path(__file__).parent.parent))

from kaizen.autofix.test.input_parser import InputParser, InputParsingError, build_inputs_from_yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_string_input():
    """Test string input parsing."""
    print("\n=== Testing String Input ===")
    
    input_config = {
        'type': 'string',
        'value': 'Hello, world!'
    }
    
    parser = InputParser()
    result = parser.parse_inputs(input_config)
    
    print(f"Input config: {input_config}")
    print(f"Parsed result: {result}")
    print(f"Type: {type(result[0])}")
    print(f"Value: {result[0]}")
    
    assert len(result) == 1
    assert isinstance(result[0], str)
    assert result[0] == 'Hello, world!'
    print("✅ String input test passed")

def test_dict_input():
    """Test dictionary input parsing."""
    print("\n=== Testing Dict Input ===")
    
    input_config = {
        'type': 'dict',
        'value': {
            'temperature': 25,
            'solvent': 'ethanol',
            'pressure': 1.0
        }
    }
    
    parser = InputParser()
    result = parser.parse_inputs(input_config)
    
    print(f"Input config: {input_config}")
    print(f"Parsed result: {result}")
    print(f"Type: {type(result[0])}")
    print(f"Value: {result[0]}")
    
    assert len(result) == 1
    assert isinstance(result[0], dict)
    assert result[0]['temperature'] == 25
    assert result[0]['solvent'] == 'ethanol'
    print("✅ Dict input test passed")

def test_object_input():
    """Test object input parsing with dynamic import."""
    print("\n=== Testing Object Input ===")
    
    input_config = {
        'type': 'object',
        'class_path': 'input_types.ChemistFeedback',
        'args': {
            'text': 'Too reactive',
            'tags': ['solubility', 'stability']
        }
    }
    
    parser = InputParser()
    result = parser.parse_inputs(input_config)
    
    print(f"Input config: {input_config}")
    print(f"Parsed result type: {type(result[0])}")
    print(f"Object attributes: text='{result[0].text}', tags={result[0].tags}")
    
    assert len(result) == 1
    assert hasattr(result[0], 'text')
    assert hasattr(result[0], 'tags')
    assert result[0].text == 'Too reactive'
    assert result[0].tags == ['solubility', 'stability']
    print("✅ Object input test passed")

def test_multiple_inputs():
    """Test multiple input parsing."""
    print("\n=== Testing Multiple Inputs ===")
    
    input_config = [
        {
            'name': 'feedback',
            'type': 'object',
            'class_path': 'input_types.ChemistFeedback',
            'args': {
                'text': 'Too reactive',
                'tags': ['solubility', 'stability']
            }
        },
        {
            'name': 'context',
            'type': 'dict',
            'value': {
                'temperature': 25,
                'solvent': 'ethanol'
            }
        },
        {
            'name': 'query',
            'type': 'string',
            'value': 'How stable is this compound?'
        }
    ]
    
    parser = InputParser()
    result = parser.parse_inputs(input_config)
    
    print(f"Input config: {len(input_config)} items")
    print(f"Parsed result: {len(result)} items")
    
    for i, item in enumerate(result):
        print(f"  Item {i+1}: {type(item).__name__} = {item}")
    
    assert len(result) == 3
    assert hasattr(result[0], 'text')  # ChemistFeedback object
    assert isinstance(result[1], dict)  # Context dict
    assert isinstance(result[2], str)   # Query string
    print("✅ Multiple inputs test passed")

def test_backward_compatibility():
    """Test backward compatibility with single values."""
    print("\n=== Testing Backward Compatibility ===")
    
    # Test single string
    parser = InputParser()
    result1 = parser.parse_inputs("Simple string")
    print(f"Single string: {result1}")
    assert len(result1) == 1
    assert result1[0] == "Simple string"
    
    # Test single dict
    result2 = parser.parse_inputs({'key': 'value'})
    print(f"Single dict: {result2}")
    assert len(result2) == 1
    assert result2[0] == {'key': 'value'}
    
    # Test None
    result3 = parser.parse_inputs(None)
    print(f"None input: {result3}")
    assert len(result3) == 1
    assert result3[0] is None
    
    print("✅ Backward compatibility test passed")

def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\n=== Testing Error Handling ===")
    
    parser = InputParser()
    
    # Test invalid type in input definition
    print("Testing invalid type...")
    try:
        result = parser.parse_inputs({'type': 'invalid_type', 'value': 'test'})
        print(f"Unexpected result: {result}")
        assert False, "Should have raised InputParsingError"
    except InputParsingError as e:
        print(f"✅ Caught expected error for invalid type: {e}")
    
    # Test missing value for string
    print("Testing missing value...")
    try:
        result = parser.parse_inputs({'type': 'string'})
        print(f"Unexpected result: {result}")
        assert False, "Should have raised InputParsingError"
    except InputParsingError as e:
        print(f"✅ Caught expected error for missing value: {e}")
    
    # Test missing class_path for object
    print("Testing missing class_path...")
    try:
        result = parser.parse_inputs({'type': 'object', 'args': {}})
        print(f"Unexpected result: {result}")
        assert False, "Should have raised InputParsingError"
    except InputParsingError as e:
        print(f"✅ Caught expected error for missing class_path: {e}")
    
    # Test invalid class path
    print("Testing invalid class path...")
    try:
        result = parser.parse_inputs({
            'type': 'object',
            'class_path': 'nonexistent.module.Class',
            'args': {}
        })
        print(f"Unexpected result: {result}")
        assert False, "Should have raised InputParsingError"
    except InputParsingError as e:
        print(f"✅ Caught expected error for invalid class path: {e}")
    
    # Test invalid args type for object
    print("Testing invalid args type...")
    try:
        result = parser.parse_inputs({
            'type': 'object',
            'class_path': 'input_types.ChemistFeedback',
            'args': 'invalid_args'
        })
        print(f"Unexpected result: {result}")
        assert False, "Should have raised InputParsingError"
    except InputParsingError as e:
        print(f"✅ Caught expected error for invalid args type: {e}")
    
    # Test invalid value type for string
    print("Testing invalid string value type...")
    try:
        result = parser.parse_inputs({'type': 'string', 'value': 123})
        print(f"Unexpected result: {result}")
        assert False, "Should have raised InputParsingError"
    except InputParsingError as e:
        print(f"✅ Caught expected error for invalid string value type: {e}")
    
    # Test invalid value type for dict
    print("Testing invalid dict value type...")
    try:
        result = parser.parse_inputs({'type': 'dict', 'value': 'not_a_dict'})
        print(f"Unexpected result: {result}")
        assert False, "Should have raised InputParsingError"
    except InputParsingError as e:
        print(f"✅ Caught expected error for invalid dict value type: {e}")

def test_helper_function():
    """Test the helper function build_inputs_from_yaml."""
    print("\n=== Testing Helper Function ===")
    
    yaml_input_list = [
        {
            'name': 'test_string',
            'type': 'string',
            'value': 'Test value'
        },
        {
            'name': 'test_dict',
            'type': 'dict',
            'value': {'key': 'value'}
        }
    ]
    
    result = build_inputs_from_yaml(yaml_input_list)
    
    print(f"YAML input list: {yaml_input_list}")
    print(f"Helper function result: {result}")
    
    assert len(result) == 2
    assert isinstance(result[0], str)
    assert isinstance(result[1], dict)
    print("✅ Helper function test passed")

def test_agent_integration():
    """Test integration with the test agent."""
    print("\n=== Testing Agent Integration ===")
    
    # Import the test agent
    from test_agent.test_agent import TestAgent
    
    agent = TestAgent()
    
    # Test with multiple inputs
    feedback = {
        'type': 'object',
        'class_path': 'input_types.ChemistFeedback',
        'args': {
            'text': 'Too reactive',
            'tags': ['solubility', 'stability']
        }
    }
    
    context = {
        'type': 'dict',
        'value': {
            'temperature': 25,
            'solvent': 'ethanol'
        }
    }
    
    query = {
        'type': 'string',
        'value': 'How stable is this compound?'
    }
    
    # Parse inputs
    parser = InputParser()
    parsed_inputs = parser.parse_inputs([feedback, context, query])
    
    print(f"Parsed inputs: {len(parsed_inputs)} items")
    for i, item in enumerate(parsed_inputs):
        print(f"  Input {i+1}: {type(item).__name__}")
    
    # Run agent
    response = agent.run(*parsed_inputs)
    
    print(f"Agent response: {response.message}")
    print(f"Confidence: {response.confidence}")
    print(f"Metadata: {response.metadata}")
    
    assert response.message is not None
    assert response.confidence > 0
    assert 'input_count' in response.metadata
    assert response.metadata['input_count'] == 3
    
    print("✅ Agent integration test passed")

def test_class_object_input():
    """Test class_object input parsing with import_path and pickle_path."""
    print("\n=== Testing Class Object Input ===")
    
    # 1. Test import_path
    input_config_import = {
        'type': 'class_object',
        'import_path': 'input_types.ChemistFeedback',
    }
    parser = InputParser()
    obj = parser.parse_inputs(input_config_import)[0]
    print(f"Imported class object: {obj}")
    assert isinstance(obj, type)
    assert obj.__name__ == 'ChemistFeedback'
    print("✅ class_object import_path test passed")
    
    # 2. Test pickle_path
    # Create a ChemistFeedback instance and pickle it
    from input_types import ChemistFeedback
    feedback_instance = ChemistFeedback(text='Pickled feedback', tags=['test'])
    pickle_file = 'test_pickled_feedback.pkl'
    with open(pickle_file, 'wb') as f:
        pickle.dump(feedback_instance, f)
    input_config_pickle = {
        'type': 'class_object',
        'pickle_path': pickle_file,
    }
    obj2 = parser.parse_inputs(input_config_pickle)[0]
    print(f"Loaded class object from pickle: {obj2}")
    assert isinstance(obj2, ChemistFeedback)
    assert obj2.text == 'Pickled feedback'
    print("✅ class_object pickle_path test passed")
    
    # Clean up
    os.remove(pickle_file)

def test_inline_object_input():
    """Test inline_object input parsing with direct attribute specification."""
    print("\n=== Testing Inline Object Input ===")
    
    input_config = {
        'type': 'inline_object',
        'class_path': 'input_types.ChemistFeedback',
        'attributes': {
            'text': 'Inline feedback test',
            'tags': ['inline', 'test'],
            'confidence': 0.85,
            'source': 'yaml_config'
        }
    }
    
    parser = InputParser()
    result = parser.parse_inputs(input_config)
    
    print(f"Input config: {input_config}")
    print(f"Parsed result type: {type(result[0])}")
    print(f"Object attributes: text='{result[0].text}', tags={result[0].tags}, confidence={result[0].confidence}")
    
    assert len(result) == 1
    assert hasattr(result[0], 'text')
    assert hasattr(result[0], 'tags')
    assert hasattr(result[0], 'confidence')
    assert result[0].text == 'Inline feedback test'
    assert result[0].tags == ['inline', 'test']
    assert result[0].confidence == 0.85
    assert result[0].source == 'yaml_config'
    print("✅ Inline object input test passed")

def test_inline_object_with_experiment_context():
    """Test inline_object with a different class type."""
    print("\n=== Testing Inline Object with Experiment Context ===")
    
    input_config = {
        'type': 'inline_object',
        'class_path': 'input_types.ExperimentContext',
        'attributes': {
            'temperature': 298.15,
            'pressure': 101325,
            'solvent': 'water',
            'catalyst': 'none',
            'duration': 24.0
        }
    }
    
    parser = InputParser()
    result = parser.parse_inputs(input_config)
    
    print(f"Input config: {input_config}")
    print(f"Parsed result type: {type(result[0])}")
    print(f"Object attributes: temp={result[0].temperature}, solvent='{result[0].solvent}'")
    
    assert len(result) == 1
    assert hasattr(result[0], 'temperature')
    assert hasattr(result[0], 'solvent')
    assert result[0].temperature == 298.15
    assert result[0].solvent == 'water'
    assert result[0].catalyst == 'none'
    print("✅ Inline object with experiment context test passed")

def main():
    """Run all tests."""
    print("🧪 Testing Multiple Input Functionality")
    print("=" * 50)
    
    try:
        test_string_input()
        test_dict_input()
        test_object_input()
        test_multiple_inputs()
        test_backward_compatibility()
        test_error_handling()
        test_helper_function()
        test_agent_integration()
        test_class_object_input()
        test_inline_object_input()
        test_inline_object_with_experiment_context()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! Multiple input functionality is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 