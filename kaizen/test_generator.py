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

console = Console()

class TestGenerator:
    """Class for generating test cases based on code analysis and test results."""
    
    def __init__(self, project_path: str, results_path: str, output_path: str):
        """
        Initialize the test generator.
        
        Args:
            project_path: Path to the agent project
            results_path: Path to test results directory
            output_path: Path to write generated test files
        """
        self.project_path = Path(project_path)
        self.results_path = Path(results_path)
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
            with open(file_path, 'r') as f:
                content = f.read()
                
            if file_path.suffix == '.py':
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
                            
        except Exception as e:
            console.print(f"[yellow]Warning: Could not analyze {file_path}: {str(e)}[/yellow]")
    
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
        
        # Analyze existing test configuration if provided
        config_analysis = None
        if config_path:
            config_analysis = self.analyze_test_config(config_path)
        
        # Generate test cases using LLM
        test_cases = self._generate_test_cases_with_llm(
            code_analysis,
            test_analysis,
            include_suggestions,
            config_analysis
        )
        
        return test_cases
    
    def _generate_test_cases_with_llm(
        self,
        code_analysis: Dict[str, Any],
        test_analysis: Dict[str, Any],
        include_suggestions: bool,
        config_analysis: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate test cases using OpenAI's API."""
        try:
            # Prepare prompt for LLM
            prompt = self._create_llm_prompt(
                code_analysis,
                test_analysis,
                include_suggestions,
                config_analysis
            )
            
            # Call OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a test generation expert. Generate YAML test cases based on the provided code analysis and test results."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            # Parse response into test cases
            test_cases = self._parse_llm_response(response.choices[0].message.content)
            
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
        prompt = f"""Generate YAML test cases for the following codebase analysis and test results:

Code Analysis:
{json.dumps(code_analysis, indent=2)}

Test Results Analysis:
{json.dumps(test_analysis, indent=2)}
"""

        if config_analysis:
            prompt += f"""
Existing Test Configuration Analysis:
{json.dumps(config_analysis, indent=2)}

Requirements:
1. Generate test cases in YAML format
2. Include test name, agent type, and steps
3. Each step should have input and expected output
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
Requirements:
1. Generate test cases in YAML format
2. Include test name, agent type, and steps
3. Each step should have input and expected output
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
            # Split response into individual YAML documents
            yaml_docs = response.split('---')
            
            for doc in yaml_docs:
                if doc.strip():
                    test_case = yaml.safe_load(doc)
                    if test_case:
                        test_cases.append(test_case)
                        
        except Exception as e:
            console.print(f"[red]Error parsing LLM response: {str(e)}[/red]")
        
        return test_cases
    
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
            
            # Create and checkout new branch
            self._create_branch(branch_name)
            
            # Add and commit test files
            for file in test_files:
                subprocess.run(['git', 'add', file], check=True)
            
            commit_message = f"Add test cases: {pr_title}"
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            # Push branch and create PR
            subprocess.run(['git', 'push', 'origin', branch_name], check=True)
            
            # Create PR using GitHub API
            self._create_github_pr(branch_name, pr_title, pr_body, test_files)
            
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
        
        # Get GitHub token from config
        token = self.config.get('GITHUB_TOKEN')
        if not token:
            raise ValueError("GitHub token not found in configuration")
        
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