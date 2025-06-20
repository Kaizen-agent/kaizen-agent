#!/usr/bin/env python3
"""
Demonstration of the new inline_object input type functionality.

This script shows how the inline_object input type makes it much easier
to specify class objects directly in YAML without needing external files.
"""

import yaml
from kaizen.autofix.test.input_parser import InputParser

def demo_inline_object():
    """Demonstrate the inline_object input type."""
    print("🚀 Inline Object Input Type Demonstration")
    print("=" * 50)
    
    # Example YAML configuration with inline_object
    yaml_config = """
input:
  # Inline object - everything defined in YAML!
  - name: chemist_feedback
    type: inline_object
    class_path: "input_types.ChemistFeedback"
    attributes:
      text: "Compound shows excellent stability under test conditions"
      tags: ["stability", "testing", "inline"]
      confidence: 0.95
      source: "yaml_config"
  
  # Another inline object with different class
  - name: experiment_context
    type: inline_object
    class_path: "input_types.ExperimentContext"
    attributes:
      temperature: 298.15
      pressure: 101325
      solvent: "water"
      catalyst: "none"
      duration: 24.0
  
  # Regular dict for comparison
  - name: additional_params
    type: dict
    value:
      concentration: 0.1
      stirring_speed: 500
      pH: 7.0
"""
    
    print("📋 YAML Configuration:")
    print(yaml_config)
    
    # Parse the configuration
    config = yaml.safe_load(yaml_config)
    parser = InputParser()
    
    try:
        inputs = parser.parse_inputs(config['input'])
        
        print("\n✅ Parsed Inputs:")
        print(f"Total inputs: {len(inputs)}")
        
        for i, item in enumerate(inputs, 1):
            print(f"\n  Input {i}:")
            print(f"    Type: {type(item).__name__}")
            print(f"    Value: {item}")
            
            # Show specific attributes for our custom classes
            if hasattr(item, 'text'):
                print(f"    Text: {item.text}")
                print(f"    Tags: {item.tags}")
                print(f"    Confidence: {item.confidence}")
            elif hasattr(item, 'temperature'):
                print(f"    Temperature: {item.temperature} K")
                print(f"    Solvent: {item.solvent}")
                print(f"    Duration: {item.duration} hours")
        
        print("\n🎉 Success! Inline object inputs work perfectly!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

def compare_input_types():
    """Compare different input types for the same data."""
    print("\n\n📊 Input Type Comparison")
    print("=" * 50)
    
    # Same data, different input types
    chemist_data = {
        'text': 'Compound shows excellent stability',
        'tags': ['stability', 'testing'],
        'confidence': 0.95,
        'source': 'yaml_config'
    }
    
    print("Same ChemistFeedback data, different input types:")
    
    # 1. Inline object (new, recommended)
    inline_config = {
        'type': 'inline_object',
        'class_path': 'input_types.ChemistFeedback',
        'attributes': chemist_data
    }
    
    # 2. Object (requires separate class file)
    object_config = {
        'type': 'object',
        'class_path': 'input_types.ChemistFeedback',
        'args': chemist_data
    }
    
    # 3. Dict (no validation, no type safety)
    dict_config = {
        'type': 'dict',
        'value': chemist_data
    }
    
    parser = InputParser()
    
    print("\n1. Inline Object (NEW):")
    print("   ✅ Type safety, validation, self-contained")
    print("   ✅ Everything in YAML, no external files")
    print("   ✅ Easy to modify and version control")
    
    print("\n2. Object:")
    print("   ✅ Type safety and validation")
    print("   ❌ Requires separate class file")
    print("   ❌ External dependency")
    
    print("\n3. Dict:")
    print("   ✅ Simple, no setup required")
    print("   ❌ No validation or type safety")
    print("   ❌ No method access")
    
    # Test all three
    try:
        inline_result = parser.parse_inputs(inline_config)[0]
        object_result = parser.parse_inputs(object_config)[0]
        dict_result = parser.parse_inputs(dict_config)[0]
        
        print(f"\n✅ All input types work:")
        print(f"   Inline object: {type(inline_result).__name__}")
        print(f"   Object: {type(object_result).__name__}")
        print(f"   Dict: {type(dict_result).__name__}")
        
        # Show that inline_object and object produce the same result
        assert inline_result.text == object_result.text
        assert inline_result.tags == object_result.tags
        print(f"   ✅ Inline object and object produce identical results")
        
    except Exception as e:
        print(f"❌ Error in comparison: {e}")

def main():
    """Run the demonstration."""
    demo_inline_object()
    compare_input_types()
    
    print("\n" + "=" * 50)
    print("🎯 Key Benefits of Inline Object Input:")
    print("   • No external files needed")
    print("   • Version control friendly")
    print("   • Easy to modify in YAML")
    print("   • Self-contained configurations")
    print("   • Maintains type safety and validation")
    print("   • Perfect for test configurations")

if __name__ == "__main__":
    main() 