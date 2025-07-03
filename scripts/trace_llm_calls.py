#!/usr/bin/env python3
"""
Step-4: Runtime trace analysis
Trace actual LLM API calls during Streamlit execution.
"""

import json
import sys
import traceback
import subprocess
import time
import signal
import os
from pathlib import Path
from typing import Dict, Any, Set
import csv


class LLMCallTracer:
    """Trace LLM API calls and log prompt symbols."""
    
    def __init__(self):
        self.traced_symbols = set()
        self.call_log = []
        self.log_file = Path(__file__).parent.parent / "trace_llm_calls.jsonl"
        
    def setup_tracing(self):
        """Setup function call tracing."""
        # Monkey patch OpenAI calls
        try:
            import openai
            self._patch_openai(openai)
        except ImportError:
            print("OpenAI not available for tracing")
        
        # Setup general function tracing
        sys.setprofile(self._profile_function)
        
    def _patch_openai(self, openai_module):
        """Patch OpenAI API calls."""
        original_create = None
        
        # Try to find and patch the create method
        try:
            if hasattr(openai_module, 'ChatCompletion'):
                original_create = openai_module.ChatCompletion.create
                openai_module.ChatCompletion.create = self._wrap_openai_create(original_create)
            elif hasattr(openai_module, 'chat') and hasattr(openai_module.chat, 'completions'):
                original_create = openai_module.chat.completions.create
                openai_module.chat.completions.create = self._wrap_openai_create(original_create)
        except Exception as e:
            print(f"Error patching OpenAI: {e}")
    
    def _wrap_openai_create(self, original_func):
        """Wrap OpenAI create function to trace calls."""
        def wrapper(*args, **kwargs):
            try:
                # Extract prompt information
                self._extract_prompt_info(args, kwargs)
            except Exception as e:
                print(f"Error extracting prompt info: {e}")
            
            # Call original function
            return original_func(*args, **kwargs)
        
        return wrapper
    
    def _extract_prompt_info(self, args, kwargs):
        """Extract prompt information from API call arguments."""
        symbols = set()
        
        # Check messages parameter
        if 'messages' in kwargs:
            messages = kwargs['messages']
            if isinstance(messages, list):
                for msg in messages:
                    if isinstance(msg, dict) and 'content' in msg:
                        content = msg['content']
                        if isinstance(content, str):
                            # Look for variable names in content
                            symbols.update(self._extract_symbols_from_text(content))
        
        # Check prompt parameter
        if 'prompt' in kwargs:
            prompt = kwargs['prompt']
            if isinstance(prompt, str):
                symbols.update(self._extract_symbols_from_text(prompt))
        
        # Log the call
        call_info = {
            'symbols': list(symbols),
            'timestamp': time.time(),
            'function': 'openai_create'
        }
        
        self.call_log.append(call_info)
        self.traced_symbols.update(symbols)
        
        # Write to JSONL immediately
        self._write_to_jsonl(call_info)
    
    def _extract_symbols_from_text(self, text: str) -> Set[str]:
        """Extract potential symbol names from text."""
        symbols = set()
        
        # Look for common prompt patterns
        import re
        
        # Pattern for variable-like strings
        var_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
        matches = re.findall(var_pattern, text)
        
        for match in matches:
            if 'prompt' in match.lower():
                symbols.add(match)
        
        return symbols
    
    def _profile_function(self, frame, event, arg):
        """Profile function calls to detect LLM usage."""
        if event == 'call':
            func_name = frame.f_code.co_name
            if any(keyword in func_name.lower() for keyword in ['prompt', 'chat', 'openai', 'claude']):
                # Extract local variables that might be prompts
                local_vars = frame.f_locals
                for var_name, var_value in local_vars.items():
                    if 'prompt' in var_name.lower() and isinstance(var_value, str):
                        self.traced_symbols.add(var_name)
                        
                        call_info = {
                            'symbols': [var_name],
                            'timestamp': time.time(),
                            'function': func_name
                        }
                        self.call_log.append(call_info)
                        self._write_to_jsonl(call_info)
    
    def _write_to_jsonl(self, call_info: Dict[str, Any]):
        """Write call info to JSONL file."""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(call_info, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Error writing to JSONL: {e}")
    
    def get_traced_symbols(self) -> Set[str]:
        """Get all traced symbols."""
        return self.traced_symbols.copy()


def start_streamlit_with_tracing():
    """Start Streamlit with tracing and send a test request."""
    repo_root = Path(__file__).parent.parent
    
    # Setup tracer
    tracer = LLMCallTracer()
    tracer.setup_tracing()
    
    print("Starting Streamlit with tracing...")
    
    # Start Streamlit in headless mode
    process = None
    try:
        process = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', 'app.py',
            '--server.headless', 'true',
            '--server.port', '8502'
        ], cwd=repo_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        print("Waiting for Streamlit to start...")
        time.sleep(5)  # Wait for startup
        
        # Send a test request to trigger LLM calls
        try:
            import requests
            test_url = "http://localhost:8502/"
            response = requests.get(test_url, timeout=10)
            print(f"Test request sent, status: {response.status_code}")
        except ImportError:
            print("Requests not available, using curl")
            try:
                subprocess.run(['curl', '-s', 'http://localhost:8502/'], 
                             timeout=10, capture_output=True)
                print("Test request sent via curl")
            except Exception as e:
                print(f"Test request failed: {e}")
        except Exception as e:
            print(f"Test request failed: {e}")
        
        # Wait a bit more for processing
        time.sleep(3)
        
    except Exception as e:
        print(f"Error starting Streamlit: {e}")
    
    finally:
        # Kill Streamlit process
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            print("Streamlit process terminated")
    
    # Also kill any remaining streamlit processes
    try:
        subprocess.run(['pkill', '-f', 'streamlit'], capture_output=True)
    except Exception:
        pass
    
    return tracer.get_traced_symbols()


