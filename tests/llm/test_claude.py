import unittest
import os
from dotenv import load_dotenv
from trading_agent.llm.client import get_llm_client
from .test_base import BaseLLMClientTest

class TestClaudeClient(BaseLLMClientTest):
    """Test cases for Claude client."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        load_dotenv()
        
        # Check if API key is set
        if not os.getenv('ANTHROPIC_API_KEY'):
            self.skipTest("ANTHROPIC_API_KEY not found in environment variables")
        
        # Initialize Claude client
        self.client = get_llm_client("claude", model="general")
    
    def test_basic_response(self):
        """Test basic response generation."""
        for prompt in self.test_prompts:
            with self.subTest(prompt=prompt):
                try:
                    response = self.client.generate_response(prompt)
                    self._test_response_format(response)
                except Exception as e:
                    self.fail(f"Response generation failed: {str(e)}")
    
    def test_model_switching(self):
        """Test model switching functionality."""
        model_types = ["financial", "code", "small", "large"]
        for model_type in model_types:
            with self.subTest(model_type=model_type):
                self._test_model_switching(self.client, model_type)
    
    def test_context_handling(self):
        """Test context handling in prompts."""
        self._test_context_handling(self.client)
    
    def test_error_handling(self):
        """Test error handling."""
        self._test_error_handling(self.client)

if __name__ == '__main__':
    unittest.main() 