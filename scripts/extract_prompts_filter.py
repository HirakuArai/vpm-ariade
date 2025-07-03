#!/usr/bin/env python3
"""
Filter prompts catalog to extract only actual LLM prompt candidates.
"""

import ast
import csv
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional


def load_prompts_catalog(catalog_path: Path) -> List[Dict[str, str]]:
    """Load the prompts catalog CSV file."""
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


def filter_by_symbol_name(prompts: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Step 1: Filter by symbol name containing 'prompt'."""
    filtered = []
    
    for prompt in prompts:
        symbol = prompt.get('symbol', '').lower()
        if 'prompt' in symbol:
            filtered.append(prompt)
    
    return filtered


class LLMCallAnalyzer(ast.NodeVisitor):
    """AST visitor to find LLM API calls and their associated prompts."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.llm_calls = []
        self.variable_assignments = {}
        self.prompt_variables = set()
        
    def visit_Call(self, node):
        """Find LLM API calls."""
        # Check for OpenAI API calls
        if self._is_openai_call(node):
            self._extract_prompt_args(node)
        
        # Check for Claude API calls
        if self._is_claude_call(node):
            self._extract_prompt_args(node)
        
        self.generic_visit(node)
    
    def visit_Assign(self, node):
        """Track variable assignments."""
        if isinstance(node.value, ast.Str):
            # Python < 3.8
            string_value = node.value.s
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.variable_assignments[target.id] = string_value
        elif isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            # Python >= 3.8
            string_value = node.value.value
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.variable_assignments[target.id] = string_value
        
        self.generic_visit(node)
    
    def _is_openai_call(self, node) -> bool:
        """Check if this is an OpenAI API call."""
        try:
            # openai.ChatCompletion.create
            if (isinstance(node.func, ast.Attribute) and 
                isinstance(node.func.value, ast.Attribute) and
                isinstance(node.func.value.value, ast.Name) and
                node.func.value.value.id == 'openai' and
                node.func.value.attr == 'ChatCompletion' and
                node.func.attr == 'create'):
                return True
            
            # client.chat.completions.create
            if (isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Attribute) and
                isinstance(node.func.value.value, ast.Attribute) and
                node.func.value.value.attr == 'chat' and
                node.func.value.attr == 'completions' and
                node.func.attr == 'create'):
                return True
            
            # Direct function calls that might be OpenAI wrappers
            if (isinstance(node.func, ast.Name) and
                any(keyword in node.func.id.lower() for keyword in ['openai', 'chat', 'completion'])):
                return True
                
        except AttributeError:
            pass
        
        return False
    
    def _is_claude_call(self, node) -> bool:
        """Check if this is a Claude API call."""
        try:
            # claude_api.Chat or similar
            if (isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Name) and
                'claude' in node.func.value.id.lower()):
                return True
            
            # Direct function calls that might be Claude wrappers
            if (isinstance(node.func, ast.Name) and
                'claude' in node.func.id.lower()):
                return True
                
        except AttributeError:
            pass
        
        return False
    
    def _extract_prompt_args(self, node):
        """Extract prompt arguments from LLM API calls."""
        try:
            # Look for 'messages' keyword argument
            for keyword in node.keywords:
                if keyword.arg == 'messages':
                    self._process_messages_arg(keyword.value)
                elif keyword.arg in ['prompt', 'content', 'system', 'user']:
                    self._process_prompt_arg(keyword.value)
            
            # Look for positional arguments that might be prompts
            for arg in node.args:
                if isinstance(arg, ast.Name):
                    self.prompt_variables.add(arg.id)
                elif isinstance(arg, ast.Str):
                    # Direct string argument
                    pass
                elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    # Direct string constant
                    pass
                    
        except Exception as e:
            print(f"Error extracting prompt args: {e}")
    
    def _process_messages_arg(self, arg_node):
        """Process 'messages' argument to find prompt content."""
        if isinstance(arg_node, ast.List):
            for item in arg_node.elts:
                if isinstance(item, ast.Dict):
                    for key, value in zip(item.keys, item.values):
                        if (isinstance(key, ast.Str) and key.s == 'content') or \
                           (isinstance(key, ast.Constant) and key.value == 'content'):
                            self._process_prompt_arg(value)
        elif isinstance(arg_node, ast.Name):
            self.prompt_variables.add(arg_node.id)
    
    def _process_prompt_arg(self, arg_node):
        """Process individual prompt argument."""
        if isinstance(arg_node, ast.Name):
            self.prompt_variables.add(arg_node.id)
        elif isinstance(arg_node, ast.Str):
            # Direct string - we'll match this by content
            pass
        elif isinstance(arg_node, ast.Constant) and isinstance(arg_node.value, str):
            # Direct string constant
            pass


