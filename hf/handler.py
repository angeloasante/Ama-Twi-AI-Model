"""
Lightweight generation handler for HuggingFace Inference Endpoints.
Loads Qwen3.5-9B fine-tune and serves text generation.
All tool/agentic logic lives in the Next.js API route — this is pure generation.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


class EndpointHandler:
    def __init__(self, path: str = "/repository"):
        print(f"Loading model from {path} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            path, trust_remote_code=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        self.model.eval()
        print("Model loaded and ready.")

    def __call__(self, data: dict) -> dict:
        """
        Expected input:
        {
            "inputs": "user message",
            "parameters": {
                "system_prompt": "...",
                "max_new_tokens": 384,
                "temperature": 0.7,
                "top_p": 0.9,
                "repetition_penalty": 1.2
            }
        }
        """
        inputs = data.get("inputs", "")
        params = data.get("parameters", {})

        system_prompt = params.get("system_prompt", "You are Ama, a helpful bilingual Twi-English AI assistant.")
        max_new_tokens = min(params.get("max_new_tokens", 384), 2048)
        temperature = params.get("temperature", 0.7)
        top_p = params.get("top_p", 0.9)
        repetition_penalty = params.get("repetition_penalty", 1.2)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": inputs},
        ]

        # Apply chat template — disable thinking for Qwen3.5
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

        model_inputs = self.tokenizer(
            text, return_tensors="pt"
        ).to(self.model.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature if temperature > 0 else None,
                top_p=top_p if temperature > 0 else None,
                repetition_penalty=repetition_penalty,
                do_sample=temperature > 0,
            )

        # Decode only the new tokens
        new_tokens = output_ids[0][model_inputs["input_ids"].shape[1]:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        # Clean up stop tokens
        for tok in ["<|im_end|>", "<|endoftext|>", "</s>", "<s>", "<|eot_id|>"]:
            if tok in response:
                response = response[:response.index(tok)].strip()

        return {"generated_text": response}
