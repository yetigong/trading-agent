import unittest
from trading_agent.llm.client import get_llm_client
from .test_base import BaseLLMClientTest

class TestMockClient(BaseLLMClientTest):
    """Test cases for Mock client."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
        # Initialize Mock client with some test responses
        self.test_responses = {
            "What is the current market sentiment for AAPL?": "The market sentiment for AAPL is bullish.",
            "Should I buy or sell TSLA based on recent news?": "Based on recent news, consider selling TSLA.",
        }
        self.client = get_llm_client("mock", responses=self.test_responses)
    
    def test_basic_response(self):
        """Test basic response generation."""
        # Test predefined responses
        for prompt, expected_response in self.test_responses.items():
            with self.subTest(prompt=prompt):
                response = self.client.generate_response(prompt)
                self.assertEqual(response, expected_response)
        
        # Test default response for unknown prompt
        unknown_prompt = "This is an unknown prompt"
        response = self.client.generate_response(unknown_prompt)
        self.assertEqual(response, "This is a mock response. Please implement actual LLM integration.")
    
    def test_error_handling(self):
        """Test error handling."""
        self._test_error_handling(self.client)

if __name__ == '__main__':
    unittest.main() 