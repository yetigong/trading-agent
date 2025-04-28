from typing import Dict, Any, Optional
import os
from anthropic import Anthropic
from .base import LLMClient

class ClaudeClient(LLMClient):
    """Anthropic's Claude API client implementation."""
    
    # Default model to use
    DEFAULT_MODEL = "claude-3-5-sonnet-20241022"
    
    # Available models - using the same model for all tasks for simplicity
    AVAILABLE_MODELS = {
        "general": "claude-3-5-sonnet-20241022",
        "financial": "claude-3-5-sonnet-20241022",
        "code": "claude-3-5-sonnet-20241022",
        "small": "claude-3-5-sonnet-20241022",
        "large": "claude-3-5-sonnet-20241022"
    }
    
    def __init__(self, model: str = None, api_key: str = None):
        """
        Initialize the Claude client.
        
        Args:
            model: Model name or key from AVAILABLE_MODELS. If None, uses DEFAULT_MODEL
            api_key: Anthropic API key. If None, tries to get from environment
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = self.AVAILABLE_MODELS.get(model, model) or self.DEFAULT_MODEL
    
    def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a response using Claude's API.
        
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
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.7,
                system="""You are a trading assistant that provides specific trading decisions in a structured format.
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
5. Risk Level: medium""",
                messages=[
                    {
                        "role": "user",
                        "content": formatted_prompt
                    }
                ],
                timeout=30  # 30 second timeout
            )
            
            return message.content[0].text
            
        except Exception as e:
            raise Exception(f"Error generating response from Claude: {str(e)}")
    
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
            "general": "Claude-3.5 Sonnet: Latest model for all tasks",
            "financial": "Claude-3.5 Sonnet: Latest model for all tasks",
            "code": "Claude-3.5 Sonnet: Latest model for all tasks",
            "small": "Claude-3.5 Sonnet: Latest model for all tasks",
            "large": "Claude-3.5 Sonnet: Latest model for all tasks"
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