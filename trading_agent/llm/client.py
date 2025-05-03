from typing import Dict, Any, Optional
from .base import LLMClient
from .huggingface_client import HuggingFaceClient
from .claude_client import ClaudeClient
from .gemini_client import GeminiClient
from .openai_client import OpenAIClient
from .mock_client import MockLLMClient

def get_llm_client(client_type: str = "claude", **kwargs) -> LLMClient:
    """
    Factory function to get the appropriate LLM client.
    
    Args:
        client_type: Type of LLM client to use ("openai", "huggingface", "claude", "gemini", or "mock")
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
    elif client_type == "gemini":
        return GeminiClient(**kwargs)
    elif client_type == "mock":
        return MockLLMClient(**kwargs)
    else:
        raise ValueError(f"Unsupported LLM client type: {client_type}") 