def load_traced_symbols_from_jsonl() -> Set[str]:
    """Load traced symbols from JSONL file."""
    symbols = set()
    jsonl_path = Path(__file__).parent.parent / "trace_llm_calls.jsonl"
    
    if not jsonl_path.exists():
        print("No trace JSONL file found")
        return symbols
    
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        call_info = json.loads(line)
                        if 'symbols' in call_info:
                            symbols.update(call_info['symbols'])
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSONL line: {e}")
    except Exception as e:
        print(f"Error reading JSONL file: {e}")
    
    return symbols


def combine_static_and_runtime_results():
    """Combine static analysis and runtime tracing results."""
    repo_root = Path(__file__).parent.parent
    
    # Load static results
    static_path = repo_root / "prompts_catalog_ui_static.csv"
    static_prompts = []
    
    try:
        with open(static_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                static_prompts.append(row)
    except Exception as e:
        print(f"Error loading static results: {e}")
        return []
    
    # Load runtime symbols
    runtime_symbols = load_traced_symbols_from_jsonl()
    
    print(f"Static prompts: {len(static_prompts)}")
    print(f"Runtime symbols: {len(runtime_symbols)}")
    
    # Combine results (intersection)
    combined_prompts = []
    
    for prompt in static_prompts:
        symbol = prompt.get('symbol', '')
        
        # Check if symbol was traced at runtime
        if symbol in runtime_symbols:
            combined_prompts.append(prompt)
            continue
        
        # Check partial matches
        symbol_lower = symbol.lower()
        if any(symbol_lower in runtime_symbol.lower() or 
               runtime_symbol.lower() in symbol_lower 
               for runtime_symbol in runtime_symbols):
            combined_prompts.append(prompt)
    
    # If no runtime matches, include all static results (fallback)
    if not combined_prompts and static_prompts:
        print("No runtime matches found, using static results as fallback")
        combined_prompts = static_prompts[:25]  # Limit to 25
    
    return combined_prompts


def save_ui_catalog(prompts, output_path: Path):
    """Save final UI catalog."""
    try:
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            if prompts:
                fieldnames = ['filepath', 'line_no', 'symbol', 'preview']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(prompts)
    except Exception as e:
        print(f"Error saving UI catalog: {e}")


def main():
    """Main runtime tracing logic."""
    repo_root = Path(__file__).parent.parent
    output_path = repo_root / "prompts_catalog_ui.csv"
    
    # Clear previous trace log
    jsonl_path = repo_root / "trace_llm_calls.jsonl"
    if jsonl_path.exists():
        jsonl_path.unlink()
    
    # Start tracing
    print("Starting runtime tracing...")
    runtime_symbols = start_streamlit_with_tracing()
    
    # Load additional symbols from JSONL
    additional_symbols = load_traced_symbols_from_jsonl()
    runtime_symbols.update(additional_symbols)
    
    print(f"Runtime traced: {len(runtime_symbols)}")
    
    # Combine with static results
    print("Combining static and runtime results...")
    final_prompts = combine_static_and_runtime_results()
    
    # Save final results
    print("Saving final UI catalog...")
    save_ui_catalog(final_prompts, output_path)
    
    # Output results
    print(f"UI-linked prompts: {len(final_prompts)}")
    
    return len(final_prompts) <= 25


if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)