def analyze_llm_calls_in_file(filepath: Path) -> Set[str]:
    """Analyze a Python file for LLM calls and return associated prompt variables."""
    prompt_variables = set()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
        
        # Parse AST
        tree = ast.parse(content)
        analyzer = LLMCallAnalyzer(lines)
        analyzer.visit(tree)
        
        prompt_variables.update(analyzer.prompt_variables)
        
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
    
    return prompt_variables


def filter_by_llm_usage(prompts: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Step 2: Filter by actual LLM usage through AST analysis."""
    filtered = []
    
    # Group prompts by file
    file_groups = {}
    for prompt in prompts:
        filepath = prompt['filepath']
        if filepath not in file_groups:
            file_groups[filepath] = []
        file_groups[filepath].append(prompt)
    
    # Analyze each file for LLM calls
    for filepath, file_prompts in file_groups.items():
        try:
            prompt_variables = analyze_llm_calls_in_file(Path(filepath))
            
            # If we found LLM calls, include relevant prompts
            if prompt_variables:
                for prompt in file_prompts:
                    symbol = prompt.get('symbol', '')
                    # Check if this prompt's symbol matches any LLM call variables
                    if symbol in prompt_variables:
                        filtered.append(prompt)
                        continue
                    
                    # Also include if symbol name suggests it's a prompt
                    symbol_lower = symbol.lower()
                    if any(keyword in symbol_lower for keyword in ['prompt', 'message', 'system', 'user']):
                        filtered.append(prompt)
            
            # If no LLM calls found but file has prompt-like symbols, include them
            else:
                for prompt in file_prompts:
                    symbol_lower = prompt.get('symbol', '').lower()
                    if any(keyword in symbol_lower for keyword in ['prompt', 'message', 'system', 'user', 'template']):
                        filtered.append(prompt)
                        
        except Exception as e:
            print(f"Error processing file {filepath}: {e}")
            # On error, include all prompts from this file
            filtered.extend(file_prompts)
    
    return filtered


def deduplicate_by_preview(prompts: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Step 3: Deduplicate by SHA-1 hash of preview content."""
    seen_hashes = set()
    filtered = []
    
    for prompt in prompts:
        preview = prompt.get('preview', '')
        # Create SHA-1 hash of preview content
        hash_obj = hashlib.sha1(preview.encode('utf-8'))
        preview_hash = hash_obj.hexdigest()
        
        if preview_hash not in seen_hashes:
            seen_hashes.add(preview_hash)
            filtered.append(prompt)
    
    return filtered


def save_filtered_catalog(prompts: List[Dict[str, str]], output_path: Path):
    """Step 4: Save filtered catalog to CSV."""
    try:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            if prompts:
                fieldnames = ['filepath', 'line_no', 'symbol', 'preview']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(prompts)
    except Exception as e:
        print(f"Error saving filtered catalog: {e}")


def main():
    """Main filtering logic."""
    repo_root = Path(__file__).parent.parent
    input_path = repo_root / "prompts_catalog.csv"
    output_path = repo_root / "prompts_catalog_filtered.csv"
    
    print("Loading prompts catalog...")
    prompts = load_prompts_catalog(input_path)
    print(f"Loaded {len(prompts)} total prompts")
    
    # Step 1: Filter by symbol name containing 'prompt'
    print("Step 1: Filtering by symbol name containing 'prompt'...")
    step1_prompts = filter_by_symbol_name(prompts)
    print(f"After step 1: {len(step1_prompts)} prompts")
    
    # Step 2: Filter by LLM usage analysis
    print("Step 2: Analyzing LLM usage...")
    step2_prompts = filter_by_llm_usage(step1_prompts)
    print(f"After step 2: {len(step2_prompts)} prompts")
    
    # Step 3: Deduplicate by preview hash
    print("Step 3: Deduplicating by preview content...")
    step3_prompts = deduplicate_by_preview(step2_prompts)
    print(f"After step 3: {len(step3_prompts)} prompts")
    
    # Step 4: Save filtered catalog
    print("Step 4: Saving filtered catalog...")
    save_filtered_catalog(step3_prompts, output_path)
    print(f"Filtered catalog saved to: {output_path}")
    
    # Output final count
    print(f"\n✅ 抽出件数: {len(step3_prompts)}")
    
    # Self-check
    if len(step3_prompts) >= 120:
        print("❌ Self-check: NG - 取得行が120を超えました")
        return False
    else:
        print("✅ Self-check: OK - 行数制限内")
        return True


if __name__ == "__main__":
    main()