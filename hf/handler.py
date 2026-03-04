"""
Custom handler for HuggingFace Inference Endpoints
Twi AI (Ama) - travis-moore/twi-llama-v5
"""

from typing import Dict, Any
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


class EndpointHandler:
    def __init__(self, path: str = ""):
        """Load model and tokenizer."""
        self.tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            torch_dtype=torch.float16,
            device_map="auto"
        )
    
    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process inference request.
        
        Expected input:
        {
            "inputs": "Your message here",
            "parameters": {
                "max_new_tokens": 512,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        """
        # Get inputs
        inputs = data.get("inputs", "")
        params = data.get("parameters", {})
        
        # Default parameters
        max_new_tokens = params.get("max_new_tokens", 512)
        temperature = params.get("temperature", 0.7)
        top_p = params.get("top_p", 0.9)
        do_sample = params.get("do_sample", True)
        
        # System prompt
        system_prompt = params.get("system_prompt", 
            "You are Ama, a bilingual AI assistant fluent in Twi and English. "
            "Created by Angelo Asante. Match the user's language."
        )
        
        # Build chat format
        if isinstance(inputs, str):
            # Format as chat
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": inputs}
            ]
            prompt = self.tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
        else:
            prompt = str(inputs)
        
        # Generate
        outputs = self.pipe(
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature if do_sample else None,
            top_p=top_p if do_sample else None,
            do_sample=do_sample,
            pad_token_id=self.tokenizer.pad_token_id,
            return_full_text=False
        )
        
        # Extract generated text
        generated_text = outputs[0]["generated_text"] if outputs else ""
        
        return {
            "generated_text": generated_text
        }
