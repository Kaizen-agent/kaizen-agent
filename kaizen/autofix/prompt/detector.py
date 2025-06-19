import re
import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Set, Pattern

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class FilePatterns:
    """Configuration for file pattern matching."""
    prompt_patterns: List[str] = None
    utils_patterns: List[str] = None
    config_patterns: List[str] = None
    agent_patterns: List[str] = None
    common_words: Set[str] = None
    
    def __post_init__(self):
        """Initialize default patterns if not provided."""
        self.prompt_patterns = self.prompt_patterns or ['prompt', 'instruction', 'guideline', 'template']
        self.utils_patterns = self.utils_patterns or ['utils', 'utility', 'helper', 'common']
        self.config_patterns = self.config_patterns or ['config', 'setting', 'parameter', 'option']
        self.agent_patterns = self.agent_patterns or ['agent', 'assistant', 'bot', 'model']
        self.common_words = self.common_words or {
            'test', 'error', 'failed', 'failure', 'assert', 'check', 'verify', 'validate',
            'should', 'must', 'need', 'have', 'with', 'from', 'that', 'this', 'when'
        }

@dataclass
class PromptDetectionConfig:
    """Configuration for prompt detection."""
    # Scoring weights for different types of patterns
    system_message_weight: float = 0.8
    user_message_weight: float = 0.8
    assistant_message_weight: float = 0.8
    general_prompt_weight: float = 0.6
    chat_array_weight: float = 0.7
    
    # Context scoring weights
    prompt_content_weight: float = 1.0
    input_output_weight: float = 0.5
    structured_pattern_weight: float = 0.8
    nested_pattern_weight: float = 0.9
    multiline_weight: float = 0.3
    formatting_weight: float = 0.2
    numbered_list_weight: float = 0.2
    
    # False positive reduction weights
    test_file_weight: float = 0.5
    config_file_weight: float = 0.5
    utility_file_weight: float = 0.5
    
    # Thresholds
    min_prompt_score: float = 0.6
    min_context_score: float = 0.3
    
    # Cache settings
    cache_size: int = 1000
    cache_ttl: int = 3600  # 1 hour in seconds

