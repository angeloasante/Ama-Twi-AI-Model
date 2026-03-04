"""
Deploy Twi AI (Ama) to Modal - Serverless GPU API
Cost: ~$0.001-0.003 per request

Deploy:
    modal deploy modal_deploy.py

Test:
    curl -X POST https://YOUR_USERNAME--twi-ai-chat.modal.run \
      -H "Content-Type: application/json" \
      -d '{"prompt": "Wo ho te sɛn?"}'
"""

import modal

MODEL_ID = "travis-moore/twi-llama-v5"
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"  # For tokenizer
MODEL_DIR = "/model"

# Download model during image build (not at runtime!)
def download_model():
    import os
    from huggingface_hub import snapshot_download
    
    # Download the fine-tuned model (but skip the broken tokenizer files)
    snapshot_download(
        MODEL_ID,
        local_dir=MODEL_DIR,
        ignore_patterns=["*.md", "*.txt", "tokenizer.json", "tokenizer_config.json"],
        token=os.environ.get("HF_TOKEN"),
    )
    
    # Download tokenizer from base Llama model
    snapshot_download(
        BASE_MODEL,
        local_dir=MODEL_DIR,
        allow_patterns=["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"],
        token=os.environ.get("HF_TOKEN"),
    )

# Create the Modal app
app = modal.App("twi-ai")

# Define the container image - model is baked in!
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.2.0",
        "transformers==4.44.0",
        "accelerate>=0.27.2",
        "huggingface_hub>=0.20.0",
        "sentencepiece>=0.1.99",
        "protobuf>=3.20.0",
        "fastapi[standard]",
        "numpy<2",  # torch 2.2 needs numpy < 2
    )
    .run_function(
        download_model,
        secrets=[modal.Secret.from_name("huggingface")],
    )
)

DEFAULT_SYSTEM_PROMPT = """You are Ama (meaning "born on Saturday" in Akan), a bilingual AI assistant fluent in Twi and English.

Key traits:
- Created by Angelo Asante, a Ghanaian developer passionate about AI for African languages
- Warm, knowledgeable guide for Ghanaian language and culture
- Seamlessly switches between Twi and English based on user's language
- Expert in Akan proverbs, cultural traditions, and customs

IMPORTANT - Akan Day Names (MEMORIZE THIS):
| Day       | Male Name | Female Name |
|-----------|-----------|-------------|
| Monday    | Kwadwo    | Adwoa       |
| Tuesday   | Kwabena   | Abena       |
| Wednesday | Kweku     | Akua        |
| Thursday  | Yaw       | Yaa         |
| Friday    | Kofi      | Afua        |
| Saturday  | Kwame     | Ama         |
| Sunday    | Kwasi     | Akosua      |

Always use this table when discussing Akan day names. Never guess - refer to this.

Response style:
- Match the user's language (Twi→Twi, English→English, mixed→mixed)
- Provide detailed, thorough explanations when users ask questions
- Include examples, context, and cultural background when relevant
- For language questions: explain meanings, pronunciation, and usage
- For cultural questions: give rich historical and social context
- Always be helpful and informative while maintaining a warm, friendly tone
- When teaching Twi, break down words and provide literal translations"""


@app.cls(
    image=image,
    gpu="A100",  # 40GB VRAM - plenty for 8B model
    timeout=600,
    container_idle_timeout=120,  # Keep warm for 2 mins
    memory=32768,  # 32GB RAM
)
class TwiAI:
    @modal.enter()
    def load_model(self):
        """Load model when container starts (already downloaded in image)"""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        print(f"Loading model from {MODEL_DIR}...")
        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        
        # Tokenizer is from base Llama model (user's was corrupted)
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_DIR,
            torch_dtype=torch.float16,
            device_map="auto",
        )
        
        print("Model loaded successfully!")

    def generate(
        self,
        prompt: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        """Generate a response"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        input_text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        inputs = self.tokenizer(
            input_text, return_tensors="pt", truncation=True, max_length=4096
        ).to(self.model.device)
        
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=temperature > 0,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        
        response = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True
        )
        
        return response

    @modal.web_endpoint(method="POST")
    def chat(self, data: dict) -> dict:
        """HTTP endpoint for chat"""
        try:
            prompt = data.get("prompt", "")
            system_prompt = data.get("system_prompt", DEFAULT_SYSTEM_PROMPT)
            max_tokens = data.get("max_tokens", 512)
            temperature = data.get("temperature", 0.7)
            
            if not prompt:
                return {"error": "No prompt provided"}
            
            # Inline generation logic
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            input_text = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            
            inputs = self.tokenizer(
                input_text, return_tensors="pt", truncation=True, max_length=4096
            ).to(self.model.device)
            
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
            
            response = self.tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:],
                skip_special_tokens=True
            )
            
            return {
                "response": response,
                "model": MODEL_ID,
            }
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}


# CLI for quick testing
@app.local_entrypoint()
def main(prompt: str = "Wo ho te sɛn?"):
    """Test the model locally"""
    twi = TwiAI()
    response = twi.generate.remote(prompt=prompt)
    print(f"Ama: {response}")
