from typing import Dict, Any, Optional
from .base import LLMClient

class MockLLMClient(LLMClient):
    """Mock LLM client for testing and development."""
    
    def __init__(self, responses: Dict[str, str] = None):
        self.responses = responses or {}
    
    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Return a mock response based on the prompt."""
        # If we have a specific response for this prompt, use it
        if prompt in self.responses:
            return self.responses[prompt]
        
        # Otherwise, return a default response
        return "This is a mock response. Please implement actual LLM integration." 