#!/usr/bin/env python3
"""
Step-3: Static UI call analysis
Scan UI-related files for LLM calls and extract associated prompts.
"""

import ast
import csv
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple


def load_prompts_catalog(catalog_path: Path) -> List[Dict[str, str]]:
    """Load the filtered prompts catalog CSV file."""
    prompts = []
    
    try:
        with open(catalog_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                prompts.append(row)
    except Exception as e:
        print(f"Error loading catalog: {e}")
        return []
    
    return prompts


def find_ui_related_files(repo_root: Path) -> List[Path]:
    """Find UI-related Python files to scan."""
    ui_files = []
    
    # Primary UI files
    patterns = [
        "app.py",
        "core/**/*.py",
        "*.py"  # Include root level files
    ]
    
    for pattern in patterns:
        ui_files.extend(repo_root.glob(pattern))
    
    # Filter out non-UI files
    excluded_patterns = [
        "tests/",
        "archive/",
        "scripts/",
        "__pycache__/",
        ".git/"
    ]
    
    filtered_files = []
    for file_path in ui_files:
        if file_path.is_file() and file_path.suffix == '.py':
            path_str = str(file_path)
            if not any(excluded in path_str for excluded in excluded_patterns):
                filtered_files.append(file_path)
    
    return filtered_files


class LLMCallExtractor(ast.NodeVisitor):
    """Extract LLM API calls and their prompt arguments."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.llm_calls = []
        self.prompt_symbols = set()
        
    def visit_Call(self, node):
        """Find LLM API calls and extract prompt arguments."""
        if self._is_llm_call(node):
            self._extract_prompt_arguments(node)
        self.generic_visit(node)
    
    def _is_llm_call(self, node) -> bool:
        """Check if this is an LLM API call."""
        try:
            # Check function name patterns
            if isinstance(node.func, ast.Attribute):
                attr_name = node.func.attr
                if attr_name in ['create', 'chat', 'complete']:
                    return True
            
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if any(keyword in func_name.lower() for keyword in ['openai', 'claude', 'chat', 'completion']):
                    return True
            
            # Check for nested attribute calls (e.g., client.chat.completions.create)
            if isinstance(node.func, ast.Attribute):
                current = node.func
                path_parts = []
                
                while isinstance(current, ast.Attribute):
                    path_parts.append(current.attr)
                    current = current.value
                
                if isinstance(current, ast.Name):
                    path_parts.append(current.id)
                
                path_str = '.'.join(reversed(path_parts))
                if any(keyword in path_str.lower() for keyword in ['openai', 'claude', 'chat', 'completion']):
                    return True
                    
        except AttributeError:
            pass
        
        return False
    
    def _extract_prompt_arguments(self, node):
        """Extract prompt arguments from LLM API calls."""
        try:
            # Look for keyword arguments
            for keyword in node.keywords:
                if keyword.arg in ['messages', 'prompt', 'content', 'system']:
                    self._process_argument(keyword.value)
            
            # Look for positional arguments
            for arg in node.args:
                self._process_argument(arg)
                
        except Exception as e:
            print(f"Error extracting arguments: {e}")
    
    def _process_argument(self, arg_node):
        """Process individual argument to extract prompt symbols."""
        if isinstance(arg_node, ast.Name):
            self.prompt_symbols.add(arg_node.id)
        elif isinstance(arg_node, ast.Call):
            # Function call - check if it's a prompt function
            if isinstance(arg_node.func, ast.Name) and 'prompt' in arg_node.func.id.lower():
                self.prompt_symbols.add(arg_node.func.id)
            elif isinstance(arg_node.func, ast.Attribute) and 'prompt' in arg_node.func.attr.lower():
                self.prompt_symbols.add(arg_node.func.attr)
        elif isinstance(arg_node, ast.List):
            # List of messages
            for item in arg_node.elts:
                if isinstance(item, ast.Dict):
                    for key, value in zip(item.keys, item.values):
                        if (isinstance(key, ast.Str) and key.s == 'content') or \
                           (isinstance(key, ast.Constant) and key.value == 'content'):
                            self._process_argument(value)
        elif isinstance(arg_node, ast.Attribute):
            # Attribute access
            if 'prompt' in arg_node.attr.lower():
                self.prompt_symbols.add(arg_node.attr)


def analyze_ui_file_for_llm_calls(file_path: Path) -> Set[str]:
    """Analyze a Python file for LLM calls and return associated prompt symbols."""
    prompt_symbols = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
        
        # Parse AST
        tree = ast.parse(content)
        extractor = LLMCallExtractor(lines)
        extractor.visit(tree)
        
        prompt_symbols.update(extractor.prompt_symbols)
        
        # Also use regex as fallback
        regex_symbols = analyze_file_with_regex(content)
        prompt_symbols.update(regex_symbols)
        
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
    
    return prompt_symbols


def analyze_file_with_regex(content: str) -> Set[str]:
    """Fallback regex analysis for LLM calls."""
    prompt_symbols = set()
    
    # Patterns for LLM API calls
    patterns = [
        r'openai\..*?create\s*\(',
        r'client\.chat\..*?create\s*\(',
        r'claude_api\..*?create\s*\(',
        r'ChatCompletion\.create\s*\(',
        r'\.chat\.completions\.create\s*\('
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        for match in matches:
            # Extract the function call context
            start = match.start()
            end = content.find(')', start)
            if end != -1:
                call_content = content[start:end]
                
                # Look for prompt-related arguments
                prompt_patterns = [
                    r'messages\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*)',
                    r'prompt\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*)',
                    r'content\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*)',
                    r'system\s*=\s*([a-zA-Z_][a-zA-Z0-9_]*)'
                ]
                
                for prompt_pattern in prompt_patterns:
                    prompt_matches = re.finditer(prompt_pattern, call_content)
                    for prompt_match in prompt_matches:
                        symbol = prompt_match.group(1)
                        if 'prompt' in symbol.lower():
                            prompt_symbols.add(symbol)
    
    return prompt_symbols


def filter_prompts_by_ui_usage(prompts: List[Dict[str, str]], ui_files: List[Path]) -> List[Dict[str, str]]:
    """Filter prompts based on UI file analysis."""
    all_ui_symbols = set()
    
    print(f"Analyzing {len(ui_files)} UI files for LLM calls...")
    
    # Analyze all UI files
    for ui_file in ui_files:
        try:
            symbols = analyze_ui_file_for_llm_calls(ui_file)
            all_ui_symbols.update(symbols)
            if symbols:
                print(f"  {ui_file.name}: {len(symbols)} prompt symbols")
        except Exception as e:
            print(f"  Error analyzing {ui_file}: {e}")
    
    print(f"Total UI prompt symbols found: {len(all_ui_symbols)}")
    
    # Filter prompts that match UI symbols
    filtered_prompts = []
    for prompt in prompts:
        symbol = prompt.get('symbol', '')
        
        # Check if symbol matches any UI symbol
        if symbol in all_ui_symbols:
            filtered_prompts.append(prompt)
            continue
        
        # Check if symbol name suggests UI usage
        symbol_lower = symbol.lower()
        if any(ui_symbol.lower() in symbol_lower for ui_symbol in all_ui_symbols):
            filtered_prompts.append(prompt)
            continue
        
        # Check if any UI symbol contains this prompt symbol
        if any(symbol.lower() in ui_symbol.lower() for ui_symbol in all_ui_symbols):
            filtered_prompts.append(prompt)
    
    return filtered_prompts


def save_ui_static_catalog(prompts: List[Dict[str, str]], output_path: Path):
    """Save UI static analysis results to CSV."""
    try:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            if prompts:
                fieldnames = ['filepath', 'line_no', 'symbol', 'preview']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(prompts)
    except Exception as e:
        print(f"Error saving UI static catalog: {e}")


def main():
    """Main static UI analysis logic."""
    repo_root = Path(__file__).parent.parent
    input_path = repo_root / "prompts_catalog_filtered.csv"
    output_path = repo_root / "prompts_catalog_ui_static.csv"
    
    # Load filtered prompts catalog
    print("Loading filtered prompts catalog...")
    prompts = load_prompts_catalog(input_path)
    print(f"Loaded {len(prompts)} filtered prompts")
    
    if not prompts:
        print("❌ No prompts loaded, exiting")
        return False
    
    # Find UI-related files
    print("Finding UI-related files...")
    ui_files = find_ui_related_files(repo_root)
    print(f"Found {len(ui_files)} UI files to analyze")
    
    # Filter prompts by UI usage
    print("Filtering prompts by UI usage...")
    ui_prompts = filter_prompts_by_ui_usage(prompts, ui_files)
    print(f"UI-linked prompts: {len(ui_prompts)}")
    
    # Save results
    print("Saving UI static analysis results...")
    save_ui_static_catalog(ui_prompts, output_path)
    
    # Output result
    print(f"Static detected: {len(ui_prompts)}")
    
    return True


if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)