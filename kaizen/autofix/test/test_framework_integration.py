def test_framework_parameter_in_execution():
    """Test that the framework parameter is passed through to execute_region_with_tracking."""
    from kaizen.autofix.test.code_region import CodeRegionExecutor, RegionInfo, RegionType
    from pathlib import Path
    import tempfile
    import os
    
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
class TestAgent:
    def process(self, data):
        return {'status': 'success', 'result': f"Processed: {data}", 'framework': 'test'}
""")
        test_file = f.name
    
    try:
        workspace_root = Path(tempfile.gettempdir())
        executor = CodeRegionExecutor(workspace_root)
        
        # Create region info
        region_info = RegionInfo(
            type=RegionType.CLASS,
            name='TestAgent',
            code=open(test_file).read(),
            start_line=1,
            end_line=5,
            imports=[],
            dependencies=frozenset(),
            class_methods=['process']
        )
        
        # Test with framework parameter
        test_framework = 'llamaindex'
        result = executor.execute_region_with_tracking(
            region_info,
            method_name='process',
            input_data=['test data'],
            tracked_variables=set(),
            framework=test_framework
        )
        
        # Verify the execution worked
        assert 'result' in result
        assert result['result']['status'] == 'success'
        assert 'test data' in result['result']['result']
        
        print(f"✅ Framework parameter '{test_framework}' passed through successfully")
        
    finally:
        os.unlink(test_file)

if __name__ == "__main__":
    test_framework_parameter_in_execution()
    print("🎉 Framework parameter integration test passed!") 