class PromptDetector:
    """A class for detecting prompts in code files."""
    
    def __init__(self, config: Optional[PromptDetectionConfig] = None):
        """
        Initialize the prompt detector.
        
        Args:
            config: Optional configuration for prompt detection
        """
        self.config = config or PromptDetectionConfig()
        self._cache = {}
        self._cache_timestamps = {}
        
    def _get_cache_key(self, file_path: str, content: str) -> str:
        """Generate a cache key for the file content."""
        return f"{file_path}:{hash(content)}"
        
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if the cached result is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        return time.time() - self._cache_timestamps[cache_key] < self.config.cache_ttl
        
    def _update_cache(self, cache_key: str, result: Tuple[bool, Optional[str]]):
        """Update the cache with a new result."""
        # Remove oldest entry if cache is full
        if len(self._cache) >= self.config.cache_size:
            oldest_key = min(self._cache_timestamps.items(), key=lambda x: x[1])[0]
            del self._cache[oldest_key]
            del self._cache_timestamps[oldest_key]
            
        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()
        
    def detect_prompt(self, file_path: str, content: str) -> Tuple[bool, Optional[str]]:
        """
        Detect if a file contains prompts by analyzing its content.
        
        Args:
            file_path: Path to the file to analyze
            content: The content of the file
            
        Returns:
            Tuple[bool, Optional[str]]: (contains_prompt, error_message)
        """
        try:
            # Check cache first
            cache_key = self._get_cache_key(file_path, content)
            if self._is_cache_valid(cache_key):
                return self._cache[cache_key]
                
            if not content.strip():
                return False, "File is empty"
                
            # Initialize scoring
            prompt_score = 0.0
            context_score = 0.0
            
            # Check for prompt patterns with context
            content_lower = content.lower()
            
            # System message patterns
            system_patterns = [
                (r'system_message\s*=\s*[\'"](.*?)[\'"]', self.config.system_message_weight),
                (r'system_prompt\s*=\s*[\'"](.*?)[\'"]', self.config.system_message_weight),
                (r'role\s*:\s*[\'"]system[\'"]', self.config.system_message_weight * 0.9)
            ]
            
            # User message patterns
            user_patterns = [
                (r'user_message\s*=\s*[\'"](.*?)[\'"]', self.config.user_message_weight),
                (r'user_prompt\s*=\s*[\'"](.*?)[\'"]', self.config.user_message_weight),
                (r'role\s*:\s*[\'"]user[\'"]', self.config.user_message_weight * 0.9)
            ]
            
            # Assistant message patterns
            assistant_patterns = [
                (r'assistant_message\s*=\s*[\'"](.*?)[\'"]', self.config.assistant_message_weight),
                (r'assistant_prompt\s*=\s*[\'"](.*?)[\'"]', self.config.assistant_message_weight),
                (r'role\s*:\s*[\'"]assistant[\'"]', self.config.assistant_message_weight * 0.9)
            ]
            
            # General prompt patterns
            general_patterns = [
                (r'prompt\s*=\s*[\'"](.*?)[\'"]', self.config.general_prompt_weight),
                (r'instruction\s*=\s*[\'"](.*?)[\'"]', self.config.general_prompt_weight),
                (r'guideline\s*=\s*[\'"](.*?)[\'"]', self.config.general_prompt_weight),
                (r'template\s*=\s*[\'"](.*?)[\'"]', self.config.general_prompt_weight)
            ]
            
            # Chat/message array patterns
            chat_patterns = [
                (r'messages\s*=\s*\[', self.config.chat_array_weight),
                (r'chat\s*=\s*\[', self.config.chat_array_weight),
                (r'conversation\s*=\s*\[', self.config.chat_array_weight)
            ]
            
            # Combine all patterns
            all_patterns = (
                system_patterns + 
                user_patterns + 
                assistant_patterns + 
                general_patterns + 
                chat_patterns
            )
            
            # Check patterns and calculate scores
            for pattern, weight in all_patterns:
                matches = re.finditer(pattern, content_lower)
                for match in matches:
                    # Get context around the match
                    start = max(0, match.start() - 50)
                    end = min(len(content_lower), match.end() + 50)
                    context = content_lower[start:end]
                    
                    # Calculate context score
                    if any(keyword in context for keyword in ['you are', 'your task', 'please', 'should', 'must', 'need to']):
                        context_score += self.config.prompt_content_weight
                    elif any(keyword in context for keyword in ['input', 'output', 'format', 'response', 'result']):
                        context_score += self.config.input_output_weight
                    
                    # Check for structured patterns
                    if re.search(r'\{.*?role.*?content.*?\}', context):
                        context_score += self.config.structured_pattern_weight
                    elif re.search(r'\[.*?\{.*?role.*?content.*?\}.*?\]', context):
                        context_score += self.config.nested_pattern_weight
                    
                    # Check for formatting
                    if '\n' in match.group(0):
                        context_score += self.config.multiline_weight
                    if re.search(r'[#*\-]\s+[A-Z]', context):
                        context_score += self.config.formatting_weight
                    if re.search(r'\d+\.\s+[A-Z]', context):
                        context_score += self.config.numbered_list_weight
                    
                    # Add to prompt score
                    prompt_score += weight
            
            # Check for false positives
            if prompt_score >= self.config.min_prompt_score:
                # Check if the file is likely a test file
                if any(keyword in content_lower for keyword in ['test_', 'test_', 'unittest', 'pytest']):
                    prompt_score *= self.config.test_file_weight
                # Check if the file is likely a configuration file
                if any(keyword in content_lower for keyword in ['config', 'settings', 'options']):
                    prompt_score *= self.config.config_file_weight
                # Check if the file is likely a utility file
                if any(keyword in content_lower for keyword in ['utils', 'helpers', 'common']):
                    prompt_score *= self.config.utility_file_weight
            
            # Final decision
            result = (
                prompt_score >= self.config.min_prompt_score and 
                context_score >= self.config.min_context_score,
                None
            )
            
            # Update cache
            self._update_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting prompts in {file_path}: {str(e)}")
            return False, str(e) 