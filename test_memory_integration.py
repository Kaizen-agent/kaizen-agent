#!/usr/bin/env python3
"""Test script to verify memory system integration in AutoFix."""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from kaizen.autofix.main import AutoFix
from kaizen.cli.commands.memory import ExecutionMemory

def test_memory_integration():
    """Test that AutoFix properly integrates with the memory system."""
    print("🧪 Testing Memory System Integration")
    print("=" * 40)
    
    # Create a mock configuration
    config = {
        'max_retries': 2,
        'create_pr': False,
        'auto_fix': True,
        'preserve_partial_improvements': True
    }
    
    # Create runner config with required fields
    runner_config = {
        'name': 'test_memory_integration',
        'file_path': 'test_file.py',
        'test_timeout': 30,
        'max_retries': 1,
        'tests': []  # Empty tests list
    }
    
    # Create memory system
    memory = ExecutionMemory()
    
    # Initialize AutoFix with memory
    autofix = AutoFix(config, runner_config, memory=memory)
    
    print("✅ AutoFix initialized with memory system")
    
    # Test that memory is properly stored
    assert autofix.memory is not None, "Memory should be stored in AutoFix"
    print("✅ Memory system properly stored in AutoFix")
    
    # Test memory learning summary method
    learning_summary = autofix._get_memory_learning_summary()
    assert isinstance(learning_summary, dict), "Learning summary should be a dictionary"
    assert 'total_attempts' in learning_summary, "Learning summary should have total_attempts"
    assert 'successful_patterns' in learning_summary, "Learning summary should have successful_patterns"
    print("✅ Memory learning summary method works correctly")
    
    # Test that AutoFix can be initialized without memory (backward compatibility)
    autofix_no_memory = AutoFix(config, runner_config, memory=None)
    assert autofix_no_memory.memory is None, "Memory should be None when not provided"
    print("✅ AutoFix works without memory system (backward compatibility)")
    
    # Test learning summary without memory
    learning_summary_no_memory = autofix_no_memory._get_memory_learning_summary()
    assert learning_summary_no_memory['total_attempts'] == 0, "Should return empty summary when no memory"
    print("✅ Learning summary works correctly without memory")
    
    print("\n✅ All memory integration tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_memory_integration()
        print("\n🎉 Memory system integration is working correctly!")
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 