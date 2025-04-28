from trading_agent.llm.client import get_llm_client
import os
from dotenv import load_dotenv

def test_huggingface_client():
    # Load environment variables
    load_dotenv()
    
    # Check if API key is set
    if not os.getenv('HUGGINGFACE_API_KEY'):
        print("Error: HUGGINGFACE_API_KEY not found in environment variables")
        return
    
    # Initialize HuggingFace client with financial model
    llm_client = get_llm_client("huggingface", model="financial")
    
    # Test prompts
    test_prompts = [
        "Analyze the current market conditions and provide a brief overview.",
        "What are the key factors to consider when making trading decisions?",
        "How would you approach portfolio rebalancing in a volatile market?"
    ]
    
    print("\nTesting HuggingFace Client...")
    print(f"Using model: {llm_client.model}")
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\nTest {i}:")
        print(f"Prompt: {prompt}")
        try:
            response = llm_client.generate_response(prompt)
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    # Test model switching
    print("\nTesting model switching...")
    try:
        llm_client.switch_model("general")
        print(f"Switched to model: {llm_client.model}")
        response = llm_client.generate_response("What is your current model?")
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error switching models: {str(e)}")

if __name__ == "__main__":
    test_huggingface_client() 