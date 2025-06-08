"""
OpenAI ChatCompletion helper for Kai VPM conversational charter generation
"""

import os
import streamlit as st
from typing import List, Dict
import openai

def check_openai_key() -> bool:
    """Check if OpenAI API key is available"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False
    
    # Set the API key for openai client
    openai.api_key = api_key
    return True


def ask_gpt(messages: List[Dict[str, str]], model: str = "gpt-3.5-turbo") -> str:
    """
    Send messages to OpenAI ChatCompletion and return response
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: OpenAI model to use
        
    Returns:
        Response content as string
        
    Raises:
        Exception: If API call fails or key is missing
    """
    if not check_openai_key():
        raise Exception("OPENAI_API_KEY environment variable is required")
    
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except openai.APIError as e:
        raise Exception(f"OpenAI API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error calling OpenAI: {str(e)}")


def get_system_prompt() -> str:
    """Get the system prompt for charter conversation"""
    return """You are Kai, an expert project manager.
Your job is to guide the user to define a project charter through natural conversation.
Ask ONE question at a time in Japanese, building on previous answers.
Be conversational and helpful, not formal.

When you have enough information to create a complete charter, reply with <charter_complete/> followed by a JSON block that exactly matches this schema:

{
  "name": "project name",
  "purpose": "why this project exists",
  "outcomes": ["list", "of", "expected", "outcomes"],
  "scope": {
    "in": ["what", "is", "included"],
    "out": ["what", "is", "excluded"]
  },
  "stakeholders": [
    {"name": "Person Name", "role": "their role"}
  ],
  "constraints": {
    "budget": "budget amount or 'なし'",
    "deadline": "deadline date or '未定'",
    "tools": ["list", "of", "tools", "or", "constraints"]
  },
  "milestones": [
    {"date": "YYYY-MM-DD or '未定'", "title": "milestone description"}
  ],
  "risks": [
    {"risk": "risk description", "mitigation": "mitigation strategy"}
  ],
  "success_metrics": ["how", "to", "measure", "success"]
}

Start by asking about the project's main goal or purpose."""


def extract_charter_json(response: str) -> dict:
    """
    Extract JSON from response that contains <charter_complete/>
    
    Args:
        response: GPT response containing <charter_complete/> and JSON
        
    Returns:
        Parsed charter data as dict, or None if no valid JSON found
    """
    import json
    import re
    
    if "<charter_complete/>" not in response:
        return None
    
    # Find JSON block after <charter_complete/>
    json_match = re.search(r'<charter_complete/>\s*```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if not json_match:
        # Try without code blocks
        json_match = re.search(r'<charter_complete/>\s*(\{.*?\})', response, re.DOTALL)
    
    if not json_match:
        return None
    
    try:
        json_str = json_match.group(1)
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None