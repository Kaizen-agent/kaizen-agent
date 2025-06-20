# Multiple Input Support for Test Runner

This document describes the enhanced test runner functionality that supports multiple inputs with flexible types and formats.

## Overview

The test runner has been upgraded to support multiple input objects, each with flexible types and formats, as defined in the YAML test file. This enables more advanced use cases like multi-agent workflows, contextual reasoning, and complex data processing.

## Features

- **Multiple Input Support**: Pass any number of inputs to agent methods
- **Flexible Input Types**: Support for string, dict, object, and class_object types
- **Dynamic Object Import**: Automatically import and instantiate Python classes
- **Class Object Support**: Import class objects or load from pickle files
- **Backward Compatibility**: Existing single-input configurations continue to work
- **Type Safety**: Comprehensive validation and error handling
- **Extensible**: Easy to add new input types in the future

## Input Types Setup Guide

### 1. String Input

**Purpose**: Simple text input for queries, messages, or raw data.

**Dictionary Structure**:
```yaml
input:
  - name: user_message
    type: string
    value: "How stable is this compound in ethanol?"
```

**Required Fields**:
- `type`: Must be `"string"`
- `value`: The string content (required)

**Optional Fields**:
- `name`: Descriptive name for the input (for internal use)

**Example Use Cases**:
```yaml
# Simple query
input:
  - name: query
    type: string
    value: "What is the boiling point of ethanol?"

# User message
input:
  - name: user_input
    type: string
    value: "Please analyze this compound for stability"

# File path
input:
  - name: file_path
    type: string
    value: "/path/to/data.csv"
```

### 2. Dictionary Input

**Purpose**: Structured data input for context, parameters, or configuration.

**Dictionary Structure**:
```yaml
input:
  - name: context
    type: dict
    value:
      temperature: 25
      solvent: "ethanol"
      pressure: 1.0
      concentration: 0.1
```

**Required Fields**:
- `type`: Must be `"dict"`
- `value`: The dictionary content (required)

**Optional Fields**:
- `name`: Descriptive name for the input

**Example Use Cases**:
```yaml
# Experimental parameters
input:
  - name: experiment_config
    type: dict
    value:
      temperature: 298.15
      pressure: 101325
      solvent: "water"
      pH: 7.0
      stirring_speed: 500

# User preferences
input:
  - name: user_preferences
    type: dict
    value:
      language: "en"
      units: "metric"
      precision: 3
      output_format: "json"

# API configuration
input:
  - name: api_config
    type: dict
    value:
      base_url: "https://api.example.com"
      timeout: 30
      retries: 3
      headers:
        Authorization: "Bearer token123"
```

### 3. Object Input

**Purpose**: Complex object input with dynamic class instantiation.

**Dictionary Structure**:
```yaml
input:
  - name: chemist_feedback
    type: object
    class_path: "input_types.ChemistFeedback"
    args:
      text: "Too reactive"
      tags: ["solubility", "stability"]
      confidence: 0.9
      source: "lab_analysis"
```

**Required Fields**:
- `type`: Must be `"object"`
- `class_path`: Python import path to the class (e.g., "module.submodule.ClassName")
- `args`: Dictionary of arguments to pass to the class constructor

**Optional Fields**:
- `name`: Descriptive name for the input

**Creating Custom Classes for Object Inputs**:

1. **Define your class** (e.g., in `input_types.py`):
```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ChemistFeedback:
    text: str
    tags: List[str]
    confidence: Optional[float] = None
    source: Optional[str] = None
    
    def __post_init__(self):
        """Validate the feedback data."""
        if not self.text.strip():
            raise ValueError("Feedback text cannot be empty")
        if not self.tags:
            raise ValueError("At least one tag must be provided")
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'text': self.text,
            'tags': self.tags,
            'confidence': self.confidence,
            'source': self.source
        }
```

2. **Use in YAML**:
```yaml
input:
  - name: feedback
    type: object
    class_path: "input_types.ChemistFeedback"
    args:
      text: "Compound shows excellent stability"
      tags: ["stability", "synthesis"]
      confidence: 0.95
      source: "experimental_data"
```

