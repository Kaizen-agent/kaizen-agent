"""Enhanced TypeScript execution script generation with automatic Mastra agent detection."""

import json
import os
from pathlib import Path
from typing import List, Optional, Any
import logging

logger = logging.getLogger(__name__)

def create_enhanced_typescript_execution_script(
    file_path: str, 
    method_name: Optional[str], 
    input_data: List[Any],
    workspace_root: Path,
    is_mastra: bool = False
) -> str:
    """Create an enhanced TypeScript execution script with automatic Mastra agent detection.
    
    Args:
        file_path: Path to the TypeScript file to execute
        method_name: Optional method name to call
        input_data: Input data to pass to the method
        workspace_root: Root directory of the workspace
        is_mastra: Whether this is a Mastra agent (enables optimizations)
        
    Returns:
        TypeScript execution script as a string
    """
    # Convert to absolute path and then to relative path for import
    abs_path = os.path.abspath(file_path)
    rel_path = os.path.relpath(abs_path, str(workspace_root))
    rel_path = rel_path.replace('\\', '/')
    
    # Ensure the import path starts with ./ for relative imports
    if not rel_path.startswith('./') and not rel_path.startswith('../'):
        rel_path = f"./{rel_path}"
    
    # Convert input data to JSON string
    input_json = json.dumps(input_data)
    
    # Add Mastra-specific optimizations
    mastra_optimizations = ""
    if is_mastra:
        mastra_optimizations = """
        // Mastra-specific optimizations
        process.env.NODE_ENV = 'production';  // Disable development features
        process.env.TS_NODE_CACHE = 'true';   // Enable TypeScript caching
        process.env.TS_NODE_COMPILER_OPTIONS = JSON.stringify({
            "module": "commonjs",
            "target": "es2020", 
            "esModuleInterop": true,
            "skipLibCheck": true,  // Skip library type checking for speed
            "noEmitOnError": false // Continue even with type errors
        });
"""
    
    # Create the execution script with enhanced agent detection and execution
    script = f"""
// Enhanced TypeScript execution script with automatic Mastra agent detection
{mastra_optimizations}

// Load environment variables from .env file
import * as fs from 'fs';
import * as path from 'path';

function loadEnvFile(envPath: string): void {{
    try {{
        if (fs.existsSync(envPath)) {{
            const envContent = fs.readFileSync(envPath, 'utf8');
            const lines = envContent.split('\\n');
            
            for (const line of lines) {{
                const trimmedLine = line.trim();
                if (trimmedLine && !trimmedLine.startsWith('#')) {{
                    const equalIndex = trimmedLine.indexOf('=');
                    if (equalIndex > 0) {{
                        const key = trimmedLine.substring(0, equalIndex).trim();
                        const value = trimmedLine.substring(equalIndex + 1).trim();
                        // Remove quotes if present
                        const cleanValue = value.replace(/^["']|["']$/g, '');
                        process.env[key] = cleanValue;
                        console.error(`DEBUG: Loaded env var: ${{key}}`);
                    }}
                }}
            }}
            console.error(`DEBUG: Loaded environment variables from: ${{envPath}}`);
        }}
    }} catch (error) {{
        console.error(`DEBUG: Error loading .env file: ${{error}}`);
    }}
}}

// Load environment variables from common .env file locations
const possibleEnvPaths = [
    '.env',
    '.env.local', 
    '.env.test',
    path.join(process.cwd(), '.env'),
    path.join(process.cwd(), '.env.local'),
    path.join(process.cwd(), '.env.test')
];

for (const envPath of possibleEnvPaths) {{
    loadEnvFile(envPath);
}}

// Utility function to collect streaming responses
async function collectStreamingResponse(response: any): Promise<string> {{
    if (response && typeof response === 'object') {{
        // Check if it's an async iterator (streaming response)
        if (response[Symbol.asyncIterator]) {{
            console.error('DEBUG: Detected streaming response, collecting chunks...');
            let fullText = '';
            try {{
                for await (const chunk of response) {{
                    if (chunk && typeof chunk === 'object') {{
                        // Handle different chunk formats
                        if (chunk.textDelta) {{
                            fullText += chunk.textDelta;
                        }} else if (chunk.text) {{
                            fullText += chunk.text;
                        }} else if (chunk.content) {{
                            fullText += chunk.content;
                        }} else if (typeof chunk === 'string') {{
                            fullText += chunk;
                        }} else {{
                            // Try to stringify the chunk
                            fullText += JSON.stringify(chunk);
                        }}
                    }} else if (typeof chunk === 'string') {{
                        fullText += chunk;
                    }}
                }}
                console.error('DEBUG: Collected streaming response:', fullText.length, 'characters');
                return fullText;
            }} catch (error) {{
                console.error('DEBUG: Error collecting streaming response:', error);
                return fullText || 'Error collecting streaming response';
            }}
        }}
    }}
    return response;
}}

// Enhanced agent detection function
function isMastraAgent(obj: any): boolean {{
    if (!obj || typeof obj !== 'object') return false;
    
    // Check for Mastra agent properties
    const hasModel = obj.model && typeof obj.model === 'object';
    const hasInstructions = obj.instructions && typeof obj.instructions === 'string';
    const hasName = obj.name && typeof obj.name === 'string';
    const hasComponent = obj.component && typeof obj.component === 'object';
    
    // Check for AI SDK patterns
    const hasGenerate = typeof obj.generate === 'function';
    const hasGenerateText = typeof obj.generateText === 'function';
    const hasText = typeof obj.text === 'function';
    
    // Check for common agent patterns
    const hasRun = typeof obj.run === 'function';
    const hasProcess = typeof obj.process === 'function';
    const hasExecute = typeof obj.execute === 'function';
    const hasInvoke = typeof obj.invoke === 'function';
    
    return hasModel || hasInstructions || hasName || hasComponent || 
           hasGenerate || hasGenerateText || hasText || 
           hasRun || hasProcess || hasExecute || hasInvoke;
}}

// Intelligent agent executor that tries multiple execution strategies
async function executeAgent(agent: any, input: any): Promise<any> {{
    console.error('DEBUG: Executing agent with input:', typeof input, input);
    console.error('DEBUG: Agent type:', typeof agent);
    console.error('DEBUG: Agent keys:', Object.keys(agent || {{}}));
    
    // Normalize input - handle both single values and arrays
    const normalizedInput = Array.isArray(input) ? input : [input];
    const firstInput = normalizedInput[0];
    
    // Strategy 1: Direct function calls (if agent is callable)
    if (typeof agent === 'function') {{
        console.error('DEBUG: Trying agent as function');
        const result = await agent(...normalizedInput);
        return await collectStreamingResponse(result);
    }}
    
    // Strategy 2: Common agent method names
    const commonMethods = ['run', 'process', 'execute', 'invoke', 'call'];
    for (const method of commonMethods) {{
        if (typeof agent[method] === 'function') {{
            console.error(`DEBUG: Trying agent.${{method}}()`);
            try {{
                const result = await agent[method](...normalizedInput);
                return await collectStreamingResponse(result);
            }} catch (error) {{
                console.error(`DEBUG: agent.${{method}}() failed:`, error.message);
            }}
        }}
    }}
    
    // Strategy 3: Mastra-specific patterns
    if (isMastraAgent(agent)) {{
        console.error('DEBUG: Detected Mastra agent, trying specialized patterns');
        
        // Strategy 3a: agent.generate(input)
        if (typeof agent.generate === 'function') {{
            console.error('DEBUG: Trying agent.generate()');
            try {{
                const result = await agent.generate(firstInput);
                return await collectStreamingResponse(result);
            }} catch (error) {{
                console.error('DEBUG: agent.generate() failed:', error.message);
            }}
        }}
        
        // Strategy 3b: agent.generateText(input)
        if (typeof agent.generateText === 'function') {{
            console.error('DEBUG: Trying agent.generateText()');
            try {{
                const result = await agent.generateText(firstInput);
                return await collectStreamingResponse(result);
            }} catch (error) {{
                console.error('DEBUG: agent.generateText() failed:', error.message);
            }}
        }}
        
                        // Strategy 3c: agent.text({{ messages: [{{ role: 'user', content: input }}] }})
                if (typeof agent.text === 'function') {{
                    console.error('DEBUG: Trying agent.text() with messages format');
                    try {{
                        const result = await agent.text({{
                            messages: [{{ role: 'user', content: firstInput }}]
                        }});
                        return await collectStreamingResponse(result);
                    }} catch (error) {{
                        console.error('DEBUG: agent.text() failed:', error.message);
                    }}
                }}
        
        // Strategy 3d: Direct model usage with instructions
        if (agent.model && typeof agent.model.generateText === 'function' && agent.instructions) {{
            console.error('DEBUG: Trying direct model usage with instructions');
            try {{
                const combinedPrompt = `${{agent.instructions}}\\n\\nInput: ${{firstInput}}`;
                const result = await agent.model.generateText({{ prompt: combinedPrompt }});
                return await collectStreamingResponse(result);
            }} catch (error) {{
                console.error('DEBUG: Direct model usage failed:', error.message);
            }}
        }}
        
        // Strategy 3e: agent.model.doGenerate() for newer AI SDK patterns
        if (agent.model && typeof agent.model.doGenerate === 'function') {{
            console.error('DEBUG: Trying agent.model.doGenerate()');
            try {{
                const result = await agent.model.doGenerate({{ prompt: firstInput }});
                return await collectStreamingResponse(result);
            }} catch (error) {{
                console.error('DEBUG: agent.model.doGenerate() failed:', error.message);
            }}
        }}
        
        // Strategy 3f: Component-based agents
        if (agent.component && typeof agent.component === 'object') {{
            console.error('DEBUG: Trying component-based execution');
            const component = agent.component;
            console.error('DEBUG: Component keys:', Object.keys(component));
            
            // Try component methods
            const componentMethods = ['generate', 'run', 'process', 'execute'];
            for (const method of componentMethods) {{
                if (typeof component[method] === 'function') {{
                    console.error(`DEBUG: Trying component.${{method}}()`);
                    try {{
                        const result = await component[method](firstInput);
                        return await collectStreamingResponse(result);
                    }} catch (error) {{
                        console.error(`DEBUG: component.${{method}}() failed:`, error.message);
                    }}
                }}
            }}
        }}
        
        // Strategy 3g: Try model directly if it has generateText
        if (agent.model && typeof agent.model.generateText === 'function') {{
            console.error('DEBUG: Trying agent.model.generateText() directly');
            try {{
                const result = await agent.model.generateText({{ prompt: firstInput }});
                return await collectStreamingResponse(result);
            }} catch (error) {{
                console.error('DEBUG: agent.model.generateText() failed:', error.message);
            }}
        }}
        
        // Strategy 3h: Try model with different parameter formats
        if (agent.model && typeof agent.model.generateText === 'function') {{
            console.error('DEBUG: Trying agent.model.generateText() with different formats');
            const formats = [
                firstInput,
                {{ text: firstInput }},
                {{ prompt: firstInput }},
                {{ input: firstInput }}
            ];
            
            for (const format of formats) {{
                try {{
                    const result = await agent.model.generateText(format);
                    return await collectStreamingResponse(result);
                }} catch (error) {{
                    console.error('DEBUG: Format failed:', format, error.message);
                }}
            }}
        }}
    }}
    
    // Strategy 4: Class constructor pattern (new Agent())
    if (agent.prototype && typeof agent === 'function') {{
        console.error('DEBUG: Trying class constructor pattern');
        try {{
            const instance = new agent();
            return await executeAgent(instance, input);
        }} catch (error) {{
            console.error('DEBUG: Class constructor failed:', error.message);
        }}
    }}
    
    // Strategy 5: Last resort - try to call the object directly
    if (typeof agent === 'object' && agent !== null) {{
        console.error('DEBUG: Trying to call object directly');
        try {{
            const result = await agent(...normalizedInput);
            return await collectStreamingResponse(result);
        }} catch (error) {{
            console.error('DEBUG: Direct object call failed:', error.message);
        }}
    }}
    
    throw new Error('No suitable execution method found for agent. Available properties: ' + Object.keys(agent || {{}}).join(', '));
}}

(async () => {{
    try {{
        // Load environment variables before importing the module
        console.error('DEBUG: Loading environment variables...');
        const possibleEnvPaths = [
            '.env',
            '.env.local', 
            '.env.test',
            path.join(process.cwd(), '.env'),
            path.join(process.cwd(), '.env.local'),
            path.join(process.cwd(), '.env.test')
        ];

        for (const envPath of possibleEnvPaths) {{
            loadEnvFile(envPath);
        }}

        // Check if critical environment variables are loaded
        const criticalVars = ['GOOGLE_API_KEY', 'GOOGLE_GENERATIVE_AI_API_KEY'];
        for (const varName of criticalVars) {{
            if (process.env[varName]) {{
                console.error(`DEBUG: Found ${{varName}} in environment`);
            }} else {{
                console.error(`DEBUG: Missing ${{varName}} in environment`);
            }}
        }}

        // Set up Google API key fallbacks
        if (process.env.GOOGLE_API_KEY && !process.env.GOOGLE_GENERATIVE_AI_API_KEY) {{
            process.env.GOOGLE_GENERATIVE_AI_API_KEY = process.env.GOOGLE_API_KEY;
            console.error('DEBUG: Set GOOGLE_GENERATIVE_AI_API_KEY from GOOGLE_API_KEY');
        }}
        if (process.env.GOOGLE_GENERATIVE_AI_API_KEY && !process.env.GOOGLE_API_KEY) {{
            process.env.GOOGLE_API_KEY = process.env.GOOGLE_GENERATIVE_AI_API_KEY;
            console.error('DEBUG: Set GOOGLE_API_KEY from GOOGLE_GENERATIVE_AI_API_KEY');
        }}

        // Final check for required environment variables
        if (!process.env.GOOGLE_API_KEY && !process.env.GOOGLE_GENERATIVE_AI_API_KEY) {{
            console.error('DEBUG: WARNING - No Google API key found in environment');
            console.error('DEBUG: Available environment variables:', Object.keys(process.env).filter(key => key.includes('GOOGLE')));
        }} else {{
            console.error('DEBUG: Google API key is available for use');
        }}

        // Dynamic import of the target module with error handling
        let targetModule;
        try {{
            targetModule = await import('{rel_path}');
        }} catch (importError) {{
            // If dynamic import fails, try require (for CommonJS modules)
            try {{
                targetModule = require('{rel_path}');
            }} catch (requireError) {{
                throw new Error(`Failed to import module: ${{importError.message}} | ${{requireError.message}}`);
            }}
        }}
        
        // Input data
        const inputData = {input_json};
        
        // Execute based on the module structure
        let result = null;
        
        // If method_name is specified, try to call it
        if ('{method_name}' && typeof targetModule['{method_name}'] === 'function') {{
            console.error('DEBUG: Calling specified method:', '{method_name}');
            result = await targetModule['{method_name}'](...inputData);
        }}
        // If the module itself is a function, call it
        else if (typeof targetModule === 'function') {{
            console.error('DEBUG: Calling module as function');
            result = await targetModule(...inputData);
        }}
        // If the module has a default export that's a function
        else if (targetModule.default && typeof targetModule.default === 'function') {{
            console.error('DEBUG: Calling default export as function');
            result = await targetModule.default(...inputData);
        }}
        // If the module has a main function
        else if (targetModule.main && typeof targetModule.main === 'function') {{
            console.error('DEBUG: Calling main function');
            result = await targetModule.main(...inputData);
        }}
        // Handle modern agent frameworks (like Mastra) that export agent instances
        else if (targetModule.default && typeof targetModule.default === 'object') {{
            console.error('DEBUG: Trying default export as agent');
            result = await executeAgent(targetModule.default, inputData);
        }}
        // Handle named exports for agent instances
        else {{
            // Look for any exported object that might be an agent
            const exportedNames = Object.keys(targetModule);
            let agentFound = false;
            
            // Debug: Log all exports and their types
            console.error('DEBUG: Available exports:', exportedNames);
            for (const name of exportedNames) {{
                const exported = targetModule[name];
                console.error(`DEBUG: ${{name}} type:`, typeof exported);
                if (typeof exported === 'object' && exported !== null) {{
                    console.error(`DEBUG: ${{name}} keys:`, Object.keys(exported));
                    console.error(`DEBUG: ${{name}} methods:`, Object.getOwnPropertyNames(exported).filter(key => typeof exported[key] === 'function'));
                }}
            }}
            
            for (const name of exportedNames) {{
                const exported = targetModule[name];
                
                // Check if it's a function (direct callable)
                if (typeof exported === 'function') {{
                    console.error(`DEBUG: Trying to call ${{name}} as function`);
                    result = await exported(...inputData);
                    agentFound = true;
                    console.error(`DEBUG: Called function ${{name}}`);
                    break;
                }}
                
                // Check if it's an object that might be an agent
                if (typeof exported === 'object' && exported !== null) {{
                    console.error(`DEBUG: Trying ${{name}} as potential agent`);
                    try {{
                        result = await executeAgent(exported, inputData);
                        agentFound = true;
                        console.error(`DEBUG: Successfully executed agent ${{name}}`);
                        break;
                    }} catch (error) {{
                        console.error(`DEBUG: ${{name}} execution failed:`, error.message);
                        // Continue to next export
                    }}
                }}
            }}
            
            if (!agentFound) {{
                throw new Error('No callable function or agent instance found in module. Available exports: ' + exportedNames.join(', '));
            }}
        }}
        
        // Output the result
        console.log(JSON.stringify({{
            result: result,
            tracked_values: {{}}
        }}));
        
    }} catch (error) {{
        console.error(JSON.stringify({{
            error: error.message,
            tracked_values: {{}}
        }}));
        process.exit(1);
    }}
}})();
"""
    return script

 