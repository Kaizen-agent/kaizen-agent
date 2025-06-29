"""Tests for the new agent entry point system."""

import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from .code_region import (
    CodeRegionExtractor, 
    CodeRegionExecutor, 
    AgentEntryPoint, 
    RegionInfo,
    RegionType
)


class TestAgentEntryPoint:
    """Test the new agent entry point system."""
    
    def test_agent_entry_point_creation(self):
        """Test creating AgentEntryPoint objects."""
        # Test with all fields
        entry_point = AgentEntryPoint(
            module="test_module",
            class_name="TestClass",
            method="test_method",
            fallback_to_function=True
        )
        
        assert entry_point.module == "test_module"
        assert entry_point.class_name == "TestClass"
        assert entry_point.method == "test_method"
        assert entry_point.fallback_to_function is True
        
        # Test with minimal fields
        entry_point = AgentEntryPoint(module="test_module")
        assert entry_point.module == "test_module"
        assert entry_point.class_name is None
        assert entry_point.method is None
        assert entry_point.fallback_to_function is True
    
    def test_extract_region_by_entry_point(self):
        """Test extracting regions using entry points."""
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import json
from typing import Dict, Any

class TestAgent:
    def __init__(self):
        self.processed_count = 0
    
    def process_input(self, input_data):
        self.processed_count += 1
        return {
            'status': 'success',
            'result': f"Processed: {input_data}",
            'count': self.processed_count
        }

def process_function(input_data):
    return {'status': 'success', 'result': input_data}
""")
            test_file = f.name
        
        try:
            workspace_root = Path(tempfile.gettempdir())
            extractor = CodeRegionExtractor(workspace_root)
            
            # Test with class and method
            entry_point = AgentEntryPoint(
                module="test_agent",
                class_name="TestAgent",
                method="process_input"
            )
            
            region_info = extractor.extract_region_by_entry_point(
                Path(test_file), 
                entry_point
            )
            
            assert region_info.entry_point == entry_point
            assert region_info.type == RegionType.CLASS
            assert "TestAgent" in region_info.code
            assert "process_input" in region_info.code
            
        finally:
            os.unlink(test_file)
    
    def test_validate_entry_point(self):
        """Test entry point validation."""
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
class ValidAgent:
    def process(self, data):
        return {'status': 'success', 'data': data}

def valid_function(data):
    return {'status': 'success', 'data': data}

class CallableAgent:
    def __call__(self, data):
        return {'status': 'success', 'data': data}
""")
            test_file = f.name
        
        try:
            workspace_root = Path(tempfile.gettempdir())
            extractor = CodeRegionExtractor(workspace_root)
            
            # Test valid class and method
            entry_point = AgentEntryPoint(
                module="valid_agent",
                class_name="ValidAgent",
                method="process"
            )
            assert extractor.validate_entry_point(entry_point, Path(test_file))
            
            # Test valid function
            entry_point = AgentEntryPoint(
                module="valid_agent",
                method="valid_function"
            )
            assert extractor.validate_entry_point(entry_point, Path(test_file))
            
            # Test callable class
            entry_point = AgentEntryPoint(
                module="valid_agent",
                class_name="CallableAgent"
            )
            assert extractor.validate_entry_point(entry_point, Path(test_file))
            
            # Test invalid class
            entry_point = AgentEntryPoint(
                module="valid_agent",
                class_name="InvalidClass",
                method="process"
            )
            assert not extractor.validate_entry_point(entry_point, Path(test_file))
            
            # Test invalid method
            entry_point = AgentEntryPoint(
                module="valid_agent",
                class_name="ValidAgent",
                method="invalid_method"
            )
            assert not extractor.validate_entry_point(entry_point, Path(test_file))
            
        finally:
            os.unlink(test_file)
    
    def test_execute_with_entry_point(self):
        """Test executing code using entry points."""
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
class TestAgent:
    def __init__(self):
        self.count = 0
    
    def process(self, data):
        self.count += 1
        return {
            'status': 'success',
            'result': f"Processed {self.count}: {data}",
            'count': self.count
        }

def test_function(data):
    return {'status': 'success', 'result': f"Function processed: {data}"}

class CallableAgent:
    def __init__(self):
        self.count = 0
    
    def __call__(self, data):
        self.count += 1
        return {'status': 'success', 'result': f"Callable processed {self.count}: {data}"}
