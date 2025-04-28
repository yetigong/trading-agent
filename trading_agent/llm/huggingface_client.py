from typing import Dict, Any, Optional
import os
from huggingface_hub import InferenceClient
from .base import LLMClient

class HuggingFaceClient(LLMClient):
    """HuggingFace Inference API client implementation."""
    
    # Default model to use if none specified
    DEFAULT_MODEL = "microsoft/phi-1.5"
    
    # Available models for different use cases
    AVAILABLE_MODELS = {
        "general": "microsoft/phi-1.5",
        "financial": "microsoft/phi-1.5",  # Using Phi-1.5 for now
        "code": "microsoft/phi-1.5",  # Using Phi-1.5 for now
        "small": "microsoft/phi-1.5",
        "large": "microsoft/phi-1.5"  # Using Phi-1.5 for now
    }
    
    def __init__(self, model: str = None, api_key: str = None):
        """
        Initialize the HuggingFace client.
        
        Args:
            model: Model name or key from AVAILABLE_MODELS. If None, uses DEFAULT_MODEL
            api_key: HuggingFace API key. If None, tries to get from environment
        """
        self.api_key = api_key or os.getenv('HUGGINGFACE_API_KEY')
        if not self.api_key:
            raise ValueError("HUGGINGFACE_API_KEY not found in environment variables")
        
        self.client = InferenceClient(token=self.api_key)
        self.model = self.AVAILABLE_MODELS.get(model, model) or self.DEFAULT_MODEL
    
    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a response using HuggingFace's Inference API.
        
        Args:
            prompt: The input prompt
            context: Optional context information
            
        Returns:
            Generated response as string
        """
        try:
            # Format the prompt with context if provided
            formatted_prompt = self._format_prompt(prompt, context)
            
            # Generate response
            response = self.client.text_generation(
                prompt=formatted_prompt,
                model=self.model,
                max_new_tokens=512,
                temperature=0.7,
                top_p=0.95,
                repetition_penalty=1.1
            )
            
            return response.strip()
            
        except Exception as e:
            raise Exception(f"Error generating response from HuggingFace: {str(e)}")
    
    def _format_prompt(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Format the prompt with context information.
        
        Args:
            prompt: The input prompt
            context: Optional context information
            
        Returns:
            Formatted prompt string
        """
        if not context:
            return prompt
            
        # Format context as a string
        context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
        
        # Combine context and prompt
        return f"""Context:
{context_str}

Task:
{prompt}"""
    
    @classmethod
    def get_available_models(cls) -> Dict[str, str]:
        """Get a dictionary of available models and their descriptions."""
        return {
            "general": "Phi-1.5: General purpose model for various tasks",
            "financial": "Phi-1.5: Model with good financial analysis capabilities",
            "code": "Phi-1.5: Model with good code generation capabilities",
            "small": "Phi-1.5: Lightweight model for quick responses",
            "large": "Phi-1.5: Model for complex tasks"
        }
    
    def switch_model(self, model: str) -> None:
        """
        Switch to a different model.
        
        Args:
            model: Model name or key from AVAILABLE_MODELS
        """
        if model in self.AVAILABLE_MODELS:
            self.model = self.AVAILABLE_MODELS[model]
        else:
            self.model = model 