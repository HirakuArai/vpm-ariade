#!/usr/bin/env python3
"""
Extract all triple-quoted prompt strings from Python files in the repository
and output them to a CSV catalog.
"""

import ast
import csv
import re
from pathlib import Path
from typing import List, Tuple, Optional


class PromptExtractor(ast.NodeVisitor):
    """AST visitor to extract triple-quoted strings with their context."""
    
    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.prompts: List[Tuple[int, Optional[str], str]] = []
        self.current_function = None
        self.current_class = None
        
    def visit_FunctionDef(self, node):
        """Track current function context."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_AsyncFunctionDef(self, node):
        """Track async function context."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function
        
    def visit_ClassDef(self, node):
        """Track current class context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
        
    def visit_Assign(self, node):
        """Extract variable assignments with triple-quoted strings."""
        if isinstance(node.value, ast.Str):
            # Python < 3.8 compatibility
            string_value = node.value.s
            if self._is_triple_quoted(node.value.lineno, node.value.end_lineno):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.prompts.append((
                            node.value.lineno,
                            target.id,
                            string_value
                        ))
        elif isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            # Python >= 3.8
            string_value = node.value.value
            if self._is_triple_quoted(node.value.lineno, node.value.end_lineno):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.prompts.append((
                            node.value.lineno,
                            target.id,
                            string_value
                        ))
        self.generic_visit(node)
        
    def visit_Expr(self, node):
        """Extract standalone triple-quoted strings (like docstrings)."""
        if isinstance(node.value, ast.Str):
            # Python < 3.8 compatibility
            string_value = node.value.s
            if self._is_triple_quoted(node.value.lineno, node.value.end_lineno):
                # Determine context
                symbol = self._get_current_context()
                self.prompts.append((
                    node.value.lineno,
                    symbol,
                    string_value
                ))
        elif isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            # Python >= 3.8
            string_value = node.value.value
            if self._is_triple_quoted(node.value.lineno, node.value.end_lineno):
                # Determine context
                symbol = self._get_current_context()
                self.prompts.append((
                    node.value.lineno,
                    symbol,
                    string_value
                ))
        self.generic_visit(node)
        
    def _is_triple_quoted(self, start_line: int, end_line: Optional[int]) -> bool:
        """Check if a string is triple-quoted by examining source lines."""
        if start_line <= 0 or start_line > len(self.source_lines):
            return False
            
        line = self.source_lines[start_line - 1]
        # Look for triple quotes
        return '"""' in line or "'''" in line
        
    def _get_current_context(self) -> str:
        """Get the current context (function/class name or 'module')."""
        if self.current_function:
            if self.current_class:
                return f"{self.current_class}.{self.current_function}"
            return self.current_function
        elif self.current_class:
            return self.current_class
        else:
            return "module"


def extract_prompts_from_file(filepath: Path) -> List[Tuple[str, int, str, str]]:
    """Extract all triple-quoted strings from a Python file."""
    results = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
            
        # Parse AST
        tree = ast.parse(content)
        extractor = PromptExtractor(lines)
        extractor.visit(tree)
        
        # Format results
        for line_no, symbol, text in extractor.prompts:
            # Create preview (first 40 chars, single line)
            preview = text.replace('\n', ' ').replace('\r', ' ')[:40]
            if len(text) > 40:
                preview += '...'
                
            results.append((
                str(filepath),
                line_no,
                symbol or 'anonymous',
                preview
            ))
            
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        
    return results


def extract_prompts_with_regex(filepath: Path) -> List[Tuple[str, int, str, str]]:
    """Fallback regex-based extraction for edge cases."""
    results = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Regex patterns for triple-quoted strings
        patterns = [
            r'(\w+)\s*=\s*("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')',
            r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                # Calculate line number
                line_no = content[:match.start()].count('\n') + 1
                
                if len(match.groups()) == 2:
                    # Variable assignment
                    symbol = match.group(1)
                    text = match.group(2).strip('"""').strip("'''")
                else:
                    # Standalone string
                    symbol = 'inline'
                    text = match.group(1).strip('"""').strip("'''")
                    
                # Create preview
                preview = text.replace('\n', ' ').replace('\r', ' ')[:40]
                if len(text) > 40:
                    preview += '...'
                    
                results.append((
                    str(filepath),
                    line_no,
                    symbol,
                    preview
                ))
                
    except Exception as e:
        print(f"Error in regex extraction for {filepath}: {e}")
        
    return results


def main():
    """Main extraction logic."""
    # Get repository root
    repo_root = Path(__file__).parent.parent
    
    # Find all Python files
    py_files = list(repo_root.rglob("*.py"))
    
    # Exclude virtual environments and hidden directories
    py_files = [
        f for f in py_files 
        if not any(part.startswith('.') or part in ['venv', 'env', '__pycache__'] 
                  for part in f.parts)
    ]
    
    # Extract prompts
    all_prompts = []
    
    for py_file in py_files:
        # Try AST-based extraction first
        prompts = extract_prompts_from_file(py_file)
        
        # If no results, try regex-based extraction
        if not prompts:
            prompts = extract_prompts_with_regex(py_file)
            
        all_prompts.extend(prompts)
    
    # Sort by filepath and line number
    all_prompts.sort(key=lambda x: (x[0], x[1]))
    
    # Write to CSV
    output_file = repo_root / "prompts_catalog.csv"
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow(['filepath', 'line_no', 'symbol', 'preview'])
        # Write data
        writer.writerows(all_prompts)
    
    # Print summary
    print(f"Extracted {len(all_prompts)} prompts")
    print(f"Output saved to: {output_file}")
    
    # Self-check
    if len(all_prompts) > 0:
        print("✅ Self-check: OK")
    else:
        print("❌ Self-check: NG - No prompts found")
        

if __name__ == "__main__":
    main()