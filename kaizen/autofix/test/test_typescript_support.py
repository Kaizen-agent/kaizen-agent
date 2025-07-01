"""Test TypeScript support functionality."""

import tempfile
import os
from pathlib import Path
import pytest

from .code_region import CodeRegionExtractor, CodeRegionExecutor, AgentEntryPoint, RegionType


class TestTypeScriptSupport:
    """Test TypeScript support in CodeRegionExtractor and CodeRegionExecutor."""
    
    def test_extract_region_ts(self):
        """Test extracting TypeScript regions."""
        # Create a temporary TypeScript file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write("""
import { Request, Response } from 'express';

// kaizen:start:test_function
export function testFunction(input: string): string {
    return `Hello, ${input}!`;
}
// kaizen:end:test_function

export class TestClass {
    private value: string;
    
    constructor(value: string) {
        this.value = value;
    }
    
    getValue(): string {
        return this.value;
    }
}
""")
            test_file = f.name
        
        try:
            workspace_root = Path(tempfile.gettempdir())
            extractor = CodeRegionExtractor(workspace_root)
            
            # Test extracting a specific region
            region_info = extractor.extract_region_ts(Path(test_file), 'test_function')
            
            assert region_info.type == RegionType.FUNCTION
            assert region_info.name == 'testFunction'
            assert 'testFunction' in region_info.code
            assert 'Hello, ${input}!' in region_info.code
            
            # Test extracting the entire file
            region_info_main = extractor.extract_region_ts(Path(test_file), 'main')
            
            assert region_info_main.type == RegionType.CLASS
            assert region_info_main.name == 'TestClass'
            assert 'TestClass' in region_info_main.code
            assert 'getValue' in region_info_main.code
            
        finally:
            os.unlink(test_file)
    
    def test_extract_region_ts_by_name(self):
        """Test extracting TypeScript functions by name."""
        # Create a temporary TypeScript file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write("""
import * as fs from 'fs';

export function processData(data: any[]): any[] {
    return data.map(item => ({ ...item, processed: true }));
}

export const asyncProcessor = async (input: string): Promise<string> => {
    return new Promise(resolve => {
        setTimeout(() => resolve(`Processed: ${input}`), 100);
    });
};

export class DataProcessor {
    async process(input: any): Promise<any> {
        return { result: input, timestamp: Date.now() };
    }
}
""")
            test_file = f.name
        
        try:
            workspace_root = Path(tempfile.gettempdir())
            extractor = CodeRegionExtractor(workspace_root)
            
            # Test extracting function by name
            region_info = extractor.extract_region_ts_by_name(Path(test_file), 'processData')
            
            assert region_info.type == RegionType.FUNCTION
            assert region_info.name == 'processData'
            assert 'processData' in region_info.code
            assert 'data.map' in region_info.code
            
            # Test extracting async function
            region_info_async = extractor.extract_region_ts_by_name(Path(test_file), 'asyncProcessor')
            
            assert region_info_async.type == RegionType.FUNCTION
            assert region_info_async.name == 'asyncProcessor'
            assert 'asyncProcessor' in region_info_async.code
            assert 'Promise' in region_info_async.code
            
        finally:
            os.unlink(test_file)
    
    def test_extract_region_by_entry_point_ts(self):
        """Test extracting TypeScript regions using entry points."""
        # Create a temporary TypeScript file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write("""
import { Request, Response } from 'express';

export class TestAgent {
    private config: any;
    
    constructor(config: any) {
        this.config = config;
    }
    
    async process(input: any): Promise<any> {
        return {
            status: 'success',
            result: `Processed: ${JSON.stringify(input)}`,
            config: this.config
        };
    }
}

export function simpleProcessor(input: string): string {
    return `Simple: ${input}`;
}
""")
            test_file = f.name
        
        try:
            workspace_root = Path(tempfile.gettempdir())
            extractor = CodeRegionExtractor(workspace_root)
            
            # Test with class and method
            entry_point = AgentEntryPoint(
                module="test_agent",
                class_name="TestAgent",
                method="process"
            )
            
            region_info = extractor.extract_region_by_entry_point_ts(
                Path(test_file), 
                entry_point
            )
            
            assert region_info.entry_point == entry_point
            assert region_info.type == RegionType.CLASS
            assert "TestAgent" in region_info.code
            assert "process" in region_info.code
            
        finally:
            os.unlink(test_file)
    
    def test_extract_imports_ts(self):
        """Test extracting imports from TypeScript code."""
        workspace_root = Path(tempfile.gettempdir())
        extractor = CodeRegionExtractor(workspace_root)
        
        # Test TypeScript import patterns
        ts_code = """
import { Request, Response } from 'express';
import * as fs from 'fs';
import path from 'path';
import { readFile, writeFile } from 'fs/promises';
import { User as UserModel } from './models/user';
import './utils/logger';
"""
        
        # Use the private method for testing
        imports = extractor._extract_imports_ts(ts_code)
        
        assert len(imports) >= 4  # Should find multiple imports
        assert any(imp.module == 'express' for imp in imports)
        assert any(imp.module == 'fs' for imp in imports)
        assert any(imp.module == 'path' for imp in imports)
    
    def test_determine_region_type_ts(self):
        """Test determining TypeScript region types."""
        workspace_root = Path(tempfile.gettempdir())
        extractor = CodeRegionExtractor(workspace_root)
        
        # Test class detection
        class_code = """
export class TestClass {
    private value: string;
    
    constructor(value: string) {
        this.value = value;
    }
    
    getValue(): string {
        return this.value;
    }
    
    setValue(value: string): void {
        this.value = value;
    }
}
"""
        
        region_type, name, methods = extractor._determine_region_type_ts(class_code)
        assert region_type == RegionType.CLASS
        assert name == 'TestClass'
        assert 'getValue' in methods
        assert 'setValue' in methods
        
        # Test function detection
        function_code = """
export function testFunction(input: string): string {
    return `Hello, ${input}!`;
}
"""
        
        region_type, name, methods = extractor._determine_region_type_ts(function_code)
        assert region_type == RegionType.FUNCTION
        assert name == 'testFunction'
        assert methods == []
        
        # Test async function detection
        async_function_code = """
export const asyncFunction = async (input: string): Promise<string> => {
    return new Promise(resolve => resolve(`Async: ${input}`));
};
"""
        
        region_type, name, methods = extractor._determine_region_type_ts(async_function_code)
        assert region_type == RegionType.FUNCTION
        assert name == 'asyncFunction'
        assert methods == []


if __name__ == "__main__":
    # Run basic tests
    test = TestTypeScriptSupport()
    test.test_extract_region_ts()
    test.test_extract_region_ts_by_name()
    test.test_extract_region_by_entry_point_ts()
    test.test_extract_imports_ts()
    test.test_determine_region_type_ts()
    print("All TypeScript support tests passed!") 