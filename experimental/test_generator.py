"""
Test generation module for Kaizen Agent.
"""
import os
import json
import yaml
import ast
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import openai
from rich.console import Console
from .config import get_config
import random
import time
import google.generativeai as genai

console = Console()

class TestGenerator:
    """Class for generating test cases based on code analysis and test results."""
    
    def __init__(self, project_path: str, results_path: Optional[str], output_path: str = './test-examples'):
        """
        Initialize the test generator.
        
        Args:
            project_path: Path to the agent project
            results_path: Path to test results directory (optional)
            output_path: Path to write generated test files (default: ./test-examples)
        """
        self.project_path = Path(project_path)
        self.results_path = Path(results_path) if results_path else None
        self.output_path = Path(output_path)
        self.config = get_config()
        
        # Create output directory if it doesn't exist
        self.output_path.mkdir(parents=True, exist_ok=True)
        
    def analyze_codebase(self) -> Dict[str, Any]:
        """
        Analyze the codebase to identify testable components.
        
        Returns:
            Dict containing analysis results
        """
        analysis = {
            'functions': [],
            'classes': [],
            'untested_regions': [],
            'complex_regions': []
        }
        
        # Walk through project directory
        for root, _, files in os.walk(self.project_path):
            for file in files:
                if file.endswith(('.py', '.ts')):
                    file_path = Path(root) / file
                    self._analyze_file(file_path, analysis)
        
        return analysis
    
    def analyze_test_config(self, config_path: str) -> Dict[str, Any]:
        """
        Analyze existing test configuration files.
        
        Args:
            config_path: Path to test configuration file or directory
            
        Returns:
            Dict containing analysis of test configurations
        """
        config_path = Path(config_path)
        analysis = {
            'test_cases': [],
            'coverage': {},
            'patterns': {
                'input_types': set(),
                'expected_outputs': set(),
                'test_scenarios': set()
            }
        }
        
        if config_path.is_file():
            self._analyze_config_file(config_path, analysis)
        elif config_path.is_dir():
            for file in config_path.glob('**/*.yaml'):
                self._analyze_config_file(file, analysis)
        
        # Convert sets to lists for JSON serialization
        analysis['patterns'] = {
            'input_types': list(analysis['patterns']['input_types']),
            'expected_outputs': list(analysis['patterns']['expected_outputs']),
            'test_scenarios': list(analysis['patterns']['test_scenarios'])
        }
        
        return analysis
    
    def _analyze_config_file(self, file_path: Path, analysis: Dict[str, Any]):
        """Analyze a single test configuration file."""
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
                
            if not config:
                return
                
            # Extract test case information
            test_case = {
                'name': config.get('name', 'Unnamed Test'),
                'agent_type': config.get('agent_type', 'unknown'),
                'steps': []
            }
            
            # Analyze steps
            for step in config.get('steps', []):
                step_info = {
                    'name': step.get('name', 'Unnamed Step'),
                    'input_type': type(step.get('input', {})).__name__,
                    'expected_outputs': []
                }
                
                # Extract input patterns
                input_data = step.get('input', {})
                if isinstance(input_data, dict):
                    analysis['patterns']['input_types'].update(input_data.keys())
                
                # Extract expected output patterns
                if 'expected_output_contains' in step:
                    step_info['expected_outputs'].extend(step['expected_output_contains'])
                    analysis['patterns']['expected_outputs'].update(step['expected_output_contains'])
                
                if 'expected_output_exact' in step:
                    step_info['expected_outputs'].append('exact_match')
                    analysis['patterns']['expected_outputs'].add('exact_match')
                
                # Extract test scenarios
                if 'scenario' in step:
                    analysis['patterns']['test_scenarios'].add(step['scenario'])
                
                test_case['steps'].append(step_info)
            
            analysis['test_cases'].append(test_case)
            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not analyze {file_path}: {str(e)}[/yellow]")
    
    def _analyze_file(self, file_path: Path, analysis: Dict[str, Any]):
        """Analyze a single file for testable components."""
        try:
            # Try to read the file with UTF-8 encoding first
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # If UTF-8 fails, try with a different encoding
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                
            if file_path.suffix == '.py':
                try:
                    tree = ast.parse(content)
                    
                    # Find functions and classes
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            analysis['functions'].append({
                                'name': node.name,
                                'file': str(file_path),
                                'line': node.lineno
                            })
                        elif isinstance(node, ast.ClassDef):
                            analysis['classes'].append({
                                'name': node.name,
                                'file': str(file_path),
                                'line': node.lineno
                            })
                            
                    # Check for complex regions (e.g., nested conditionals, loops)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.If, ast.For, ast.While)):
                            complexity = self._calculate_complexity(node)
                            if complexity > 3:  # Threshold for complexity
                                analysis['complex_regions'].append({
                                    'file': str(file_path),
                                    'line': node.lineno,
                                    'complexity': complexity
                                })
                except SyntaxError as e:
                    console.print(f"[yellow]Warning: Syntax error in {file_path}: {str(e)}[/yellow]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Error analyzing Python file {file_path}: {str(e)}[/yellow]")
            elif file_path.suffix == '.ts':
                # Basic TypeScript analysis (can be enhanced)
                if 'function ' in content:
                    analysis['functions'].append({
                        'name': 'TypeScript function',
                        'file': str(file_path),
                        'line': 1
                    })
                if 'class ' in content:
                    analysis['classes'].append({
                        'name': 'TypeScript class',
                        'file': str(file_path),
                        'line': 1
                    })
                            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not read or analyze {file_path}: {str(e)}[/yellow]")
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of an AST node."""
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler)):
                complexity += 1
                
        return complexity
    
    def analyze_test_results(self) -> Dict[str, Any]:
        """
        Analyze existing test results to identify gaps and failures.
        
        Returns:
            Dict containing analysis of test results
        """
        results = {
            'failures': [],
            'gaps': [],
            'coverage': {}
        }
        
        # Skip analysis if no results path provided
        if not self.results_path:
            return results
        
        # Walk through results directory
        for root, _, files in os.walk(self.results_path):
            for file in files:
                if file.endswith(('.json', '.log')):
                    file_path = Path(root) / file
                    self._analyze_result_file(file_path, results)
        
        return results
    
    def _analyze_result_file(self, file_path: Path, results: Dict[str, Any]):
        """Analyze a single test result file."""
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix == '.json':
                    data = json.load(f)
                else:
                    # Parse log file
                    data = self._parse_log_file(f.read())
                
                # Extract failures
                if 'failures' in data:
                    results['failures'].extend(data['failures'])
                
                # Extract coverage information
                if 'coverage' in data:
                    results['coverage'].update(data['coverage'])
                    
        except Exception as e:
            console.print(f"[yellow]Warning: Could not analyze {file_path}: {str(e)}[/yellow]")
    
    def _parse_log_file(self, content: str) -> Dict[str, Any]:
        """Parse a log file into a structured format."""
        # Basic log parsing - can be enhanced based on actual log format
        data = {
            'failures': [],
            'coverage': {}
        }
        
        for line in content.split('\n'):
            if 'FAILED' in line or 'ERROR' in line:
                data['failures'].append({
                    'message': line.strip(),
                    'timestamp': datetime.now().isoformat()
                })
            elif 'coverage' in line.lower():
                # Extract coverage information
                parts = line.split(':')
                if len(parts) >= 2:
                    data['coverage'][parts[0].strip()] = parts[1].strip()
        
        return data
    
    def generate_tests(self, include_suggestions: bool = False, config_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generate test cases based on code analysis and test results.
        
        Args:
            include_suggestions: Whether to include rationale/comments in YAML
            config_path: Optional path to existing test configuration
            
        Returns:
            List of generated test cases
        """
        # Analyze codebase and test results
        code_analysis = self.analyze_codebase()
        test_analysis = self.analyze_test_results()
        
        # Load existing test cases if provided
        existing_test_cases = []
        if config_path:
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    if isinstance(config, dict) and 'steps' in config:
                        # Single test case format
                        existing_test_cases.append(config)
                    elif isinstance(config, list):
                        # Multiple test cases format
                        existing_test_cases.extend(config)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not load existing test cases from {config_path}: {str(e)}[/yellow]")
        
        # Analyze existing test configuration if provided
        config_analysis = None
        if config_path:
            config_analysis = self.analyze_test_config(config_path)
        
        # Generate new test cases using LLM
        new_test_cases = self._generate_test_cases_with_llm(
            code_analysis,
            test_analysis,
            include_suggestions,
            config_analysis
        )
        
        # Combine existing and new test cases
        all_test_cases = existing_test_cases + new_test_cases
        
        if not all_test_cases:
            console.print("[red]No test cases were generated or loaded.[/red]")
            return []
        
        console.print(f"[green]Total test cases: {len(all_test_cases)} ({len(existing_test_cases)} existing + {len(new_test_cases)} new)[/green]")
        return all_test_cases
    
    def _generate_test_cases_with_llm(
        self,
        code_analysis: Dict[str, Any],
        test_analysis: Dict[str, Any],
        include_suggestions: bool,
        config_analysis: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate test cases using Gemini's API."""
        try:
            # Prepare prompt for LLM
            prompt = self._create_llm_prompt(
                code_analysis,
                test_analysis,
                include_suggestions,
                config_analysis
            )
            
            # Initialize Gemini client
            genai.configure(api_key=self.config.get_api_key("google"))
            model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
            
            console.print("[yellow]Generating test cases with Gemini...[/yellow]")
            
            # Call Gemini API
            response = model.generate_content(prompt)
            
            # Get the response content
            content = response.text.strip()
            
            # Debug output
            console.print("[yellow]Raw LLM response:[/yellow]")
            console.print(content)
            
            # Parse response into test cases
            test_cases = self._parse_llm_response(content)
            
            return test_cases
            
        except Exception as e:
            console.print(f"[red]Error generating test cases: {str(e)}[/red]")
            return []
    
    def _create_llm_prompt(
        self,
        code_analysis: Dict[str, Any],
        test_analysis: Dict[str, Any],
        include_suggestions: bool,
        config_analysis: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a prompt for the LLM."""
        prompt = f"""Generate YAML test cases for the following codebase analysis and test results.

Code Analysis:
{json.dumps(code_analysis, indent=2)}

Test Results Analysis:
{json.dumps(test_analysis, indent=2)}
"""

        if config_analysis:
            prompt += f"""
Existing Test Configuration Analysis:
{json.dumps(config_analysis, indent=2)}

IMPORTANT: Return ONLY the YAML test cases, no explanations or additional text.

Requirements:
1. Generate test cases in YAML format with the following structure:
   test_cases:
     - name: "Test Case Name"
       agent_type: "dynamic_region"
       steps:
         - name: "Step Name"
           input:
             file_path: "{os.path.join('test_agent', '{agent_name}', '{agent_name}.py')}"
             region: "{'{agent_name}'}"
             method: "{'{method_name}'}"
             input: "hey, can we meet tomorrow to discuss the project?"
           expected_output_contains:
             - "Dear"
             - "meeting"
             - "project"
             - "schedule"
           validation:
             type: "contains"
             min_length: 100
             max_length: 500

2. Each test case must have:
   - name: A descriptive name
   - agent_type: The type of agent being tested
   - steps: A list of test steps

3. Each step must have:
   - name: A descriptive name
   - input: The input configuration with actual file paths and methods
   - expected_output_contains: List of expected text snippets
   - validation: Validation criteria

4. Focus on untested functions and classes
5. Include edge cases for complex regions
6. Address existing test failures
7. Follow patterns from existing test configuration:
   - Input types: {list(config_analysis['patterns']['input_types'])}
   - Expected output patterns: {list(config_analysis['patterns']['expected_outputs'])}
   - Test scenarios: {list(config_analysis['patterns']['test_scenarios'])}
8. Ensure new tests complement existing ones without duplication
"""
        else:
            prompt += """
IMPORTANT: Return ONLY the YAML test cases, no explanations or additional text.

Requirements:
1. Generate test cases in YAML format with the following structure:
   test_cases:
     - name: "Test Case Name"
       agent_type: "dynamic_region"
       steps:
         - name: "Step Name"
           input:
             file_path: "{os.path.join('test_agent', '{agent_name}', '{agent_name}.py')}"
             region: "{'{agent_name}'}"
             method: "{'{method_name}'}"
             input: "hey, can we meet tomorrow to discuss the project?"
           expected_output_contains:
             - "Dear"
             - "meeting"
             - "project"
             - "schedule"
           validation:
             type: "contains"
             min_length: 100
             max_length: 500

2. Each test case must have:
   - name: A descriptive name
   - agent_type: The type of agent being tested
   - steps: A list of test steps

3. Each step must have:
   - name: A descriptive name
   - input: The input configuration with actual file paths and methods
   - expected_output_contains: List of expected text snippets
   - validation: Validation criteria

4. Focus on untested functions and classes
5. Include edge cases for complex regions
6. Address existing test failures
"""

        if include_suggestions:
            prompt += "\n9. Include comments explaining the rationale for each test case"

        return prompt
    
    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into structured test cases."""
        test_cases = []
        
        try:
            # Clean up the response
            response = response.strip()
            
            # If response starts with a list marker, wrap it in a test_cases object
            if response.startswith('- '):
                response = f"test_cases:\n{response}"
            
            # Try to parse as YAML
            try:
                parsed = yaml.safe_load(response)
                if isinstance(parsed, dict) and 'test_cases' in parsed:
                    test_cases = parsed['test_cases']
                elif isinstance(parsed, list):
                    test_cases = parsed
                else:
                    console.print("[yellow]Warning: Unexpected YAML structure. Expected 'test_cases' list or array of test cases.[/yellow]")
                    console.print(f"Got: {type(parsed)}")
                    return []
            except yaml.YAMLError as e:
                console.print(f"[red]Error parsing YAML: {str(e)}[/red]")
                console.print("Raw response:")
                console.print(response)
                return []
            
            # Validate test cases
            valid_cases = []
            for case in test_cases:
                if not isinstance(case, dict):
                    console.print(f"[yellow]Warning: Skipping invalid test case (not a dictionary): {case}[/yellow]")
                    continue
                    
                if 'name' not in case:
                    console.print("[yellow]Warning: Skipping test case without name[/yellow]")
                    continue
                    
                if 'steps' not in case:
                    console.print(f"[yellow]Warning: Skipping test case '{case['name']}' without steps[/yellow]")
                    continue
                    
                valid_cases.append(case)
            
            return valid_cases
            
        except Exception as e:
            console.print(f"[red]Error parsing LLM response: {str(e)}[/red]")
            console.print("Raw response:")
            console.print(response)
            return []
    
    def save_test_cases(self, test_cases: List[Dict[str, Any]]) -> List[str]:
        """
        Save generated test cases to YAML files.
        
        Args:
            test_cases: List of test cases to save
            
        Returns:
            List of paths to saved test files
        """
        saved_files = []
        
        for i, test_case in enumerate(test_cases):
            # Generate filename based on test name or index
            test_name = test_case.get('name', f'test_{i+1}').lower().replace(' ', '_')
            filename = f"{test_name}.yaml"
            file_path = self.output_path / filename
            
            # Save test case to file
            try:
                with open(file_path, 'w') as f:
                    yaml.dump(test_case, f, default_flow_style=False)
                saved_files.append(str(file_path))
            except Exception as e:
                console.print(f"[red]Error saving test case {filename}: {str(e)}[/red]")
        
        return saved_files
    
    def create_pull_request(self, branch_name: str, test_files: List[str]) -> bool:
        """
        Create a GitHub pull request with the generated test cases.
        
        Args:
            branch_name: Name of the branch to create
            test_files: List of test files to include in PR
            
        Returns:
            bool: Whether PR creation was successful
        """
        try:
            # Check if git is initialized
            if not self._is_git_repo():
                console.print("[red]Error: Not a git repository[/red]")
                return False
            
            # Generate meaningful branch name and PR title
            branch_name, pr_title, pr_body = self._generate_pr_info(test_files)
            
            # Add timestamp and random suffix to make branch name unique
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=4))
            unique_branch_name = f"{branch_name}-{timestamp}-{random_suffix}"
            
            # Create and checkout new branch
            try:
                subprocess.run(['git', 'checkout', '-b', unique_branch_name], check=True)
            except subprocess.CalledProcessError:
                # If branch creation fails, try with a different name
                console.print(f"[yellow]Branch {unique_branch_name} already exists, trying alternative name...[/yellow]")
                unique_branch_name = f"{branch_name}-{timestamp}-{random_suffix}-{int(time.time())}"
                subprocess.run(['git', 'checkout', '-b', unique_branch_name], check=True)
            
            # Add and commit test files
            for file in test_files:
                subprocess.run(['git', 'add', file], check=True)
            
            commit_message = f"Add test cases: {pr_title}"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            # Push branch and create PR
            subprocess.run(['git', 'push', 'origin', unique_branch_name], check=True)
            
            # Create PR using GitHub API
            self._create_github_pr(unique_branch_name, pr_title, pr_body, test_files)
            
            return True
            
        except Exception as e:
            console.print(f"[red]Error creating pull request: {str(e)}[/red]")
            return False
    
    def _generate_pr_info(self, test_files: List[str]) -> Tuple[str, str, str]:
        """
        Generate meaningful branch name, PR title, and body using LLM.
        
        Args:
            test_files: List of test files to include in PR
            
        Returns:
            Tuple of (branch_name, pr_title, pr_body)
        """
        try:
            # Read test files to analyze changes
            test_cases = []
            for file in test_files:
                with open(file, 'r') as f:
                    test_cases.append(yaml.safe_load(f))
            
            # Prepare prompt for LLM
            prompt = f"""Based on the following test cases, generate:
1. A short, descriptive branch name (max 50 chars, use hyphens)
2. A clear PR title (max 100 chars)
3. A detailed PR body explaining the changes

Test Cases:
{json.dumps(test_cases, indent=2)}

Requirements:
- Branch name should reflect the main purpose of the changes
- PR title should be clear and concise
- PR body should explain what was tested and why
- Focus on the most important changes
"""
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a PR generation expert. Generate meaningful branch names and PR descriptions based on test changes."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Extract branch name, title, and body
            lines = content.split('\n')
            branch_name = lines[0].strip()
            pr_title = lines[1].strip()
            pr_body = '\n'.join(lines[2:]).strip()
            
            # Clean up branch name
            branch_name = branch_name.lower()
            branch_name = ''.join(c if c.isalnum() or c == '-' else '-' for c in branch_name)
            branch_name = '-'.join(filter(None, branch_name.split('-')))
            
            # Add timestamp to ensure uniqueness
            timestamp = datetime.now().strftime('%Y%m%d')
            branch_name = f"{branch_name}-{timestamp}"
            
            return branch_name, pr_title, pr_body
            
        except Exception as e:
            console.print(f"[yellow]Warning: Error generating PR info: {str(e)}[/yellow]")
            # Fallback to default values
            timestamp = datetime.now().strftime('%Y%m%d')
            branch_name = f"add-tests-{timestamp}"
            pr_title = "Add auto-generated test cases"
            pr_body = f"""This PR adds auto-generated test cases based on code analysis and existing test results.

Added test files:
{chr(10).join(f'- {file}' for file in test_files)}

These tests were generated to improve test coverage and address existing gaps in testing.
"""
            return branch_name, pr_title, pr_body
    
    def _create_github_pr(self, branch_name: str, pr_title: str, pr_body: str, test_files: List[str]):
        """Create a pull request using GitHub API."""
        import requests
        
        # Get GitHub token from environment variables
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable not set. Please set it in your .env file or environment variables.")
        
        # Get repository information
        repo_url = subprocess.run(
            ['git', 'config', '--get', 'remote.origin.url'],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        # Extract owner and repo from URL
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]
        owner, repo = repo_url.split('/')[-2:]
        
        # Create PR
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        data = {
            'title': pr_title,
            'body': pr_body,
            'head': branch_name,
            'base': 'main'
        }
        
        response = requests.post(
            f'https://api.github.com/repos/{owner}/{repo}/pulls',
            headers=headers,
            json=data
        )
        
        if response.status_code != 201:
            raise Exception(f"Failed to create PR: {response.text}")
    
    def _is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        try:
            subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _create_branch(self, branch_name: str):
        """Create and checkout a new git branch."""
        subprocess.run(['git', 'checkout', '-b', branch_name], check=True)
    
    def _create_branch(self, branch_name: str):
        """Create and checkout a new git branch."""
        subprocess.run(['git', 'checkout', '-b', branch_name], check=True) 