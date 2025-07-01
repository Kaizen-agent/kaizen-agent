import { google } from '@ai-sdk/google';
import { Agent } from '@mastra/core/agent';

export const emailFixAgent = new Agent({
  name: 'Email Fix Agent',
  instructions: `You are an email assistant. Improve this email draft.`,
  model: google('gemini-2.5-flash-preview-05-20'),
});

// Example usage function to test the agent
export async function testEmailAgent(input: string): Promise<string> {
  try {
    const result = await emailFixAgent.run(input);
    return result;
  } catch (error) {
    return `Error: ${error.message}`;
  }
}

// Alternative agent with different method names for testing
export const processAgent = new Agent({
  name: 'Process Agent',
  instructions: `You are a data processing assistant.`,
  model: google('gemini-2.5-flash-preview-05-20'),
});

// Agent with process method
export const dataAgent = {
  name: 'Data Agent',
  process: async (input: any) => {
    return `Processed: ${JSON.stringify(input)}`;
  }
};

// Agent with execute method
export const executeAgent = {
  name: 'Execute Agent',
  execute: async (input: any) => {
    return `Executed: ${JSON.stringify(input)}`;
  }
};

// Agent with invoke method
export const invokeAgent = {
  name: 'Invoke Agent',
  invoke: async (input: any) => {
    return `Invoked: ${JSON.stringify(input)}`;
  }
}; 