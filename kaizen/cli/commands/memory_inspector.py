"""Memory Inspector Utility

This module provides easy-to-use utilities for inspecting and understanding
the ExecutionMemory data structure. It's designed to help developers quickly
understand what data is available and how to access it.

Usage:
    from kaizen.cli.commands.memory_inspector import MemoryInspector
    
    # Create inspector
    inspector = MemoryInspector(memory_instance)
    
    # Quick overview
    inspector.show_overview()
    
    # Detailed inspection
    inspector.show_detailed_structure()
    
    # Export to file
    inspector.export_to_file("memory_dump.json")
    
    # Get specific data
    test_runs = inspector.get_test_runs()
    fix_attempts = inspector.get_fix_attempts()
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from pprint import pprint

from .memory import ExecutionMemory


class MemoryInspector:
    """Utility class for inspecting ExecutionMemory data structure."""
    
    def __init__(self, memory: ExecutionMemory):
        """Initialize with an ExecutionMemory instance.
        
        Args:
            memory: ExecutionMemory instance to inspect
        """
        self.memory = memory
    
    def show_overview(self) -> None:
        """Show a quick overview of the memory structure."""
        print("\n" + "="*60)
        print("MEMORY STRUCTURE OVERVIEW")
        print("="*60)
        
        if not self.memory.current_execution:
            print("❌ No current execution found")
            return
        
        execution = self.memory.current_execution
        
        # Basic info
        print(f"📋 Execution ID: {execution.get('execution_id', 'Unknown')}")
        print(f"⏰ Start Time: {execution.get('start_time', 'Unknown')}")
        print(f"🔄 Duration: {self._calculate_duration(execution.get('start_time'))}")
        
        # Configuration
        config_context = execution.get('configuration_context', {})
        if config_context:
            config_meta = config_context.get('config_metadata', {})
            config_values = config_context.get('config_values', {})
            print(f"\n⚙️  Configuration:")
            print(f"   - Name: {config_meta.get('config_name', 'Unknown')}")
            print(f"   - Auto Fix: {config_values.get('auto_fix', 'Unknown')}")
            print(f"   - Better AI: {config_values.get('better_ai', 'Unknown')}")
            print(f"   - Max Retries: {config_values.get('max_retries', 'Unknown')}")
        
        # Test runs
        test_runs = execution.get('test_runs', [])
        print(f"\n🧪 Test Runs: {len(test_runs)} total")
        if test_runs:
            latest_run = test_runs[-1]
            if latest_run.summary:
                print(f"   - Latest Success Rate: {latest_run.summary.get('success_rate', 0):.1%}")
                print(f"   - Total Tests: {latest_run.summary.get('total_tests', 0)}")
                print(f"   - Passed: {latest_run.summary.get('passed_tests', 0)}")
                print(f"   - Failed: {latest_run.summary.get('failed_tests', 0)}")
        
        # LLM interactions
        llm_interactions = execution.get('llm_interactions', [])
        print(f"\n🤖 LLM Interactions: {len(llm_interactions)} total")
        if llm_interactions:
            interaction_types = {}
            for interaction in llm_interactions:
                interaction_type = interaction.interaction_type
                interaction_types[interaction_type] = interaction_types.get(interaction_type, 0) + 1
            print(f"   - Types: {dict(interaction_types)}")
        
        # Fix attempts
        fix_attempts = execution.get('fix_attempts', [])
        print(f"\n🔧 Fix Attempts: {len(fix_attempts)} total")
        if fix_attempts:
            successful = sum(1 for attempt in fix_attempts if attempt.success)
            print(f"   - Successful: {successful}")
            print(f"   - Failed: {len(fix_attempts) - successful}")
            print(f"   - Success Rate: {successful/len(fix_attempts):.1%}")
        
        print("="*60)
    
    def show_detailed_structure(self, max_items: int = 5) -> None:
        """Show detailed structure of memory data.
        
        Args:
            max_items: Maximum number of items to show in lists
        """
        print("\n" + "="*60)
        print("DETAILED MEMORY STRUCTURE")
        print("="*60)
        
        if not self.memory.current_execution:
            print("❌ No current execution found")
            return
        
        execution = self.memory.current_execution
        
        # Show all top-level keys
        print(f"\n📁 Top-level keys in execution:")
        for key in execution.keys():
            value = execution[key]
            if isinstance(value, list):
                print(f"   - {key}: List with {len(value)} items")
            elif isinstance(value, dict):
                print(f"   - {key}: Dict with {len(value)} keys")
            else:
                print(f"   - {key}: {type(value).__name__} = {value}")
        
        # Show test runs in detail
        test_runs = execution.get('test_runs', [])
        if test_runs:
            print(f"\n🧪 Test Runs Detail (showing first {min(max_items, len(test_runs))}):")
            for i, run in enumerate(test_runs[:max_items]):
                print(f"   Run {i+1}:")
                print(f"     - ID: {run.test_run_id}")
                print(f"     - Attempt: {run.attempt_number}")
                print(f"     - Timestamp: {run.timestamp}")
                print(f"     - Test Cases: {len(run.test_cases) if run.test_cases else 0}")
                print(f"     - Failed: {len(run.failed_test_cases) if run.failed_test_cases else 0}")
                print(f"     - Passed: {len(run.passed_test_cases) if run.passed_test_cases else 0}")
                if run.summary:
                    print(f"     - Success Rate: {run.summary.get('success_rate', 0):.1%}")
        
        # Show fix attempts in detail
        fix_attempts = execution.get('fix_attempts', [])
        if fix_attempts:
            print(f"\n🔧 Fix Attempts Detail (showing first {min(max_items, len(fix_attempts))}):")
            for i, attempt in enumerate(fix_attempts[:max_items]):
                print(f"   Attempt {i+1}:")
                print(f"     - Number: {attempt.attempt_number}")
                print(f"     - Success: {'✅' if attempt.success else '❌'}")
                print(f"     - Approach: {attempt.approach_description[:50]}...")
                print(f"     - Timestamp: {attempt.timestamp}")
                if attempt.lessons_learned:
                    print(f"     - Lessons: {attempt.lessons_learned[:50]}...")
        
        # Show LLM interactions in detail
        llm_interactions = execution.get('llm_interactions', [])
        if llm_interactions:
            print(f"\n🤖 LLM Interactions Detail (showing first {min(max_items, len(llm_interactions))}):")
            for i, interaction in enumerate(llm_interactions[:max_items]):
                print(f"   Interaction {i+1}:")
                print(f"     - Type: {interaction.interaction_type}")
                print(f"     - Timestamp: {interaction.timestamp}")
                print(f"     - Prompt Length: {len(interaction.prompt)} chars")
                print(f"     - Response Length: {len(interaction.response)} chars")
                if interaction.reasoning:
                    print(f"     - Has Reasoning: Yes")
        
        print("="*60)
    
    def show_schema(self) -> None:
        """Show the complete memory schema."""
        print("\n" + "="*60)
        print("MEMORY SCHEMA")
        print("="*60)
        
        schema = self.memory.get_memory_schema()
        
        for level_name, level_info in schema.items():
            print(f"\n📋 {level_name.upper().replace('_', ' ')}:")
            print(f"   Description: {level_info['description']}")
            print(f"   Fields:")
            for field_name, field_info in level_info['fields'].items():
                print(f"     - {field_name}: {field_info['type']} - {field_info['description']}")
        
        print("="*60)
    
    def show_summary(self) -> None:
        """Show comprehensive summary statistics."""
        print("\n" + "="*60)
        print("MEMORY SUMMARY STATISTICS")
        print("="*60)
        
        summary = self.memory.get_memory_summary()
        
        if 'error' in summary:
            print(f"❌ {summary['error']}")
            return
        
        # Basic info
        print(f"📋 Execution ID: {summary['execution_id']}")
        print(f"⏰ Start Time: {summary['start_time']}")
        print(f"🔄 Duration: {summary['duration']}")
        
        # Test execution
        test_exec = summary['test_execution']
        print(f"\n🧪 Test Execution:")
        print(f"   - Total Runs: {test_exec['total_runs']}")
        print(f"   - Total Test Cases: {test_exec['total_test_cases']}")
        print(f"   - Total Passed: {test_exec['total_passed']}")
        print(f"   - Total Failed: {test_exec['total_failed']}")
        print(f"   - Total Errors: {test_exec['total_errors']}")
        print(f"   - Average Success Rate: {test_exec['average_success_rate']:.1%}")
        print(f"   - Best Success Rate: {test_exec['best_success_rate']:.1%}")
        print(f"   - Worst Success Rate: {test_exec['worst_success_rate']:.1%}")
        
        # Fix attempts
        fix_attempts = summary['fix_attempts']
        print(f"\n🔧 Fix Attempts:")
        print(f"   - Total Attempts: {fix_attempts['total_attempts']}")
        print(f"   - Successful Fixes: {fix_attempts['successful_fixes']}")
        print(f"   - Failed Fixes: {fix_attempts['failed_fixes']}")
        print(f"   - Success Rate: {fix_attempts['success_rate']:.1%}")
        
        # LLM interactions
        llm_interactions = summary['llm_interactions']
        print(f"\n🤖 LLM Interactions:")
        print(f"   - Total Interactions: {llm_interactions['total_interactions']}")
        print(f"   - Interaction Types: {llm_interactions['interaction_types']}")
        print(f"   - Total Prompt Chars: {llm_interactions['total_prompt_chars']:,}")
        print(f"   - Total Response Chars: {llm_interactions['total_response_chars']:,}")
        print(f"   - Avg Prompt Length: {llm_interactions['average_prompt_length']:.0f} chars")
        print(f"   - Avg Response Length: {llm_interactions['average_response_length']:.0f} chars")
        
        # Configuration
        config = summary['configuration']
        print(f"\n⚙️  Configuration:")
        print(f"   - Config Name: {config['config_name']}")
        print(f"   - Auto Fix: {config['auto_fix_enabled']}")
        print(f"   - Better AI: {config['better_ai_enabled']}")
        print(f"   - Max Retries: {config['max_retries']}")
        print(f"   - Language: {config['language']}")
        print(f"   - Files to Fix: {len(config['files_to_fix'])} files")
        
        # Learning data
        learning = summary['learning_data']
        print(f"\n🧠 Learning Data:")
        print(f"   - Original Code Sections: {learning['original_code_sections']}")
        print(f"   - Failed Approaches: {learning['failed_approaches']}")
        print(f"   - Successful Patterns: {learning['successful_patterns']}")
        
        print("="*60)
    
    def export_to_file(self, file_path: str, format: str = 'json') -> None:
        """Export memory data to a file.
        
        Args:
            file_path: Path to save the file
            format: Export format ('json' or 'txt')
        """
        if format == 'json':
            json_data = self.memory.export_memory_to_json(file_path=file_path)
            print(f"✅ Memory data exported to JSON: {file_path}")
        elif format == 'txt':
            with open(file_path, 'w') as f:
                f.write("MEMORY DATA EXPORT\n")
                f.write("="*50 + "\n\n")
                
                # Write overview
                f.write("OVERVIEW:\n")
                summary = self.memory.get_memory_summary()
                for key, value in summary.items():
                    if isinstance(value, dict):
                        f.write(f"{key}:\n")
                        for subkey, subvalue in value.items():
                            f.write(f"  {subkey}: {subvalue}\n")
                    else:
                        f.write(f"{key}: {value}\n")
                
                f.write("\n" + "="*50 + "\n")
                f.write("DETAILED STRUCTURE:\n")
                
                # Write detailed structure
                if self.memory.current_execution:
                    execution = self.memory.current_execution
                    f.write(f"Execution ID: {execution.get('execution_id')}\n")
                    f.write(f"Start Time: {execution.get('start_time')}\n")
                    f.write(f"Test Runs: {len(execution.get('test_runs', []))}\n")
                    f.write(f"LLM Interactions: {len(execution.get('llm_interactions', []))}\n")
                    f.write(f"Fix Attempts: {len(execution.get('fix_attempts', []))}\n")
            
            print(f"✅ Memory data exported to text: {file_path}")
        else:
            print(f"❌ Unsupported format: {format}")
    
    def get_test_runs(self) -> List[Dict]:
        """Get all test runs as dictionaries.
        
        Returns:
            List of test run dictionaries
        """
        if not self.memory.current_execution:
            return []
        
        return [asdict(run) for run in self.memory.current_execution.get('test_runs', [])]
    
    def get_fix_attempts(self) -> List[Dict]:
        """Get all fix attempts as dictionaries.
        
        Returns:
            List of fix attempt dictionaries
        """
        if not self.memory.current_execution:
            return []
        
        return [asdict(attempt) for attempt in self.memory.current_execution.get('fix_attempts', [])]
    
    def get_llm_interactions(self) -> List[Dict]:
        """Get all LLM interactions as dictionaries.
        
        Returns:
            List of LLM interaction dictionaries
        """
        if not self.memory.current_execution:
            return []
        
        return [asdict(interaction) for interaction in self.memory.current_execution.get('llm_interactions', [])]
    
    def get_failed_test_cases(self) -> List[Dict]:
        """Get all failed test cases from the latest run.
        
        Returns:
            List of failed test case dictionaries
        """
        failed_cases = self.memory.get_failed_cases_latest_run()
        return [asdict(case) for case in failed_cases]
    
    def get_learning_context(self, file_path: str = None) -> Dict:
        """Get learning context for a specific file.
        
        Args:
            file_path: Path to the file (None for current)
            
        Returns:
            Learning context dictionary
        """
        return self.memory.get_previous_attempts_insights(file_path)
    
    def _calculate_duration(self, start_time) -> str:
        """Calculate duration from start time.
        
        Args:
            start_time: Start time datetime
            
        Returns:
            Duration string
        """
        if not start_time:
            return "Unknown"
        
        duration = datetime.now() - start_time
        return str(duration)


def quick_inspect(memory: ExecutionMemory) -> None:
    """Quick inspection function for immediate use.
    
    Args:
        memory: ExecutionMemory instance to inspect
    """
    inspector = MemoryInspector(memory)
    inspector.show_overview()


def detailed_inspect(memory: ExecutionMemory) -> None:
    """Detailed inspection function for comprehensive analysis.
    
    Args:
        memory: ExecutionMemory instance to inspect
    """
    inspector = MemoryInspector(memory)
    inspector.show_overview()
    inspector.show_detailed_structure()
    inspector.show_summary()


def export_inspection(memory: ExecutionMemory, file_path: str) -> None:
    """Export inspection results to file.
    
    Args:
        memory: ExecutionMemory instance to inspect
        file_path: Path to save the export
    """
    inspector = MemoryInspector(memory)
    inspector.export_to_file(file_path, 'json') 