**Example Use Cases**:
```yaml
# Experimental context
input:
  - name: experiment_context
    type: object
    class_path: "input_types.ExperimentContext"
    args:
      temperature: 25.0
      pressure: 1.0
      solvent: "ethanol"
      catalyst: "Pd/C"
      duration: 24.0

# Compound data
input:
  - name: compound_info
    type: object
    class_path: "input_types.CompoundData"
    args:
      name: "Ethanol"
      molecular_weight: 46.07
      molecular_formula: "C2H5OH"
      cas_number: "64-17-5"
      properties:
        boiling_point: 78.37
        density: 0.789

# User query with metadata
input:
  - name: user_query
    type: object
    class_path: "input_types.UserQuery"
    args:
      text: "How stable is this compound?"
      intent: "stability_analysis"
      priority: "high"
      context:
        user_id: "chemist_001"
        project: "drug_discovery"
```

### 4. Class Object Input

**Purpose**: Directly use a Python class object as input, either by importing from a module or loading from a pickle file.

**Dictionary Structure**:

#### a. Importing a class object from a module
```yaml
input:
  - name: chemist_feedback_class
    type: class_object
    import_path: "input_types.ChemistFeedback"
```

#### b. Loading a class object from a pickle file
```yaml
input:
  - name: pickled_feedback
    type: class_object
    pickle_path: "test_pickled_feedback.pkl"
```

**Required Fields**:
- `type`: Must be `"class_object"`
- Either `import_path` OR `pickle_path` (but not both)

**Optional Fields**:
- `name`: Descriptive name for the input

**Creating Pickled Objects**:

1. **Create and pickle an object**:
```python
from input_types import ChemistFeedback
import pickle

# Create an instance
feedback = ChemistFeedback(
    text="Excellent stability under test conditions",
    tags=["stability", "testing"],
    confidence=0.95,
    source="lab_results"
)

# Pickle the object
with open('my_feedback.pkl', 'wb') as f:
    pickle.dump(feedback, f)
```

2. **Use in YAML**:
```yaml
input:
  - name: saved_feedback
    type: class_object
    pickle_path: "my_feedback.pkl"
```

**Example Use Cases**:
```yaml
# Import a class for dynamic instantiation
input:
  - name: feedback_class
    type: class_object
    import_path: "input_types.ChemistFeedback"

# Load a pre-configured object
input:
  - name: standard_context
    type: class_object
    pickle_path: "standard_experiment_context.pkl"

# Load a trained model
input:
  - name: ml_model
    type: class_object
    pickle_path: "trained_model.pkl"
```

### 5. Inline Object Input

**Purpose**: Specify class objects directly in YAML with their attributes, making it much easier than loading from files.

**Dictionary Structure**:
```yaml
input:
  - name: chemist_feedback
    type: inline_object
    class_path: "test_agent.input_types.ChemistFeedback"
    attributes:
      text: "Compound shows excellent stability under test conditions"
      tags: ["stability", "testing", "inline"]
      confidence: 0.95
      source: "yaml_config"
```

**Required Fields**:
- `type`: Must be `"inline_object"`
- `class_path`: Python import path to the class (e.g., "module.submodule.ClassName")
- `attributes`: Dictionary of attributes to pass to the class constructor

**Optional Fields**:
- `name`: Descriptive name for the input

**Creating Custom Classes for Inline Object Inputs**:

1. **Define your class** (e.g., in `input_types.py`):
```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ChemistFeedback:
    text: str
    tags: List[str]
    confidence: Optional[float] = None
    source: Optional[str] = None
    
    def __post_init__(self):
        """Validate the feedback data."""
        if not self.text.strip():
            raise ValueError("Feedback text cannot be empty")
        if not self.tags:
            raise ValueError("At least one tag must be provided")
```

2. **Use in YAML**:
```yaml
input:
  - name: feedback
    type: inline_object
    class_path: "test_agent.input_types.ChemistFeedback"
    attributes:
      text: "Compound shows excellent stability"
      tags: ["stability", "synthesis"]
      confidence: 0.95
      source: "experimental_data"
```

