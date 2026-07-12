from typing import Dict, Any, Optional
import os
import google.generativeai as genai
from .base import LLMClient

class GeminiClient(LLMClient):
    """Google's Gemini API client implementation."""

    # Default: gemini-3.5-flash (thinking/reasoning). Lite stays on the "small" alias.
    DEFAULT_MODEL = "gemini-3.5-flash"

    AVAILABLE_MODELS = {
        "general": "gemini-3.5-flash",
        "financial": "gemini-3.5-flash",
        "reasoning": "gemini-3.5-flash",
        "code": "gemini-3.5-flash",
        "small": "gemini-3.1-flash-lite-preview",
        "large": "gemini-3.1-pro-preview",
    }
    
    def __init__(self, model: str = None, api_key: str = None):
        """
        Initialize the Gemini client.
        
        Args:
            model: Model name or key from AVAILABLE_MODELS. If None, uses DEFAULT_MODEL
            api_key: Google API key. If None, tries to get from environment
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        self.model = self.AVAILABLE_MODELS.get(model, model) or self.DEFAULT_MODEL
        self.client = genai.GenerativeModel(self.model)
    
    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a response using Gemini's API.
        
        Args:
            prompt: The input prompt
            context: Optional context information
            
        Returns:
            Generated response as string
        """
        try:
            # Format the prompt with context if provided
            formatted_prompt = self._format_prompt(prompt, context)
            
            # Keep system guidance JSON-compatible with strategy/analysis prompts.
            system_message = (
                "You are a trading assistant. Follow the user's schema exactly. "
                "When asked for JSON, respond with JSON only (no markdown fences).\n\n"
            )
            full_prompt = system_message + formatted_prompt

            response = self.client.generate_content(
                full_prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                }
            )

            if not response.candidates:
                raise ValueError("Gemini returned no candidates")

            text = response.text
            if not text:
                raise ValueError(
                    f"Gemini returned empty text (finish_reason={response.candidates[0].finish_reason})"
                )

            return text
            
        except Exception as e:
            raise Exception(f"Error generating response from Gemini: {str(e)}")
    
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
            "general": "Gemini 3.5 Flash: thinking/reasoning default",
            "financial": "Gemini 3.5 Flash: thinking/reasoning default",
            "reasoning": "Gemini 3.5 Flash: thinking/reasoning",
            "code": "Gemini 3.5 Flash",
            "small": "Gemini 3.1 Flash Lite Preview: fast/cheap",
            "large": "Gemini 3.1 Pro Preview: strongest reasoning",
        }
    
    def switch_model(self, model: str) -> None:
        """
        Switch to a different model.
        
        Args:
            model: Model name or key from AVAILABLE_MODELS
        """
        if model in self.AVAILABLE_MODELS:
            self.model = self.AVAILABLE_MODELS[model]
            self.client = genai.GenerativeModel(self.model)
        else:
            self.model = model
            self.client = genai.GenerativeModel(self.model) 