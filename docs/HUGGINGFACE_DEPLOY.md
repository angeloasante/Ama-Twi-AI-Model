# Twi AI (Ama) - HuggingFace Deployment Guide

## Quick Start

### 1. Get HuggingFace Token
- Go to https://huggingface.co/settings/tokens
- Create new token with **Write** permissions
- Copy the token (starts with `hf_...`)

### 2. Push Model to Hub
Run in Colab:
```python
# Install
!pip install huggingface_hub

# Login
from huggingface_hub import login
login(token="YOUR_HF_TOKEN")

# Upload LoRA adapter
from huggingface_hub import upload_folder

upload_folder(
    folder_path="/content/drive/MyDrive/twi-ai/twi-llama-v5-prev/final",
    repo_id="travis-moore/twi-llama-v5",
    repo_type="model",
)
```

---

## FREE API Options (Budget-Friendly!)

### Option A: Free Inference API ⭐ RECOMMENDED
After pushing to Hub, you automatically get a FREE API!

**Endpoint:** `https://api-inference.huggingface.co/models/travis-moore/twi-llama-v5`

**Usage:**
```python
import requests

API_URL = "https://api-inference.huggingface.co/models/travis-moore/twi-llama-v5"
headers = {"Authorization": "Bearer YOUR_HF_TOKEN"}

def query(payload):
    response = requests.post(API_URL, headers=headers, json=payload)
    return response.json()

output = query({
    "inputs": "Wo ho te sɛn?",
})
print(output)
```

**What you get FREE:**
- ✅ Unlimited requests (with rate limiting)
- ✅ Auto-scaling
- ✅ No setup needed
- ⚠️ Cold starts (30-60 sec first request)
- ⚠️ Queue during high traffic

---

### Option B: Gradio Space with ZeroGPU ⭐ FREE DEMO
Create a web chat interface with FREE GPU!

1. Go to https://huggingface.co/spaces
2. Create new Space → Select "Gradio" → Select **ZeroGPU** (free tier)
3. Add this `app.py`:

```python
import gradio as gr
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import spaces

# Load model at startup
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
ADAPTER = "travis-moore/twi-llama-v5"

tokenizer = AutoTokenizer.from_pretrained(ADAPTER)

@spaces.GPU  # Gets free GPU when needed!
def chat(message, history):
    # Load model with GPU
    base = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.float16, device_map="auto"
    )
    model = PeftModel.from_pretrained(base, ADAPTER)
    
    messages = [{"role": "system", "content": "You are Ama, a helpful Twi AI assistant."}]
    for h in history:
        messages.append({"role": "user", "content": h[0]})
        messages.append({"role": "assistant", "content": h[1]})
    messages.append({"role": "user", "content": message})
    
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    outputs = model.generate(**inputs, max_new_tokens=100, temperature=0.7, do_sample=True)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response.split("assistant")[-1].strip()

demo = gr.ChatInterface(
    chat,
    title="🇬🇭 Ama - Twi AI Assistant",
    description="Chat in Twi and English! Created by Angelo Asante",
    examples=["Wo ho te sɛn?", "What is your name?", "Who created you?"]
)
demo.launch()
```

**URL:** `https://huggingface.co/spaces/travis-moore/twi-ai-ama`

---

### Option C: Replicate (Pay Per Second) 💰 CHEAP
Only pay when API is called. ~$0.001/second of GPU time.

1. Go to https://replicate.com
2. Click "Create a model"
3. Import from HuggingFace: `travis-moore/twi-llama-v5`
4. Get your API token

**Cost:** ~$0.0005 per request (half a cent!)
- 1,000 requests = ~$0.50
- 10,000 requests = ~$5

---

## Cost Comparison

| Option | Cost | Best For |
|--------|------|----------|
| **Free Inference API** | $0 | Testing, low traffic apps |
| **Gradio + ZeroGPU** | $0 | Demo website |
| **Replicate** | ~$0.001/req | Production, pay-per-use |
| **Modal** | ~$0.001/req | Production, pay-per-use |
| Inference Endpoints | $430+/mo | High traffic (skip this!) |

---

## Recommended Path for Budget

1. **Push to Hub** → Get FREE API instantly
2. **Create Gradio Space** → Get FREE demo website
3. **If you need production API** → Use Replicate (pay per request)

---

## Quick Test Commands

**Test free API:**
```bash
curl https://api-inference.huggingface.co/models/travis-moore/twi-llama-v5 \
  -X POST \
  -H "Authorization: Bearer YOUR_HF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inputs": "Wo ho te sɛn?"}'
```