**Example Use Cases**:
```yaml
# Experimental context with inline object
input:
  - name: experiment_context
    type: inline_object
    class_path: "test_agent.input_types.ExperimentContext"
    attributes:
      temperature: 25.0
      pressure: 1.0
      solvent: "ethanol"
      catalyst: "Pd/C"
      duration: 24.0

# Compound data with inline object
input:
  - name: compound_info
    type: inline_object
    class_path: "test_agent.input_types.CompoundData"
    attributes:
      name: "Ethanol"
      molecular_weight: 46.07
      molecular_formula: "C2H5OH"
      cas_number: "64-17-5"
      properties:
        boiling_point: 78.37
        density: 0.789

# User query with metadata using inline object
input:
  - name: user_query
    type: inline_object
    class_path: "test_agent.input_types.UserQuery"
    attributes:
      text: "How stable is this compound?"
      intent: "stability_analysis"
      priority: "high"
      context:
        user_id: "chemist_001"
        project: "drug_discovery"

# Complex nested object
input:
  - name: analysis_request
    type: inline_object
    class_path: "test_agent.input_types.AnalysisRequest"
    attributes:
      compound_name: "Aspirin"
      analysis_type: "stability"
      parameters:
        temperature_range: [20, 40]
        humidity_range: [30, 70]
        duration_days: 30
      priority: "urgent"
      requester: "lab_manager"
```

**Advantages of Inline Object Input**:
- **No external files needed**: Everything is defined in the YAML configuration
- **Version control friendly**: All object definitions are tracked in your test files
- **Easy to modify**: Change attributes directly in the YAML without touching Python files
- **Self-contained**: Test configurations are complete and portable
- **Type safety**: Still maintains the benefits of using proper Python classes

**Comparison with Other Input Types**:

| Input Type | Use Case | Pros | Cons |
|------------|----------|------|------|
| `inline_object` | Complex objects with validation | Type safety, validation, self-contained | Requires class definition |
| `object` | Dynamic instantiation | Flexible, reusable classes | Requires separate class files |
| `class_object` | Pre-existing objects | Load from files/modules | External dependencies |
| `dict` | Simple data structures | Simple, no setup required | No validation, no type safety |

## Complete YAML Configuration Examples

### Basic Multiple Inputs
```yaml
name: Chemistry Analysis Test
agent_type: dynamic_region
file_path: chemistry_agent.py
description: Test chemistry analysis with multiple input types

input:
  # Inline object input - the new convenient way!
  - name: chemist_feedback
    type: inline_object
    class_path: "test_agent.input_types.ChemistFeedback"
    attributes:
      text: "Compound shows excellent stability under test conditions"
      tags: ["stability", "testing", "inline"]
      confidence: 0.95
      source: "yaml_config"
  
  # Experimental context as inline object
  - name: experiment_context
    type: inline_object
    class_path: "test_agent.input_types.ExperimentContext"
    attributes:
      temperature: 298.15
      pressure: 101325
      solvent: "water"
      catalyst: "none"
      duration: 24.0
  
  # Regular dict input for additional parameters
  - name: additional_params
    type: dict
    value:
      concentration: 0.1
      stirring_speed: 500
      pH: 7.0
  
  # String input for user query
  - name: user_query
    type: string
    value: "How stable is this compound under these conditions?"

evaluation:
  - variable: stability_analysis
    expected: "The compound shows moderate instability in ethanol due to its polar nature."
    tolerance: "exact"
  
  - variable: safety_recommendations
    expected: "Use appropriate PPE and work in a fume hood. Consider alternative solvents."
    tolerance: "exact"
  
  - variable: analysis_results.stability_score
    expected: 0.3
    tolerance: "exact"
  
  - variable: analysis_results.risk_factors
    expected: ["polar solvent", "temperature sensitivity"]
    tolerance: "exact"
```

