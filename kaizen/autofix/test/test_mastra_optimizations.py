"""Test Mastra agent optimizations and caching functionality."""

import tempfile
import os
from pathlib import Path
import pytest
import time

from .code_region import CodeRegionExtractor, CodeRegionExecutor, RegionInfo, RegionType


class TestMastraOptimizations:
    """Test Mastra agent optimizations and caching."""
    
    def test_mastra_detection(self):
        """Test that Mastra agents are correctly detected."""
        workspace_root = Path(tempfile.gettempdir())
        executor = CodeRegionExecutor(workspace_root)
        
        # Create a Mastra agent region
        mastra_code = """
import { google } from '@ai-sdk/google';
import { Agent } from '@mastra/core/agent';

export const emailFixAgent = new Agent({
  name: 'Email Fix Agent',
  instructions: 'You are an email assistant.',
  model: google('gemini-2.5-flash-preview-05-20'),
});
"""
        
        region_info = RegionInfo(
            type=RegionType.MODULE,
            name="emailFixAgent",
            code=mastra_code,
            start_line=1,
            end_line=10,
            imports=[],
            dependencies=frozenset(),
            file_path=Path("test.ts")
        )
        
        # Test detection
        assert executor._is_mastra_agent(region_info) == True
        
        # Test non-Mastra code
        simple_code = """
export function simpleFunction(input: string): string {
    return `Hello, ${input}!`;
}
"""
        
        simple_region = RegionInfo(
            type=RegionType.FUNCTION,
            name="simpleFunction",
            code=simple_code,
            start_line=1,
            end_line=5,
            imports=[],
            dependencies=frozenset(),
            file_path=Path("test.ts")
        )
        
        assert executor._is_mastra_agent(simple_region) == False
    
    def test_cache_functionality(self):
        """Test that caching works correctly."""
        workspace_root = Path(tempfile.gettempdir())
        executor = CodeRegionExecutor(workspace_root)
        
        # Test initial cache stats
        stats = executor.get_cache_stats()
        assert stats['execution_cache_size'] == 0
        assert stats['compiled_modules_size'] == 0
        
        # Test cache clearing
        executor.clear_cache()
        stats = executor.get_cache_stats()
        assert stats['execution_cache_size'] == 0
    
    def test_optimized_execution_script(self):
        """Test that optimized execution scripts are generated correctly."""
        workspace_root = Path(tempfile.gettempdir())
        
        # Import the enhanced execution script generator directly
        from .enhanced_code_region import create_enhanced_typescript_execution_script
        
        # Test Mastra-optimized script
        script = create_enhanced_typescript_execution_script(
            "/tmp/test.ts", 
            "testMethod", 
            ["test input"],
            workspace_root,
            is_mastra=True
        )
        
        # Should contain Mastra optimizations
        assert "NODE_ENV = 'production'" in script
        assert "TS_NODE_CACHE = 'true'" in script
        assert "skipLibCheck" in script
        
        # Test regular script
        script = create_enhanced_typescript_execution_script(
            "/tmp/test.ts", 
            "testMethod", 
            ["test input"],
            workspace_root,
            is_mastra=False
        )
        
        # Should not contain Mastra optimizations
        assert "NODE_ENV = 'production'" not in script
    
    def test_cache_key_generation(self):
        """Test that cache keys are generated consistently."""
        workspace_root = Path(tempfile.gettempdir())
        executor = CodeRegionExecutor(workspace_root)
        
        region_info = RegionInfo(
            type=RegionType.FUNCTION,
            name="testFunction",
            code="export function testFunction() { return 'test'; }",
            start_line=1,
            end_line=3,
            imports=[],
            dependencies=frozenset(),
            file_path=Path("test.ts")
        )
        
        # Generate cache keys
        key1 = executor._get_cache_key(region_info, "testMethod", ["input1"])
        key2 = executor._get_cache_key(region_info, "testMethod", ["input1"])
        key3 = executor._get_cache_key(region_info, "testMethod", ["input2"])
        
        # Same inputs should generate same key
        assert key1 == key2
        
        # Different inputs should generate different keys
        assert key1 != key3
    
    def test_ts_node_cache_setup(self):
        """Test that TypeScript cache directory is set up correctly."""
        workspace_root = Path(tempfile.gettempdir())
        executor = CodeRegionExecutor(workspace_root)
        
        # Check that cache directory is set
        assert executor._ts_node_cache_dir is not None
        assert executor._ts_node_cache_dir.exists()
        
        # Check environment variables
        assert os.environ.get('TS_NODE_CACHE') == 'true'
        assert 'TS_NODE_CACHE_DIRECTORY' in os.environ


if __name__ == "__main__":
    # Run basic tests
    test = TestMastraOptimizations()
    test.test_mastra_detection()
    test.test_cache_functionality()
    test.test_optimized_execution_script()
    test.test_cache_key_generation()
    test.test_ts_node_cache_setup()
    print("All Mastra optimization tests passed!") 