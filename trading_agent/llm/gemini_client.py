from typing import Dict, Any, Optional
import os
import google.generativeai as genai
from .base import LLMClient

class GeminiClient(LLMClient):
    """Google's Gemini API client implementation."""
    
    # Default model to use
    DEFAULT_MODEL = "gemini-2.0-flash"
    
    # Available models - using the same model for all tasks for simplicity
    AVAILABLE_MODELS = {
        "general": "gemini-2.0-flash",
        "financial": "gemini-2.0-flash",
        "code": "gemini-2.0-flash",
        "small": "gemini-2.0-flash",
        "large": "gemini-2.0-flash"
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
            
            # Add system message for trading decisions
            system_message = """You are a trading assistant that provides specific trading decisions in a structured format.
For each decision, you must provide:
1. Action (BUY/SELL)
2. Symbol
3. Quantity
4. Reasoning
5. Risk Level (low/medium/high)

Each decision must be formatted exactly as shown above, with the numbers and colons. For example:
1. Action: BUY
2. Symbol: AAPL
3. Quantity: 10
4. Reasoning: Strong fundamentals and growth potential
5. Risk Level: medium

Now, based on the following information, provide your trading decisions:

"""
            
            # Combine system message and prompt
            full_prompt = system_message + formatted_prompt
            
            # Generate response
            response = self.client.generate_content(
                full_prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                }
            )
            
            return response.text
            
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
            "general": "Gemini 2.0 Flash: Latest model for all tasks",
            "financial": "Gemini 2.0 Flash: Latest model for all tasks",
            "code": "Gemini 2.0 Flash: Latest model for all tasks",
            "small": "Gemini 2.0 Flash: Latest model for all tasks",
            "large": "Gemini 2.0 Flash: Latest model for all tasks"
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