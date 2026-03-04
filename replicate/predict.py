"""
Cog prediction interface for Twi AI (Ama)
A bilingual Twi-English conversational AI assistant
Version: 1.0.1
"""

from cog import BasePredictor, Input, ConcatenateIterator
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Iterator

# Model configuration
MODEL_ID = "travis-moore/twi-llama-v5"
DEFAULT_SYSTEM_PROMPT = """You are Ama (meaning "born on Saturday" in Akan), a bilingual AI assistant fluent in Twi and English.

Key traits:
- Created by Angelo Asante, a Ghanaian developer passionate about AI for African languages
- Warm, knowledgeable guide for Ghanaian language and culture
- Seamlessly switches between Twi and English based on user's language
- Expert in Akan proverbs (ɛbɛ), cultural traditions, and customs

Response style:
- Match the user's language (Twi→Twi, English→English, mixed→mixed)
- Keep responses conversational and naturally flowing
- Include cultural context when relevant
- For Twi text, use proper orthography with ɛ and ɔ characters"""


class Predictor(BasePredictor):
    def setup(self):
        """Load the model into memory for efficient inference"""
        print(f"Loading model: {MODEL_ID}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID,
            trust_remote_code=True
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
            attn_implementation="flash_attention_2"  # Use flash attention if available
        )
        
        # Set pad token if not set
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        print("Model loaded successfully!")

    def predict(
        self,
        prompt: str = Input(
            description="Your message to Ama (in Twi or English)",
            default="Wo ho te sɛn?"
        ),
        system_prompt: str = Input(
            description="System prompt defining Ama's behavior",
            default=DEFAULT_SYSTEM_PROMPT
        ),
        max_tokens: int = Input(
            description="Maximum number of tokens to generate",
            default=512,
            ge=1,
            le=4096
        ),
        temperature: float = Input(
            description="Sampling temperature (higher = more creative)",
            default=0.7,
            ge=0.0,
            le=2.0
        ),
        top_p: float = Input(
            description="Nucleus sampling probability",
            default=0.9,
            ge=0.0,
            le=1.0
        ),
        top_k: int = Input(
            description="Top-k sampling (0 = disabled)",
            default=50,
            ge=0,
            le=500
        ),
        repetition_penalty: float = Input(
            description="Penalty for repeating tokens",
            default=1.1,
            ge=1.0,
            le=2.0
        ),
    ) -> ConcatenateIterator[str]:
        """Run inference and stream the response"""
        
        # Build the chat messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Apply chat template
        input_text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Tokenize
        inputs = self.tokenizer(
            input_text,
            return_tensors="pt",
            truncation=True,
            max_length=4096
        ).to(self.model.device)
        
        # Stream generation
        from transformers import TextIteratorStreamer
        from threading import Thread
        
        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )
        
        generation_kwargs = {
            **inputs,
            "streamer": streamer,
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k if top_k > 0 else None,
            "repetition_penalty": repetition_penalty,
            "do_sample": temperature > 0,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }
        
        # Start generation in a separate thread
        thread = Thread(target=self.model.generate, kwargs=generation_kwargs)
        thread.start()
        
        # Stream the output
        for text in streamer:
            yield text
        
        thread.join()


# For local testing
if __name__ == "__main__":
    predictor = Predictor()
    predictor.setup()
    
    # Test with a Twi greeting
    output = list(predictor.predict(prompt="Wo ho te sɛn?"))
    print("".join(output))