### Advanced Configuration with All Input Types
```yaml
name: Advanced Chemistry Analysis
agent_type: dynamic_region
file_path: chemistry_agent.py

steps:
  - name: Comprehensive Analysis
    input:
      file_path: chemistry_agent.py
      method: comprehensive_analysis
      input:
        # String inputs
        - name: compound_name
          type: string
          value: "Ethanol"
        
        - name: analysis_request
          type: string
          value: "Please analyze stability and reactivity"
        
        # Dictionary inputs
        - name: experimental_conditions
          type: dict
          value:
            temperature: 298.15
            pressure: 101325
            humidity: 0.5
            light_exposure: "dark"
        
        - name: user_preferences
          type: dict
          value:
            output_format: "detailed"
            include_graphs: true
            language: "en"
        
        # Object inputs
        - name: compound_data
          type: object
          class_path: "input_types.CompoundData"
          args:
            name: "Ethanol"
            molecular_weight: 46.07
            molecular_formula: "C2H5OH"
            properties:
              boiling_point: 78.37
              density: 0.789
        
        - name: experiment_context
          type: object
          class_path: "input_types.ExperimentContext"
          args:
            temperature: 25.0
            solvent: "water"
            catalyst: "none"
            duration: 24.0
        
        # Class object inputs
        - name: feedback_class
          type: class_object
          import_path: "input_types.ChemistFeedback"
        
        - name: saved_model
          type: class_object
          pickle_path: "trained_stability_model.pkl"
```

## Best Practices for Input Configuration

### 1. Input Naming
Use descriptive names for inputs:
```yaml
input:
  - name: chemist_feedback  # Good - descriptive
    type: object
    class_path: "input_types.ChemistFeedback"
    args: {...}
  
  - name: exp_context  # Less descriptive
    type: dict
    value: {...}
```

### 2. Type Validation
Implement validation in your input classes:
```python
@dataclass
class ChemistFeedback:
    text: str
    tags: List[str]
    
    def __post_init__(self):
        if not self.text.strip():
            raise ValueError("Feedback text cannot be empty")
        if not self.tags:
            raise ValueError("At least one tag must be provided")
```

### 3. Error Handling
Handle missing or invalid inputs gracefully:
```python
def analyze_compound(self, *inputs):
    feedback = None
    context = None
    
    for input_item in inputs:
        if isinstance(input_item, ChemistFeedback):
            feedback = input_item
        elif isinstance(input_item, dict):
            context = input_item
    
    if not feedback:
        return "Error: Chemist feedback required"
    
    return self._generate_analysis(feedback, context)
```

### 4. Documentation
Document expected input types and formats:
```python
def analyze_compound(self, *inputs):
    """Analyze compound with multiple inputs.
    
    Expected inputs:
    - ChemistFeedback: Feedback from chemist
    - dict: Experimental context (temperature, solvent, etc.)
    - str: User query
    
    Returns:
        Analysis result as string
    """
```

## Migration Guide

### From Single Input to Multiple Inputs

1. **Update YAML Configuration**
   ```yaml
   # Before
   input: "Simple string"
   
   # After
   input:
     - name: message
       type: string
       value: "Simple string"
   ```

2. **Update Agent Methods**
   ```python
   # Before
   def run(self, input_data):
       return self.process(input_data)
   
   # After
   def run(self, *inputs):
       return self.process_multiple(*inputs)
   ```

3. **Test Compatibility**
   - Run existing tests to ensure they still work
   - Gradually migrate to new format
   - Update documentation

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure class paths are correct
   - Check module availability
   - Verify Python path configuration

2. **Type Errors**
   - Validate input types in YAML
   - Check class constructor signatures
   - Review error messages for details

3. **Pickle Errors**
   - Ensure pickle files are accessible
   - Check file permissions
   - Verify pickle file format compatibility

### Debug Mode
Enable debug logging for detailed information:
```python
import logging
logging.getLogger('kaizen.autofix.test.input_parser').setLevel(logging.DEBUG)
```

## Support

For issues and questions:
1. Check the error messages for specific guidance
2. Review the test examples in `test_agent/`
3. Run the test suite to verify functionality
4. Consult the implementation code for details

---

This enhanced input system provides a powerful foundation for complex agent workflows while maintaining simplicity and backward compatibility.

### Input Types Reference

| Type | Description | Example |
|------|-------------|---------|
| `string` | Simple text input | `{"type": "string", "value": "Hello world"}` |
| `dict` | Structured data | `{"type": "dict", "value": {"key": "value"}}` |
| `object` | Dynamic class instantiation | `{"type": "object", "class_path": "module.Class", "args": {...}}` |
| `class_object` | Load existing class object | `{"type": "class_object", "import_path": "module.Class"}` |
| `inline_object` | Direct class specification in YAML | `{"type": "inline_object", "class_path": "module.Class", "attributes": {...}}` | 