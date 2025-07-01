"""Test Mastra agent support in TypeScript execution."""

import tempfile
import os
from pathlib import Path
import pytest

from .code_region import CodeRegionExtractor, CodeRegionExecutor, AgentEntryPoint, RegionType


class TestMastraAgentSupport:
    """Test Mastra agent support in TypeScript execution."""
    
    def test_extract_mastra_agent_region(self):
        """Test extracting Mastra agent regions."""
        # Create a temporary TypeScript file with Mastra agent
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write("""
import { google } from '@ai-sdk/google';
import { Agent } from '@mastra/core/agent';

export const emailFixAgent = new Agent({
  name: 'Email Fix Agent',
  instructions: `You are an email assistant. Improve this email draft.`,
  model: google('gemini-2.5-flash-preview-05-20'),
});

export async function testEmailAgent(input: string): Promise<string> {
  try {
    const result = await emailFixAgent.run(input);
    return result;
  } catch (error) {
    return `Error: ${error.message}`;
  }
}
""")
            test_file = f.name
        
        try:
            workspace_root = Path(tempfile.gettempdir())
            extractor = CodeRegionExtractor(workspace_root)
            
            # Test extracting the entire file (should detect the agent)
            region_info = extractor.extract_region_ts(Path(test_file), 'main')
            
            # Since we prioritize functions now, it should detect the function first
            assert region_info.type == RegionType.FUNCTION
            assert region_info.name == 'testEmailAgent'  # Should detect the function name
            assert 'testEmailAgent' in region_info.code
            assert 'emailFixAgent' in region_info.code  # Should still include the agent
            
            # Test extracting by function name
            region_info_func = extractor.extract_region_ts_by_name(Path(test_file), 'testEmailAgent')
            
            assert region_info_func.type == RegionType.FUNCTION
            assert region_info_func.name == 'testEmailAgent'
            assert 'testEmailAgent' in region_info_func.code
            
            # Test extracting just the agent by creating a file with only the agent
            with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f2:
                f2.write("""
import { google } from '@ai-sdk/google';
import { Agent } from '@mastra/core/agent';

export const emailFixAgent = new Agent({
  name: 'Email Fix Agent',
  instructions: `You are an email assistant. Improve this email draft.`,
  model: google('gemini-2.5-flash-preview-05-20'),
});
""")
                agent_only_file = f2.name
            
            try:
                region_info_agent = extractor.extract_region_ts(Path(agent_only_file), 'main')
                
                assert region_info_agent.type == RegionType.MODULE
                assert region_info_agent.name == 'emailFixAgent'  # Should detect the agent name
                assert 'emailFixAgent' in region_info_agent.code
                assert 'new Agent' in region_info_agent.code
                
            finally:
                os.unlink(agent_only_file)
            
        finally:
            os.unlink(test_file)
    
    def test_extract_various_agent_patterns(self):
        """Test extracting various agent patterns."""
        # Create a temporary TypeScript file with different agent patterns
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write("""
import { Agent } from '@mastra/core/agent';

// Pattern 1: export const agent = new Agent({...})
export const emailFixAgent = new Agent({
  name: 'Email Fix Agent',
  instructions: 'You are an email assistant.',
});

// Pattern 2: const agent = new Agent({...})
const processAgent = new Agent({
  name: 'Process Agent',
  instructions: 'You are a data processor.',
});

// Pattern 3: export const agent = new SomeAgent({...})
export const customAgent = new CustomAgent({
  name: 'Custom Agent',
});

// Pattern 4: Agent with different method names
export const dataAgent = {
  name: 'Data Agent',
  process: async (input: any) => {
    return `Processed: ${JSON.stringify(input)}`;
  }
};

export const executeAgent = {
  name: 'Execute Agent',
  execute: async (input: any) => {
    return `Executed: ${JSON.stringify(input)}`;
  }
};

export const invokeAgent = {
  name: 'Invoke Agent',
  invoke: async (input: any) => {
    return `Invoked: ${JSON.stringify(input)}`;
  }
};
""")
            test_file = f.name
        
        try:
            workspace_root = Path(tempfile.gettempdir())
            extractor = CodeRegionExtractor(workspace_root)
            
            # Test extracting the entire file
            region_info = extractor.extract_region_ts(Path(test_file), 'main')
            
            # Should detect one of the agent names
            assert region_info.type == RegionType.MODULE
            assert region_info.name in ['emailFixAgent', 'customAgent', 'dataAgent', 'executeAgent', 'invokeAgent']
            
        finally:
            os.unlink(test_file)
    
    def test_agent_execution_script_generation(self):
        """Test that the execution script properly handles agent patterns."""
        workspace_root = Path(tempfile.gettempdir())
        executor = CodeRegionExecutor(workspace_root)
        
        # Test the execution script generation for agent patterns
        script = executor._create_typescript_execution_script(
            '/tmp/test.ts', 
            None, 
            ['test input']
        )
        
        # Should contain agent-specific patterns
        assert 'targetModule.default.run' in script
        assert 'targetModule.default.process' in script
        assert 'targetModule.default.execute' in script
        assert 'targetModule.default.invoke' in script
        
        # Should contain fallback logic for named exports
        assert 'Object.keys(targetModule)' in script
        assert 'exported.run' in script
        assert 'exported.process' in script
        assert 'exported.execute' in script
        assert 'exported.invoke' in script
    
    def test_entry_point_with_agent(self):
        """Test using entry points with agent modules."""
        # Create a temporary TypeScript file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write("""
import { Agent } from '@mastra/core/agent';

export const emailFixAgent = new Agent({
  name: 'Email Fix Agent',
  instructions: 'You are an email assistant.',
});

export class EmailProcessor {
  async process(input: string): Promise<string> {
    return await emailFixAgent.run(input);
  }
}
""")
            test_file = f.name
        
        try:
            workspace_root = Path(tempfile.gettempdir())
            extractor = CodeRegionExtractor(workspace_root)
            
            # Test with class and method entry point
            entry_point = AgentEntryPoint(
                module="email_processor",
                class_name="EmailProcessor",
                method="process"
            )
            
            region_info = extractor.extract_region_by_entry_point_ts(
                Path(test_file), 
                entry_point
            )
            
            assert region_info.entry_point == entry_point
            assert "EmailProcessor" in region_info.code
            assert "process" in region_info.code
            
        finally:
            os.unlink(test_file)


if __name__ == "__main__":
    # Run basic tests
    test = TestMastraAgentSupport()
    test.test_extract_mastra_agent_region()
    test.test_extract_various_agent_patterns()
    test.test_agent_execution_script_generation()
    test.test_entry_point_with_agent()
    print("All Mastra agent support tests passed!") 