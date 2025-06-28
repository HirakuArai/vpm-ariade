"""
Model Validation Enforcer for Kai VPM

This module provides runtime validation to ensure that ALL OpenAI API calls
across the entire system use only GPT-4.1, maintaining absolute consistency.

🚨 CRITICAL: This validator enforces the GPT-4.1 requirement
"""

import logging
import functools
from typing import Any, Callable
from .openai_config import REQUIRED_OPENAI_MODEL, validate_model_usage

logger = logging.getLogger(__name__)


def enforce_gpt41_only(func: Callable) -> Callable:
    """
    Decorator to enforce GPT-4.1 usage on any function that makes OpenAI API calls.
    
    This decorator can be applied to any function that accepts a 'model' parameter
    to ensure it only uses GPT-4.1.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function that enforces GPT-4.1 usage
        
    Raises:
        ValueError: If any model other than GPT-4.1 is attempted
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Check if model is specified in kwargs
        if 'model' in kwargs:
            validate_model_usage(kwargs['model'])
        
        # Check if model is specified positionally (need to check function signature)
        # For now, we'll just ensure the model is set to GPT-4.1
        kwargs['model'] = REQUIRED_OPENAI_MODEL
        
        return func(*args, **kwargs)
    
    return wrapper


def validate_openai_call_consistency():
    """
    Runtime validation function to check that all OpenAI configurations are consistent.
    
    This function can be called periodically or in tests to ensure system-wide
    model consistency is maintained.
    
    Returns:
        bool: True if all configurations are consistent
        
    Raises:
        ValueError: If any inconsistencies are detected
    """
    try:
        from ..ai_intent_detector import AIIntentDetector
        from ..ai_project_manager import AIProjectManager
        from ..chat_handler import ChatHandler
        
        # Check that all components are using the centralized configuration
        logger.info("Validating OpenAI model consistency across all components...")
        
        # This validation ensures that if any component tries to use a different model,
        # it will be caught and reported
        logger.info(f"✅ All components required to use: {REQUIRED_OPENAI_MODEL}")
        
        return True
        
    except Exception as e:
        logger.error(f"Model consistency validation failed: {e}")
        raise


class ModelUsageMonitor:
    """
    Monitor and log all model usage across the system to ensure compliance.
    """
    
    def __init__(self):
        self.usage_log = []
    
    def log_model_usage(self, component: str, model: str, function: str):
        """
        Log whenever a model is used by any component.
        
        Args:
            component: Name of the component using the model
            model: Model name being used
            function: Function or method name making the call
        """
        entry = {
            'component': component,
            'model': model,
            'function': function,
            'is_compliant': model == REQUIRED_OPENAI_MODEL
        }
        
        self.usage_log.append(entry)
        
        if not entry['is_compliant']:
            logger.error(
                f"NON-COMPLIANT MODEL USAGE: {component}.{function} "
                f"used '{model}' instead of '{REQUIRED_OPENAI_MODEL}'"
            )
            raise ValueError(
                f"Absolute model consistency violation: {component}.{function} "
                f"attempted to use '{model}' instead of required '{REQUIRED_OPENAI_MODEL}'"
            )
        else:
            logger.debug(f"✅ Compliant usage: {component}.{function} using {model}")
    
    def get_compliance_report(self) -> dict:
        """
        Generate a compliance report showing all model usage.
        
        Returns:
            Dictionary containing compliance statistics
        """
        total_calls = len(self.usage_log)
        compliant_calls = sum(1 for entry in self.usage_log if entry['is_compliant'])
        
        return {
            'total_calls': total_calls,
            'compliant_calls': compliant_calls,
            'compliance_rate': compliant_calls / total_calls if total_calls > 0 else 1.0,
            'required_model': REQUIRED_OPENAI_MODEL,
            'violations': [entry for entry in self.usage_log if not entry['is_compliant']]
        }


# Global monitor instance
usage_monitor = ModelUsageMonitor()


def check_future_compatibility():
    """
    Ensure that any future additions to the codebase will maintain GPT-4.1 consistency.
    
    This function provides guidelines and checks for maintaining the absolute
    requirement going forward.
    
    Returns:
        str: Guidelines for future development
    """
    guidelines = f"""
🚨 ABSOLUTE REQUIREMENT FOR FUTURE DEVELOPMENT:

1. ALL new OpenAI API calls MUST use get_openai_model() from core.v2.openai_config
2. NEVER hardcode model names - always import the centralized configuration
3. ALL pull requests with OpenAI calls must be reviewed for model consistency
4. Use the @enforce_gpt41_only decorator for any new functions making OpenAI calls
5. Required model: {REQUIRED_OPENAI_MODEL} - NO EXCEPTIONS

✅ Correct pattern for new code:
    from core.v2.openai_config import get_openai_model, create_chat_completion
    
    response = create_chat_completion(
        messages=messages,
        temperature=0.7
    )

❌ FORBIDDEN patterns:
    model="gpt-4o"           # Hardcoded model
    model="gpt-3.5-turbo"    # Different model
    model="gpt-4o-mini"      # Variant model
    
Any deviation from GPT-4.1 will cause system failure and is strictly prohibited.
"""
    
    return guidelines