""")
            test_file = f.name
        
        try:
            workspace_root = Path(tempfile.gettempdir())
            executor = CodeRegionExecutor(workspace_root)
            
            # Get the module name from the file name (without .py extension)
            module_name = Path(test_file).stem
            
            # Create region info with entry point
            entry_point = AgentEntryPoint(
                module=module_name,
                class_name="TestAgent",
                method="process"
            )
            
            region_info = RegionInfo(
                type=RegionType.CLASS,
                name="TestAgent",
                code=open(test_file).read(),
                start_line=1,
                end_line=20,
                imports=[],
                dependencies=frozenset(),
                file_path=Path(test_file),
                entry_point=entry_point
            )
            
            # Test execution
            result = executor.execute_region_with_tracking(
                region_info,
                input_data=["test input"],
                tracked_variables=set()
            )
            
            assert result['result']['status'] == 'success'
            assert 'test input' in result['result']['result']
            assert result['result']['count'] == 1
            
            # Test function execution
            entry_point = AgentEntryPoint(
                module=module_name,
                method="test_function"
            )
            
            region_info.entry_point = entry_point
            
            result = executor.execute_region_with_tracking(
                region_info,
                input_data=["function input"],
                tracked_variables=set()
            )
            
            assert result['result']['status'] == 'success'
            assert 'function input' in result['result']['result']
            
            # Test callable class execution
            entry_point = AgentEntryPoint(
                module=module_name,
                class_name="CallableAgent"
            )
            
            region_info.entry_point = entry_point
            
            result = executor.execute_region_with_tracking(
                region_info,
                input_data=["callable input"],
                tracked_variables=set()
            )
            
            assert result['result']['status'] == 'success'
            assert 'callable input' in result['result']['result']
            
        finally:
            os.unlink(test_file)
    
    def test_fallback_to_function(self):
        """Test fallback from class to function."""
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def TestAgent(data):
    return {'status': 'success', 'result': f"Function processed: {data}"}
""")
            test_file = f.name
        
        try:
            workspace_root = Path(tempfile.gettempdir())
            executor = CodeRegionExecutor(workspace_root)
            
            # Get the module name from the file name
            module_name = Path(test_file).stem
            
            # Create entry point that should fallback to function
            entry_point = AgentEntryPoint(
                module=module_name,
                class_name="TestAgent",
                method="process",
                fallback_to_function=True
            )
            
            region_info = RegionInfo(
                type=RegionType.MODULE,
                name=module_name,
                code=open(test_file).read(),
                start_line=1,
                end_line=5,
                imports=[],
                dependencies=frozenset(),
                file_path=Path(test_file),
                entry_point=entry_point
            )
            
            # Test execution with fallback
            result = executor.execute_region_with_tracking(
                region_info,
                input_data=["fallback test"],
                tracked_variables=set()
            )
            
            assert result['result']['status'] == 'success'
            assert 'fallback test' in result['result']['result']
            
        finally:
            os.unlink(test_file)
    
    def test_nested_module_support(self):
        """Test support for nested modules."""
        # Create a nested module structure
        temp_dir = tempfile.mkdtemp()
        try:
            # Create nested directory
            nested_dir = Path(temp_dir) / "agents"
            nested_dir.mkdir()
            
            # Create __init__.py
            init_file = nested_dir / "__init__.py"
            init_file.write_text("")
            
            # Create agent file
            agent_file = nested_dir / "my_agent.py"
            agent_file.write_text("""
class MyAgent:
    def process(self, data):
        return {'status': 'success', 'result': f"Nested processed: {data}"}
""")
            
            workspace_root = Path(temp_dir)
            extractor = CodeRegionExtractor(workspace_root)
            
            # Test with nested module
            entry_point = AgentEntryPoint(
                module="agents.my_agent",
                class_name="MyAgent",
                method="process"
            )
            
            # Validate entry point
            assert extractor.validate_entry_point(entry_point, agent_file)
            
            # Extract region
            region_info = extractor.extract_region_by_entry_point(agent_file, entry_point)
            assert region_info.entry_point == entry_point
            
            # Execute
            executor = CodeRegionExecutor(workspace_root)
            result = executor.execute_region_with_tracking(
                region_info,
                input_data=["nested test"],
                tracked_variables=set()
            )
            
            assert result['result']['status'] == 'success'
            assert 'nested test' in result['result']['result']
            
        finally:
            import shutil
            shutil.rmtree(temp_dir)
    
    def test_error_handling(self):
        """Test error handling in entry point system."""
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
class TestAgent:
    def process(self, data):
        raise ValueError("Test error")
""")
            test_file = f.name
        
        try:
            workspace_root = Path(tempfile.gettempdir())
            executor = CodeRegionExecutor(workspace_root)
            
            # Get the module name from the file name
            module_name = Path(test_file).stem
            
            entry_point = AgentEntryPoint(
                module=module_name,
                class_name="TestAgent",
                method="process"
            )
            
            region_info = RegionInfo(
                type=RegionType.CLASS,
                name="TestAgent",
                code=open(test_file).read(),
                start_line=1,
                end_line=5,
                imports=[],
                dependencies=frozenset(),
                file_path=Path(test_file),
                entry_point=entry_point
            )
            
            # Test execution with error
            result = executor.execute_region_with_tracking(
                region_info,
                input_data=["error test"],
                tracked_variables=set()
            )
            
            assert 'error' in result
            assert 'Test error' in result['error']
            
        finally:
            os.unlink(test_file) 