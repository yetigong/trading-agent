import unittest
import os
from dotenv import load_dotenv
from trading_agent.llm.client import get_llm_client
from .test_base import BaseLLMClientTest

class TestOpenAIClient(BaseLLMClientTest):
    """Test cases for OpenAI client."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        load_dotenv()
        
        # Check if API key is set
        if not os.getenv('OPENAI_API_KEY'):
            self.skipTest("OPENAI_API_KEY not found in environment variables")
        
        # Initialize OpenAI client
        self.client = get_llm_client("openai", model="gpt-4")
    
    def test_basic_response(self):
        """Test basic response generation."""
        for prompt in self.test_prompts:
            with self.subTest(prompt=prompt):
                try:
                    response = self.client.generate_response(prompt)
                    self._test_response_format(response)
                except Exception as e:
                    self.fail(f"Response generation failed: {str(e)}")
    
    def test_error_handling(self):
        """Test error handling."""
        self._test_error_handling(self.client)

if __name__ == '__main__':
    unittest.main() 