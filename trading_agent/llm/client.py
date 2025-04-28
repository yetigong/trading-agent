from typing import Dict, Any, Optional
import os
import openai
from dotenv import load_dotenv
from .base import LLMClient
from .huggingface_client import HuggingFaceClient
from .claude_client import ClaudeClient

class OpenAIClient(LLMClient):
    """OpenAI GPT client implementation."""
    
    def __init__(self, model: str = "gpt-4"):
        load_dotenv()
        self.model = model
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Generate a response using OpenAI's API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a trading assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error generating response from OpenAI: {str(e)}")

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

def get_llm_client(client_type: str = "claude", **kwargs) -> LLMClient:
    """
    Factory function to get the appropriate LLM client.
    
    Args:
        client_type: Type of LLM client to use ("openai", "huggingface", "claude", or "mock")
        **kwargs: Additional arguments to pass to the client constructor
        
    Returns:
        An instance of the requested LLM client
    """
    if client_type == "openai":
        return OpenAIClient(**kwargs)
    elif client_type == "huggingface":
        return HuggingFaceClient(**kwargs)
    elif client_type == "claude":
        return ClaudeClient(**kwargs)
    elif client_type == "mock":
        return MockLLMClient(**kwargs)
    else:
        raise ValueError(f"Unsupported LLM client type: {client_type}") 