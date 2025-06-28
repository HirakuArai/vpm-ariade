"""
OpenAI Configuration Module for Kai VPM

This module provides centralized configuration for all OpenAI API calls across the system.
It enforces the absolute requirement to use GPT-4.1 consistently for all AI interactions.

🚨 CRITICAL REQUIREMENT: ALL OpenAI API calls MUST use GPT-4.1
   - This is an absolute requirement that must be maintained for all future additions
   - No exceptions for any model variations (gpt-4o, gpt-4o-mini, gpt-3.5-turbo, etc.)
   - Any deviation from this requirement is strictly prohibited

📋 Usage:
   - Import get_openai_model() function and use it for all OpenAI API calls
   - Never hardcode model names in application code
   - Use the helper functions for consistent API configurations
"""

import os
import logging
from typing import Dict, Any, Optional
import openai

logger = logging.getLogger(__name__)

# 🚨 ABSOLUTE REQUIREMENT: GPT-4.1 ONLY
# This value MUST NEVER be changed without explicit approval
# All OpenAI API calls across the entire system MUST use this model
REQUIRED_OPENAI_MODEL = "gpt-4.1"

def get_openai_model() -> str:
    """
    Get the required OpenAI model for all API calls.
    
    Returns:
        str: The required model name (always "gpt-4.1")
        
    🚨 WARNING: This function MUST always return "gpt-4.1"
    Any attempt to change this violates the core system requirement.
    """
    return REQUIRED_OPENAI_MODEL

def get_default_openai_params() -> Dict[str, Any]:
    """
    Get default parameters for OpenAI API calls.
    
    Returns:
        Dict containing standard parameters with the required model
    """
    return {
        "model": get_openai_model(),
        "temperature": 0.7,
        "max_tokens": 1000
    }

def get_openai_client(api_key: Optional[str] = None) -> openai.OpenAI:
    """
    Get a configured OpenAI client instance.
    
    Args:
        api_key: Optional API key. If not provided, uses OPENAI_API_KEY env var
        
    Returns:
        Configured OpenAI client instance
        
    Raises:
        ValueError: If no API key is available
    """
    if api_key is None:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
    
    return openai.OpenAI(api_key=api_key)

def create_chat_completion(
    messages: list,
    client: Optional[openai.OpenAI] = None,
    **kwargs
) -> Any:
    """
    Create a chat completion with enforced model consistency.
    
    Args:
        messages: List of message dictionaries
        client: Optional OpenAI client instance
        **kwargs: Additional parameters (model will be overridden)
        
    Returns:
        Chat completion response
        
    🚨 Note: The 'model' parameter in kwargs will be ignored and replaced
    with the required GPT-4.1 model to enforce consistency.
    """
    if client is None:
        client = get_openai_client()
    
    # Enforce the required model - ignore any model parameter passed in kwargs
    if "model" in kwargs:
        logger.warning(f"Model parameter '{kwargs['model']}' ignored. Using required model: {REQUIRED_OPENAI_MODEL}")
    
    # Set default parameters and override with kwargs, but always enforce the model
    params = get_default_openai_params()
    params.update(kwargs)
    params["model"] = get_openai_model()  # Always enforce the required model
    params["messages"] = messages
    
    return client.chat.completions.create(**params)

def validate_model_usage(model_name: str) -> bool:
    """
    Validate that the provided model name matches the required model.
    
    Args:
        model_name: The model name to validate
        
    Returns:
        bool: True if valid, False otherwise
        
    Use this function to check if existing code is using the correct model.
    """
    is_valid = model_name == REQUIRED_OPENAI_MODEL
    
    if not is_valid:
        logger.error(
            f"INVALID MODEL DETECTED: '{model_name}' - "
            f"Required model is '{REQUIRED_OPENAI_MODEL}'"
        )
        raise ValueError(
            f"Model '{model_name}' is not allowed. "
            f"Only '{REQUIRED_OPENAI_MODEL}' is permitted for absolute consistency."
        )
    
    return is_valid

def get_migration_guide() -> str:
    """
    Get guidance for migrating existing code to use the centralized configuration.
    
    Returns:
        String containing migration instructions
    """
    return f"""
OpenAI Model Migration Guide
===========================

BEFORE (❌ Incorrect):
    client.chat.completions.create(
        model="gpt-4o",  # or any other model
        messages=messages,
        temperature=0.7
    )

AFTER (✅ Correct):
    from core.v2.openai_config import create_chat_completion
    
    response = create_chat_completion(
        messages=messages,
        temperature=0.7  # model is automatically set to {REQUIRED_OPENAI_MODEL}
    )

OR:
    from core.v2.openai_config import get_openai_model, get_openai_client
    
    client = get_openai_client()
    response = client.chat.completions.create(
        model=get_openai_model(),
        messages=messages,
        temperature=0.7
    )

IMPORTANT: Always use get_openai_model() instead of hardcoding model names!
"""

# Verification function to ensure this module is working correctly
def _verify_config():
    """Internal verification that the configuration is correct"""
    assert get_openai_model() == "gpt-4.1", f"Model configuration error: expected 'gpt-4.1', got '{get_openai_model()}'"
    assert validate_model_usage("gpt-4.1") == True, "Validation function error"
    
    # Test invalid model validation (should raise exception)
    try:
        validate_model_usage("gpt-4o")
        assert False, "Validation should have raised exception for invalid model"
    except ValueError:
        pass  # Expected behavior

# Run verification on import
_verify_config()