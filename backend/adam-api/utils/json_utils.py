import json
from typing import Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import logging

logger = logging.getLogger(__name__)


class SafeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles non-serializable objects gracefully"""
    
    def default(self, obj: Any) -> Any:
        # Handle LangChain message objects
        if isinstance(obj, BaseMessage):
            return {
                "type": type(obj).__name__,
                "content": obj.content,
                "additional_kwargs": self._clean_dict(obj.additional_kwargs) if hasattr(obj, 'additional_kwargs') else {}
            }
        
        # Handle other non-serializable objects
        try:
            # Try the default serialization
            return super().default(obj)
        except TypeError:
            # If that fails, return a string representation
            logger.debug(f"Converting non-serializable object to string: {type(obj)}")
            return str(obj)
    
    def _clean_dict(self, d: dict) -> dict:
        """Recursively clean a dictionary to ensure all values are JSON serializable"""
        if not isinstance(d, dict):
            return {}
        
        clean = {}
        for key, value in d.items():
            try:
                # Test if the value is serializable
                json.dumps(value, cls=SafeJSONEncoder)
                clean[key] = value
            except Exception:
                # If not, convert to string
                clean[key] = str(value)
        
        return clean


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """Safely serialize an object to JSON, handling non-serializable objects"""
    return json.dumps(obj, cls=SafeJSONEncoder, **kwargs)


def ensure_json_serializable(obj: Any) -> Any:
    """Ensure an object is JSON serializable by converting it if necessary"""
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        # Parse and re-encode with SafeJSONEncoder
        return json.loads(safe_json_dumps(obj)) 