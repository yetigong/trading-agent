import os
import unittest

from dotenv import load_dotenv

from trading_agent.llm.client import get_llm_client

load_dotenv()


@unittest.skipUnless(os.getenv("HUGGINGFACE_API_KEY"), "HUGGINGFACE_API_KEY not set")
class TestHuggingFaceLive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.llm_client = get_llm_client("huggingface", model="financial")

    def test_generate_response(self):
        response = self.llm_client.generate_response("Reply with exactly: OK")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response.strip()), 0)


if __name__ == "__main__":
    unittest.main()
