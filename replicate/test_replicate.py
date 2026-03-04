#!/usr/bin/env python3
"""
Test Twi AI (Ama) on Replicate

Usage:
    export REPLICATE_API_TOKEN="r8_your_token_here"
    python test_replicate.py
"""

import os
import sys

try:
    import replicate
except ImportError:
    print("Installing replicate...")
    os.system("pip install replicate")
    import replicate

MODEL = "travis-moore/twi-llama-v5"

# Test prompts
TEST_PROMPTS = [
    # Twi greetings
    "Wo ho te sɛn?",
    "Maakye! Ɛte sɛn?",
    
    # English
    "Who are you?",
    "Who created you?",
    
    # Translation
    "How do you say 'I love you' in Twi?",
    
    # Culture
    "Tell me a Twi proverb about wisdom",
    
    # Mixed
    "What does 'Akwaaba' mean?",
]


def test_model():
    """Test the model with various prompts"""
    
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        print("❌ Error: REPLICATE_API_TOKEN not set")
        print("\nGet your token at: https://replicate.com/account/api-tokens")
        print('\nRun: export REPLICATE_API_TOKEN="r8_your_token_here"')
        sys.exit(1)
    
    print(f"🧪 Testing {MODEL}")
    print("=" * 50)
    
    for i, prompt in enumerate(TEST_PROMPTS, 1):
        print(f"\n[{i}/{len(TEST_PROMPTS)}] User: {prompt}")
        print("-" * 40)
        
        try:
            # Run with streaming
            print("Ama: ", end="", flush=True)
            for event in replicate.stream(
                MODEL,
                input={
                    "prompt": prompt,
                    "max_tokens": 256,
                    "temperature": 0.7
                }
            ):
                print(str(event), end="", flush=True)
            print()
            
        except replicate.exceptions.ReplicateError as e:
            print(f"❌ Error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    print("\n" + "=" * 50)
    print("✅ Testing complete!")


def chat_mode():
    """Interactive chat with Ama"""
    
    token = os.environ.get("REPLICATE_API_TOKEN")
    if not token:
        print("❌ Error: REPLICATE_API_TOKEN not set")
        sys.exit(1)
    
    print("💬 Chat with Ama (type 'quit' to exit)")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Da yie! (Goodbye!)")
                break
            
            if not user_input:
                continue
            
            print("Ama: ", end="", flush=True)
            for event in replicate.stream(
                MODEL,
                input={
                    "prompt": user_input,
                    "max_tokens": 512,
                    "temperature": 0.7
                }
            ):
                print(str(event), end="", flush=True)
            print()
            
        except KeyboardInterrupt:
            print("\n👋 Da yie!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "chat":
        chat_mode()
    else:
        test_model()
        print("\n💡 Tip: Run 'python test_replicate.py chat' for interactive mode")
