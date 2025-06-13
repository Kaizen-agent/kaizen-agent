"""
Utility module for handling code regions in test files.
"""
from typing import Dict, Any, Optional, Tuple, List
import re
from .logger import TestLogger

# Predefined markers for different languages
MARKERS = {
    'python': {
        'start': '# kaizen:start',
        'end': '# kaizen:end',
        'function_end': '# kaizen:function_end',
        'multi_end': '# kaizen:multi_end'
    },
    'typescript': {
        'start': '// kaizen:start',
        'end': '// kaizen:end',
        'function_end': '// kaizen:function_end',
        'multi_end': '// kaizen:multi_end'
    },
    'javascript': {
        'start': '// kaizen:start',
        'end': '// kaizen:end',
        'function_end': '// kaizen:function_end',
        'multi_end': '// kaizen:multi_end'
    },
    'java': {
        'start': '// kaizen:start',
        'end': '// kaizen:end',
        'function_end': '// kaizen:function_end',
        'multi_end': '// kaizen:multi_end'
    }
}

class CodeRegion:
    def __init__(self, language: str = 'python', logger: Optional[TestLogger] = None):
        self.language = language
        self.markers = MARKERS.get(language, MARKERS['python'])
        self.logger = logger
        self.intermediate_results = {}

    def extract_regions(self, code: str) -> Dict[str, Any]:
        """Extract code regions using predefined markers."""
        if self.logger:
            self.logger.logger.debug(f"Extracting regions for {self.language}")
        
        regions = {}
        active_regions = {}
        
        # First try to find named regions
        named_marker_regex = re.compile(rf"^\s*({re.escape(self.markers['start'])}|{re.escape(self.markers['end'])}|{re.escape(self.markers['function_end'])}|{re.escape(self.markers['multi_end'])}):([\w_\-]+)", re.MULTILINE)
        named_matches = list(named_marker_regex.finditer(code))
        
        if named_matches:
            # Process named regions
            for match in named_matches:
                marker = match.group(1)
                region_name = match.group(2)
                marker_pos = match.start()
                
                if marker == self.markers['start']:
                    active_regions[region_name] = match.end()
                elif marker == self.markers['function_end']:
                    if region_name in active_regions:
                        start_pos = active_regions[region_name]
                        region_code = code[start_pos:marker_pos].strip()
                        self.intermediate_results[region_name] = {
                            'code': region_code,
                            'type': 'function',
                            'position': marker_pos
                        }
                elif marker == self.markers['multi_end']:
                    if region_name in active_regions:
                        start_pos = active_regions[region_name]
                        region_code = code[start_pos:marker_pos].strip()
                        regions[region_name] = {
                            'code': region_code,
                            'intermediate_results': self.intermediate_results.get(region_name, {}),
                            'type': 'multi_function'
                        }
                        del active_regions[region_name]
                elif marker == self.markers['end']:
                    if region_name in active_regions:
                        start_pos = active_regions[region_name]
                        region_code = code[start_pos:marker_pos].strip()
                        regions[region_name] = {
                            'code': region_code,
                            'intermediate_results': self.intermediate_results.get(region_name, {}),
                            'type': 'regular'
                        }
                        del active_regions[region_name]
        else:
            # If no named regions found, look for simple markers
            # More flexible pattern that doesn't require markers to be at start of line
            simple_marker_regex = re.compile(rf"({re.escape(self.markers['start'])}|{re.escape(self.markers['end'])})")
            simple_matches = list(simple_marker_regex.finditer(code))
            
            if len(simple_matches) >= 2:
                # Find the first start marker
                start_match = None
                for match in simple_matches:
                    if match.group(1) == self.markers['start']:
                        start_match = match
                        break
                
                if start_match:
                    # Find the next end marker after the start marker
                    end_match = None
                    for match in simple_matches:
                        if match.group(1) == self.markers['end'] and match.start() > start_match.end():
                            end_match = match
                            break
                    
                    if end_match:
                        start_pos = start_match.end()
                        end_pos = end_match.start()
                        region_code = code[start_pos:end_pos].strip()
                        regions['default'] = {
                            'code': region_code,
                            'type': 'regular'
                        }
        
        if active_regions:
            if self.logger:
                self.logger.logger.warning(f"Unclosed regions: {list(active_regions.keys())}")
        
        if not regions:
            if self.logger:
                self.logger.logger.error(f"No regions found with markers: {self.markers}")
            return {}
        
        if self.logger:
            self.logger.logger.debug(f"Found {len(regions)} regions: {list(regions.keys())}")
        
        return regions

def extract_code_regions(code: str, language: str = 'python', logger: Optional[TestLogger] = None) -> Dict[str, Any]:
    """Extract code regions based on language."""
    region = CodeRegion(language, logger)
    return region.extract_regions(code) 