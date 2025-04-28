from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    @abstractmethod
    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The input prompt
            context: Optional context information
            
        Returns:
            Generated response as string
        """
        pass 