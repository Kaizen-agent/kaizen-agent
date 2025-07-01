// Example TypeScript file for testing

import { Request, Response } from 'express';

// kaizen:start:simple_function
export function simpleFunction(input: string): string {
    return `Hello, ${input}!`;
}
// kaizen:end:simple_function

// kaizen:start:data_processor
export class DataProcessor {
    private config: any;
    
    constructor(config: any) {
        this.config = config;
    }
    
    async process(input: any): Promise<any> {
        return {
            status: 'success',
            result: `Processed: ${JSON.stringify(input)}`,
            config: this.config,
            timestamp: Date.now()
        };
    }
    
    getConfig(): any {
        return this.config;
    }
}
// kaizen:end:data_processor

export function utilityFunction(data: any[]): any[] {
    return data.map(item => ({ ...item, processed: true }));
}

export const asyncProcessor = async (input: string): Promise<string> => {
    return new Promise(resolve => {
        setTimeout(() => resolve(`Async processed: ${input}`), 100);
    });
};

// Default export for module-level execution
export default function main(input: any): any {
    return {
        message: "Default export function",
        input: input,
        timestamp: Date.now()
    };
} 