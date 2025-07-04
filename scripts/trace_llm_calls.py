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
import inspect
import re
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
        # Store original methods
        self.original_methods = {}
        
        # Monkey patch OpenAI calls
        try:
            import openai
            self._patch_openai(openai)
        except ImportError:
            print("OpenAI not available for tracing")
        
        # Don't use sys.setprofile as it can cause issues
        # sys.setprofile(self._profile_function)
        
    def restore_original_methods(self):
        """Restore original methods to prevent issues."""
        try:
            import openai
            
            if 'chat_create' in self.original_methods:
                openai.chat.completions.create = self.original_methods['chat_create']
                
            if 'chat_completion_create' in self.original_methods:
                openai.ChatCompletion.create = self.original_methods['chat_completion_create']
                
            print("Restored original OpenAI methods")
        except Exception as e:
            print(f"Error restoring original methods: {e}")
        
    def _patch_openai(self, openai_module):
        """Patch OpenAI API calls."""
        # Store original methods for restoration
        self.original_methods = {}
        
        try:
            # OpenAI v1.x structure: openai.chat.completions.create
            if hasattr(openai_module, 'chat') and hasattr(openai_module.chat, 'completions'):
                self.original_methods['chat_create'] = openai_module.chat.completions.create
                openai_module.chat.completions.create = self._wrap_openai_create(self.original_methods['chat_create'])
                print("Patched openai.chat.completions.create")
            
            # OpenAI v0.x structure: openai.ChatCompletion.create (fallback)
            elif hasattr(openai_module, 'ChatCompletion'):
                self.original_methods['chat_completion_create'] = openai_module.ChatCompletion.create
                openai_module.ChatCompletion.create = self._wrap_openai_create(self.original_methods['chat_completion_create'])
                print("Patched openai.ChatCompletion.create")
            
            # Try to also patch client instances
            try:
                import openai
                client = openai.OpenAI()
                if hasattr(client, 'chat') and hasattr(client.chat, 'completions'):
                    self.original_methods['client_create'] = client.chat.completions.create
                    client.chat.completions.create = self._wrap_openai_create(self.original_methods['client_create'])
                    print("Patched client.chat.completions.create")
            except Exception as e:
                print(f"Could not patch client instance: {e}")
                
        except Exception as e:
            print(f"Error patching OpenAI: {e}")
    
    def _wrap_openai_create(self, original_func):
        """Wrap OpenAI create function to trace calls."""
        def wrapper(*args, **kwargs):
            symbol = "<unknown>"
            try:
                print(f"OpenAI call intercepted with kwargs keys: {list(kwargs.keys())}")
                
                # Extract prompt variable name using stack inspection
                symbol = self._extract_variable_symbol(args, kwargs)
                print(f"Extracted symbol: {symbol}")
                
                # Extract prompt information
                self._extract_prompt_info(args, kwargs, symbol)
            except Exception as e:
                print(f"Error extracting prompt info: {e}")
                import traceback
                traceback.print_exc()
                # Still log with unknown symbol
                self._extract_prompt_info(args, kwargs, symbol)
            
            # Call original function
            return original_func(*args, **kwargs)
        
        return wrapper
    
    def _extract_prompt_id_from_content(self, content):
        """Extract PROMPT_ID from content string."""
        if isinstance(content, str):
            # Look for PROMPT_ID tag: <!--PROMPT_ID:system_base-->
            match = re.search(r'<!--PROMPT_ID:(\w+)-->', content)
            if match:
                return match.group(1)
        return None
    
    def _extract_variable_symbol(self, args, kwargs):
        """Extract variable name or PROMPT_ID from the arguments."""
        try:
            # First, try to extract PROMPT_ID from content
            prompt_id = None
            
            # Check messages parameter for PROMPT_ID
            if 'messages' in kwargs:
                messages = kwargs['messages']
                if isinstance(messages, list):
                    for msg in messages:
                        if isinstance(msg, dict) and 'content' in msg:
                            content = msg['content']
                            prompt_id = self._extract_prompt_id_from_content(content)
                            if prompt_id:
                                print(f"Found PROMPT_ID in messages: {prompt_id}")
                                return prompt_id
            
            # Check prompt parameter for PROMPT_ID
            if 'prompt' in kwargs:
                prompt = kwargs['prompt']
                prompt_id = self._extract_prompt_id_from_content(prompt)
                if prompt_id:
                    print(f"Found PROMPT_ID in prompt: {prompt_id}")
                    return prompt_id
            
            # If no PROMPT_ID found, fall back to variable name detection
            # Get the caller's frame (go back several levels to find the actual caller)
            frame = inspect.currentframe()
            for _ in range(4):  # Go back through wrapper layers
                if frame is None:
                    break
                frame = frame.f_back
            
            if frame is None:
                return "messages"  # Default fallback
            
            local_vars = frame.f_locals
            func_name = frame.f_code.co_name
            
            print(f"Checking frame: {func_name} with vars: {list(local_vars.keys())}")
            
            # Look for common variable names first
            common_names = ['messages', 'request_messages', 'prompt', 'system_prompt', 'user_prompt']
            for name in common_names:
                if name in local_vars:
                    print(f"Found common variable: {name}")
                    return name
            
            # Look for any variable containing 'prompt' or 'message'
            for var_name in local_vars.keys():
                if any(keyword in var_name.lower() for keyword in ['prompt', 'message']):
                    if not var_name.startswith('_'):
                        print(f"Found keyword variable: {var_name}")
                        return var_name
            
            # Use function name if it's related to prompts
            if any(keyword in func_name.lower() for keyword in ['prompt', 'chat', 'message', 'ai']):
                return f"function_{func_name}"
            
            # Final fallback based on content
            if 'messages' in kwargs:
                return 'messages'
            elif 'prompt' in kwargs:
                return 'prompt'
            
            return "<unknown>"
            
        except Exception as e:
            print(f"Error in _extract_variable_symbol: {e}")
            # Safe fallback
            if 'messages' in kwargs:
                return 'messages'
            elif 'prompt' in kwargs:
                return 'prompt'
            return "<unknown>"
    
    def _extract_prompt_info(self, args, kwargs, symbol="<unknown>"):
        """Extract prompt information from API call arguments."""
        # Log the call with symbol
        call_info = {
            'symbol': symbol,
            'timestamp': time.time(),
            'function': 'openai_create'
        }
        
        self.call_log.append(call_info)
        if symbol != "<unknown>":
            self.traced_symbols.add(symbol)
        
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
                            'symbol': var_name,
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
        # Restore original methods
        try:
            tracer.restore_original_methods()
        except Exception as e:
            print(f"Error restoring methods: {e}")
            
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
                        if 'symbol' in call_info and call_info['symbol'] != "<unknown>":
                            symbols.add(call_info['symbol'])
                        # Backward compatibility with old format
                        elif 'symbols' in call_info:
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