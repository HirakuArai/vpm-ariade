"""
OpenAI ChatCompletion helper for Kai VPM conversational charter generation
"""

import os
from typing import List, Dict, Optional
import openai

def check_openai_key() -> bool:
    """Check if OpenAI API key is available"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return False
    
    # Set the API key for openai client
    openai.api_key = api_key
    return True


def ask_gpt(messages: List[Dict[str, str]], model: str = "gpt-4.1") -> str:
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
    return """You are **Kai**, an expert project manager.

* Goal: help the user define a complete project charter via natural conversation.
* Ask **exactly ONE** question at a time in Japanese.
* At each turn follow this algorithm:

  1. Inspect the JSON charter schema keys and note which keys are still empty or [].
  2. Choose the **most important missing key** and ask a concise, domain‑appropriate question to fill it.
  3. Never repeat a question that is semantically similar to any of the last 3 questions.
  4. Keep the tone friendly and practical; avoid abstract business jargon if the context is leisure / personal projects.
* When **all keys are filled**, reply with:

  <charter_complete/>

  ```json
  { <fully‑populated charter JSON> }
  ```

No extra text after the JSON block."""


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


# Key to Japanese question mapping
KEY_TO_JA = {
    "name": "プロジェクトの名前を教えてください。",
    "purpose": "このプロジェクトの目的や背景について教えてください。",
    "outcomes": "このプロジェクトで期待される成果物や結果を教えてください。",
    "scope.in": "このプロジェクトに含まれる作業やタスクについて教えてください。",
    "scope.out": "このプロジェクトから除外される作業やタスクはありますか？",
    "stakeholders": "このプロジェクトに関わる人や組織について教えてください。",
    "constraints.budget": "予算に関する制約はありますか？",
    "constraints.deadline": "期限に関する制約はありますか？",
    "constraints.tools": "使用するツールや技術に関する制約はありますか？",
    "milestones": "重要なマイルストーンや中間目標はありますか？",
    "risks": "予想されるリスクや懸念事項はありますか？",
    "success_metrics": "成功をどのように測定しますか？"
}


async def generate_next_question(convo: List[Dict], charter: Dict) -> str:
    """
    Generate the next most relevant question based on missing charter keys
    
    Args:
        convo: Conversation history
        charter: Current charter data (may be incomplete)
        
    Returns:
        Next question to ask in Japanese
    """
    # Derive missing keys
    missing_keys = []
    
    # Check top-level keys
    for key in ["name", "purpose", "outcomes", "stakeholders", "milestones", "risks", "success_metrics"]:
        if not charter.get(key) or (isinstance(charter.get(key), list) and len(charter.get(key)) == 0):
            missing_keys.append(key)
    
    # Check scope keys
    scope = charter.get("scope", {})
    if not scope.get("in") or len(scope.get("in", [])) == 0:
        missing_keys.append("scope.in")
    if not scope.get("out") or len(scope.get("out", [])) == 0:
        missing_keys.append("scope.out")
    
    # Check constraints keys
    constraints = charter.get("constraints", {})
    if not constraints.get("budget"):
        missing_keys.append("constraints.budget")
    if not constraints.get("deadline"):
        missing_keys.append("constraints.deadline")
    if not constraints.get("tools") or len(constraints.get("tools", [])) == 0:
        missing_keys.append("constraints.tools")
    
    if not missing_keys:
        return "すべての情報が揃いました。"
    
    # Build controller prompt
    controller_prompt = f"""You are a meta-planner for project charter creation.

missing_keys = {missing_keys}

Return ONLY the most important key to ask next as plain text. Choose based on logical dependency and importance:
1. name (project identity)
2. purpose (why the project exists)
3. outcomes (what we want to achieve)
4. scope.in (what's included)
5. stakeholders (who's involved)
6. constraints.budget, constraints.deadline (practical limits)
7. milestones (timeline)
8. risks (potential issues)
9. scope.out, constraints.tools, success_metrics (refinements)

Return only the key name, nothing else."""
    
    try:
        if not check_openai_key():
            # Fallback to simple priority order if no API key
            priority_order = ["name", "purpose", "outcomes", "scope.in", "stakeholders", "constraints.budget", "constraints.deadline"]
            for key in priority_order:
                if key in missing_keys:
                    return KEY_TO_JA.get(key, "次の質問をお聞かせください。")
            return KEY_TO_JA.get(missing_keys[0] if missing_keys else "name", "次の質問をお聞かせください。")
        
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": controller_prompt}],
            max_tokens=50,
            temperature=0.2
        )
        
        next_key = response.choices[0].message.content.strip()
        
        # Map key to Japanese question
        return KEY_TO_JA.get(next_key, "次の質問をお聞かせください。")
        
    except Exception:
        # Fallback to simple priority if API call fails
        priority_order = ["name", "purpose", "outcomes", "scope.in", "stakeholders"]
        for key in priority_order:
            if key in missing_keys:
                return KEY_TO_JA.get(key, "次の質問をお聞かせください。")
        return KEY_TO_JA.get(missing_keys[0], "次の質問をお聞かせください。")


def get_system_prompt_with_background(domain_info: Optional[str] = None) -> str:
    """Get the system prompt with optional background information"""
    base_prompt = get_system_prompt()
    
    if domain_info:
        return f"{base_prompt}\n\n<background>\n{domain_info}\n</background>"
    
    return base_prompt