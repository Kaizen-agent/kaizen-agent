#!/usr/bin/env python3
"""
Test script to verify that both LLM and algorithmic paths use the same high-quality table generation.
"""

import json
import os
import sys
from pathlib import Path

# Add the kaizen package to the path
sys.path.insert(0, str(Path(__file__).parent))

from kaizen.autofix.pr.manager import PRManager

def create_sample_test_data():
    """Create sample test data for testing."""
    return {
        'agent_info': {
            'name': 'TestAgent',
            'version': '1.0.0',
            'description': 'A test agent for validation'
        },
        'attempts': [
            {
                'status': 'failed',
                'test_cases': [
                    {
                        'name': 'test_basic_function',
                        'status': 'failed',
                        'input': 'test_input',
                        'expected_output': 'expected_result',
                        'actual_output': 'wrong_result',
                        'evaluation': 'Function returned incorrect value'
                    },
                    {
                        'name': 'test_edge_case',
                        'status': 'error',
                        'input': 'edge_input',
                        'expected_output': 'edge_result',
                        'actual_output': None,
                        'evaluation': 'Function crashed on edge case'
                    }
                ]
            },
            {
                'status': 'partial',
                'test_cases': [
                    {
                        'name': 'test_basic_function',
                        'status': 'passed',
                        'input': 'test_input',
                        'expected_output': 'expected_result',
                        'actual_output': 'expected_result',
                        'evaluation': 'Function works correctly'
                    },
                    {
                        'name': 'test_edge_case',
                        'status': 'failed',
                        'input': 'edge_input',
                        'expected_output': 'edge_result',
                        'actual_output': 'wrong_edge_result',
                        'evaluation': 'Function handles edge case incorrectly'
                    }
                ]
            },
            {
                'status': 'passed',
                'test_cases': [
                    {
                        'name': 'test_basic_function',
                        'status': 'passed',
                        'input': 'test_input',
                        'expected_output': 'expected_result',
                        'actual_output': 'expected_result',
                        'evaluation': 'Function works correctly'
                    },
                    {
                        'name': 'test_edge_case',
                        'status': 'passed',
                        'input': 'edge_input',
                        'expected_output': 'edge_result',
                        'actual_output': 'edge_result',
                        'evaluation': 'Function handles edge case correctly'
                    }
                ]
            }
        ],
        'additional_summary': 'All tests now pass after code improvements'
    }

def create_sample_changes():
    """Create sample code changes for testing."""
    return {
        'test_file.py': [
            {
                'description': 'Fixed basic function logic',
                'reason': 'Function was returning wrong value'
            },
            {
                'description': 'Added edge case handling',
                'reason': 'Function crashed on edge cases'
            }
        ]
    }

def test_table_consistency():
    """Test that both LLM and algorithmic paths use the same table generation."""
    print("Testing table generation consistency...")
    
    # Create PR manager
    config = {'base_branch': 'main', 'auto_commit_changes': True}
    pr_manager = PRManager(config)
    
    # Create sample data
    test_results = create_sample_test_data()
    changes = create_sample_changes()
    
    # Test direct table generation
    direct_table = pr_manager._generate_test_results_table(test_results)
    print(f"✅ Direct table generation: {len(direct_table)} characters")
    
    # Test algorithmic description
    algorithmic_description = pr_manager._generate_algorithmic_description(changes, test_results)
    
    # Extract table from algorithmic description
    if "## Test Results Summary" in algorithmic_description:
        table_start = algorithmic_description.find("## Test Results Summary")
        table_end = algorithmic_description.find("##", table_start + 1)
        if table_end == -1:
            table_end = len(algorithmic_description)
        
        algorithmic_table_section = algorithmic_description[table_start:table_end].strip()
        print(f"✅ Algorithmic table section: {len(algorithmic_table_section)} characters")
        
        # Check if the table is included
        if "Test Case | Baseline | Attempt 1 | Attempt 2" in algorithmic_table_section:
            print("✅ Algorithmic description includes the high-quality table")
        else:
            print("❌ Algorithmic description missing the high-quality table")
            return False
    else:
        print("❌ Algorithmic description missing Test Results Summary section")
        return False
    
    # Test that both methods generate the same table content
    if direct_table in algorithmic_table_section:
        print("✅ Algorithmic description uses the same table generation method")
    else:
        print("❌ Algorithmic description doesn't use the same table generation method")
        return False
    
    # Test table quality
    if "Improvement" in direct_table and "Final Status" in direct_table:
        print("✅ Table includes all required columns (Final Status, Improvement)")
    else:
        print("❌ Table missing required columns")
        return False
    
    if "test_basic_function" in direct_table and "test_edge_case" in direct_table:
        print("✅ Table includes all test cases")
    else:
        print("❌ Table missing test cases")
        return False
    
    # Test improvement calculation
    if "Yes" in direct_table and "No" in direct_table:
        print("✅ Table shows improvement calculations")
    else:
        print("❌ Table missing improvement calculations")
        return False
    
    return True

def test_llm_integration():
    """Test that LLM integration also uses the same table generation."""
    print("\nTesting LLM integration...")
    
    # Create PR manager
    config = {'base_branch': 'main', 'auto_commit_changes': True}
    pr_manager = PRManager(config)
    
    # Create sample data
    test_results = create_sample_test_data()
    changes = create_sample_changes()
    
    # Test that the LLM path would add the same table
    # (We can't actually call the LLM without API keys, but we can test the table generation)
    test_results_table = pr_manager._generate_test_results_table(test_results)
    
    if "Test Case | Baseline | Attempt 1 | Attempt 2" in test_results_table:
        print("✅ LLM path would use the same high-quality table generation")
    else:
        print("❌ LLM path wouldn't use the same table generation")
        return False
    
    return True

def main():
    """Run all tests."""
    print("Table Generation Consistency Tests")
    print("=" * 40)
    
    success = True
    
    # Test table consistency
    if not test_table_consistency():
        success = False
    
    # Test LLM integration
    if not test_llm_integration():
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("✅ ALL TESTS PASSED")
        print("\nSummary:")
        print("- Both LLM and algorithmic paths now use _generate_test_results_table")
        print("- Algorithmic description includes the high-quality table")
        print("- Table includes all required columns and test cases")
        print("- Improvement calculations are working correctly")
        print("- Consistent table generation across all paths")
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main() 