import unittest
from typing import Any, Dict

class BaseLLMClientTest(unittest.TestCase):
    """Base test class for LLM clients."""
    
    def setUp(self):
        """Set up test environment with common test prompts."""
        self.test_prompts = [
            "What is the current market sentiment for AAPL?",
            "Should I buy or sell TSLA based on recent news?",
            "Analyze the technical indicators for NVDA.",
            "What are the key risks for AMD in the current market?"
        ]
        
        self.test_context = {
            "market_data": {
                "AAPL": {"price": 150.0, "volume": 1000000},
                "TSLA": {"price": 200.0, "volume": 500000}
            },
            "technical_indicators": {
                "AAPL": {"RSI": 65, "MACD": 1.5},
                "TSLA": {"RSI": 45, "MACD": -0.5}
            }
        }
    
    def _test_response_format(self, response: str) -> None:
        """Test if response meets basic format requirements."""
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
        self.assertTrue(len(response.split()) >= 3)  # At least 3 words
    
    def _test_model_switching(self, client: Any, model_type: str) -> None:
        """Test switching between different model types."""
        try:
            client.set_model(model_type)
            response = client.generate_response(self.test_prompts[0])
            self._test_response_format(response)
        except Exception as e:
            self.fail(f"Model switching failed for {model_type}: {str(e)}")
    
    def _test_context_handling(self, client: Any) -> None:
        """Test handling of context in prompts."""
        prompt_with_context = (
            f"Given this market data: {self.test_context['market_data']}, "
            "what is your analysis of AAPL?"
        )
        try:
            response = client.generate_response(prompt_with_context)
            self._test_response_format(response)
            self.assertTrue(
                any(word in response.lower() for word in ['price', 'volume', 'market'])
            )
        except Exception as e:
            self.fail(f"Context handling test failed: {str(e)}")
    
    def _test_error_handling(self, client: Any) -> None:
        """Test error handling with invalid inputs."""
        invalid_inputs = [
            "",  # Empty string
            "   ",  # Whitespace
            "a" * 10000,  # Very long input
            None,  # None type
            123  # Wrong type
        ]
        
        for invalid_input in invalid_inputs:
            with self.subTest(invalid_input=invalid_input):
                try:
                    with self.assertRaises(Exception):
                        client.generate_response(invalid_input)
                except Exception as e:
                    self.fail(f"Error handling test failed for {invalid_input}: {str(e)}") 