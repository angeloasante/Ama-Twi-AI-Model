"""
HuggingFace Inference Endpoint Client for Twi AI (Ama)
======================================================
Use this to call your HuggingFace deployed model.

Setup:
1. Deploy model at: https://ui.endpoints.huggingface.co/new
2. Select: travis-moore/twi-llama-v5
3. Pick GPU: A10G recommended
4. Enable: Scale to 0
5. Copy your endpoint URL below
"""

import os
import requests
import json
from typing import Optional, Dict, Any

# Configuration
ENDPOINT_URL = os.environ.get(
    "HF_ENDPOINT_URL", 
    "https://vs68t0qrfr3hsfp3.us-east-1.aws.endpoints.huggingface.cloud"
)
HF_TOKEN = os.environ.get("HF_TOKEN")  # Required - set in environment

# System prompt
SYSTEM_PROMPT = """You are Ama (meaning "born on Saturday" in Akan), a bilingual AI assistant fluent in Twi and English.
Created by Angelo Asante, a Ghanaian developer passionate about AI for African languages.
Match the user's language - if they write Twi, respond in Twi with proper orthography (ɛ, ɔ)."""


class TwiAIClient:
    """Client for HuggingFace Inference Endpoint."""
    
    def __init__(
        self, 
        endpoint_url: str = ENDPOINT_URL,
        token: str = HF_TOKEN,
        system_prompt: str = SYSTEM_PROMPT
    ):
        self.endpoint_url = endpoint_url
        self.token = token
        self.system_prompt = system_prompt
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def chat(
        self,
        message: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Send a message to Ama and get a response.
        
        Args:
            message: Your message (Twi or English)
            max_tokens: Maximum response length
            temperature: Creativity (0.0-2.0)
            top_p: Nucleus sampling
            system_prompt: Override default system prompt
            
        Returns:
            Ama's response
        """
        # Build chat messages
        messages = [
            {"role": "system", "content": system_prompt or self.system_prompt},
            {"role": "user", "content": message}
        ]
        
        # HuggingFace TGI format
        payload = {
            "inputs": self._format_chat(messages),
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "do_sample": True,
                "return_full_text": False
            }
        }
        
        try:
            response = requests.post(
                self.endpoint_url,
                headers=self.headers,
                json=payload,
                timeout=120  # 2 min timeout for cold starts
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Parse response based on format
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "")
            elif isinstance(result, dict):
                return result.get("generated_text", str(result))
            else:
                return str(result)
                
        except requests.exceptions.RequestException as e:
            return f"Error: {str(e)}"
    
    def _format_chat(self, messages: list) -> str:
        """Format messages for the model."""
        # Llama 3 chat format
        formatted = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                formatted += f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "user":
                formatted += f"<|start_header_id|>user<|end_header_id|>\n\n{content}<|eot_id|>"
            elif role == "assistant":
                formatted += f"<|start_header_id|>assistant<|end_header_id|>\n\n{content}<|eot_id|>"
        
        # Add generation prompt
        formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        return formatted
    
    def check_status(self) -> Dict[str, Any]:
        """Check endpoint health status."""
        try:
            response = requests.get(
                self.endpoint_url.replace("/", "/health/"),
                headers=self.headers,
                timeout=10
            )
            return {"status": "healthy" if response.ok else "unhealthy", "code": response.status_code}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Convenience function
def ask_ama(message: str, **kwargs) -> str:
    """Quick function to ask Ama a question."""
    client = TwiAIClient()
    return client.chat(message, **kwargs)


# Example usage
if __name__ == "__main__":
    print("=" * 50)
    print("Twi AI (Ama) - HuggingFace Endpoint Client")
    print("=" * 50)
    
    # Check if endpoint is configured
    if "YOUR-ENDPOINT-ID" in ENDPOINT_URL:
        print("\n⚠️  Please configure your endpoint URL!")
        print("1. Deploy at: https://ui.endpoints.huggingface.co/new")
        print("2. Select model: travis-moore/twi-llama-v5")
        print("3. Copy the endpoint URL")
        print("4. Set environment variable: export HF_ENDPOINT_URL='your-url'")
        print("   Or edit this file directly")
    else:
        client = TwiAIClient()
        
        # Test messages
        test_messages = [
            "Hello, how are you?",
            "Wo ho te sɛn?",
            "What is the meaning of 'Akwaaba'?",
        ]
        
        for msg in test_messages:
            print(f"\n👤 You: {msg}")
            response = client.chat(msg)
            print(f"🤖 Ama: {response}")
