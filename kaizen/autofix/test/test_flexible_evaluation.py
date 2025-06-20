"""Tests for flexible output evaluation functionality."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

from kaizen.autofix.test.variable_tracker import VariableTracker, track_variables, safe_serialize_value
from kaizen.autofix.test.test_case import TestCase, EvaluationResponse
from kaizen.autofix.test.code_region import CodeRegionExecutor, RegionInfo, RegionType
from kaizen.autofix.test.runner import TestRunner


class TestVariableTracker:
    """Test variable tracking functionality."""
    
    def test_variable_tracking_basic(self):
        """Test basic variable tracking functionality."""
        tracker = VariableTracker()
        
        # Test tracking variables
        tracker.start_tracking({'test_var', 'another_var'})
        
        # Simulate variable assignments
        test_namespace = {'test_var': 'test_value', 'another_var': 42}
        
        # Mock frame for testing
        mock_frame = Mock()
        mock_frame.f_locals = test_namespace
        mock_frame.f_lineno = 10
        
        # Simulate tracking
        tracker._track_line_variables(mock_frame)
        
        # Check tracked values
        assert tracker.get_variable_value('test_var') == 'test_value'
        assert tracker.get_variable_value('another_var') == 42
        
        tracker.stop_tracking()
    
    def test_return_value_tracking(self):
        """Test return value tracking."""
        tracker = VariableTracker()
        tracker.start_tracking(set())
        
        # Simulate return value
        tracker._track_return_value("return_value")
        
        assert tracker.get_return_value() == "return_value"
        
        tracker.stop_tracking()
    
    def test_context_manager(self):
        """Test variable tracking context manager."""
        with track_variables({'test_var'}) as tracker:
            # Simulate variable assignment
            test_namespace = {'test_var': 'test_value'}
            mock_frame = Mock()
            mock_frame.f_locals = test_namespace
            mock_frame.f_lineno = 10
            
            tracker._track_line_variables(mock_frame)
            
            assert tracker.get_variable_value('test_var') == 'test_value'


class TestSafeSerializeValue:
    """Test safe value serialization."""
    
    def test_serialize_none(self):
        """Test serializing None value."""
        result = safe_serialize_value(None)
        assert result == "None"
    
    def test_serialize_string(self):
        """Test serializing string value."""
        result = safe_serialize_value("test string")
        assert result == "test string"
    
    def test_serialize_dict(self):
        """Test serializing dictionary value."""
        test_dict = {"key": "value", "number": 42}
        result = safe_serialize_value(test_dict)
        assert '"key": "value"' in result
        assert '"number": 42' in result
    
    def test_serialize_list(self):
        """Test serializing list value."""
        test_list = [1, 2, 3, "test"]
        result = safe_serialize_value(test_list)
        assert "1" in result
        assert "2" in result
        assert "3" in result
        assert "test" in result


class TestFlexibleEvaluation:
    """Test flexible evaluation functionality."""
    
    def test_evaluation_targets_parsing(self):
        """Test parsing evaluation targets from configuration."""
        test_data = {
            'evaluation_targets': [
                {
                    'name': 'summary_text',
                    'source': 'variable',
                    'criteria': 'Should include clarification about stability',
                    'description': 'Summary should explain stability concerns'
                },
                {
                    'name': 'return',
                    'source': 'return',
                    'criteria': 'Should be a dictionary with status key'
                }
            ]
        }
        
        test_case = TestCase.from_dict({
            'name': 'test',
            'input': {},
            'evaluation_targets': test_data['evaluation_targets']
        })
        
        assert len(test_case.evaluation_targets) == 2
        assert test_case.evaluation_targets[0]['name'] == 'summary_text'
        assert test_case.evaluation_targets[0]['source'] == 'variable'
        assert test_case.evaluation_targets[1]['name'] == 'return'
        assert test_case.evaluation_targets[1]['source'] == 'return'
    
    def test_evaluation_response_with_targets(self):
        """Test evaluation response with target evaluations."""
        response_data = {
            'status': 'passed',
            'evaluation': 'Overall evaluation passed',
            'reasoning': 'All targets met criteria',
            'confidence': 0.9,
            'target_evaluations': {
                'summary_text': {
                    'status': 'passed',
                    'evaluation': 'Summary text meets criteria',
                    'reasoning': 'Contains stability information'
                },
                'return': {
                    'status': 'passed',
                    'evaluation': 'Return value has correct structure',
                    'reasoning': 'Contains required keys'
                }
            }
        }
        
        response = EvaluationResponse(**response_data)
        assert response.status == 'passed'
        assert response.target_evaluations is not None
        assert 'summary_text' in response.target_evaluations
        assert 'return' in response.target_evaluations


class TestCodeRegionExecutorWithTracking:
    """Test code region executor with variable tracking."""
    
    def test_execute_region_with_tracking(self):
        """Test executing a region with variable tracking."""
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
class TestClass:
    def test_method(self, input_data):
        result = "processed " + input_data
        summary = "Summary: " + result
        return {"result": result, "summary": summary}
""")
            test_file = f.name
        
        try:
            workspace_root = Path(tempfile.gettempdir())
            executor = CodeRegionExecutor(workspace_root)
            
            # Create region info
            region_info = RegionInfo(
                type=RegionType.CLASS,
                name='TestClass',
                code=open(test_file).read(),
                start_line=1,
                end_line=10,
                imports=[],
                dependencies=frozenset(),
                class_methods=['test_method']
            )
            
            # Execute with tracking
            tracked_variables = {'result', 'summary'}
            result = executor.execute_region_with_tracking(
                region_info,
                'test_method',
                'test input',
                tracked_variables
            )
            
            assert 'result' in result
            assert 'tracked_values' in result
            assert 'tracked_variables' in result
            
            # Check that tracked values are captured
            tracked_values = result['tracked_values']
            assert 'result' in tracked_values
            assert 'summary' in tracked_values
            
        finally:
            os.unlink(test_file)


if __name__ == "__main__":
    pytest.main([__file__]) 