# Quick Start: Deploy to Replicate

## One-Time Setup Cost: ~$1

You need a machine with Docker + NVIDIA GPU to build. Cheapest option: **RunPod**

### Step 1: Create Replicate Account

1. Go to [replicate.com](https://replicate.com) and sign up
2. Go to [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens)
3. Copy your API token (starts with `r8_`)

### Step 2: Create Model Page

1. Go to [replicate.com/create](https://replicate.com/create)
2. **Owner**: your-username
3. **Name**: twi-llama-v5  
4. **Visibility**: Public
5. **Hardware**: Nvidia A40 (Large) - recommended for 8B model
6. Click "Create model"

### Step 3: Deploy from RunPod (~$0.50-1.00)

1. Go to [runpod.io](https://runpod.io)
2. Deploy a GPU pod:
   - Template: **RunPod Pytorch** (has Docker)
   - GPU: Any (A40, RTX 4090, etc.)
   - ~$0.30-0.50/hr
3. Connect via terminal and run:

```bash
# Upload the replicate/ folder from your local machine, then:
cd replicate

# Set your token
export REPLICATE_API_TOKEN="r8_your_token_here"

# Push to Replicate
bash push_to_replicate.sh
```

**To upload files to RunPod:**
- Use the "Upload" button in RunPod's file browser, OR
- Use `scp` from your local terminal:
  ```bash
  scp -r "/Users/travismoore/Desktop/twi ai/replicate" root@YOUR_POD_IP:/workspace/
  ```

4. Wait 30-60 minutes for build
5. **Stop the pod** when done to save money!

### Step 4: Test It!

```bash
pip install replicate
export REPLICATE_API_TOKEN="r8_your_token_here"

python -c "
import replicate
for event in replicate.stream('your-username/twi-llama-v5', input={'prompt': 'Wo ho te sɛn?'}):
    print(event, end='')
"
```

## That's It!

Your model is now available via API at ~$0.001/request. No monthly fees!

## Alternative: Use Existing Llama 3.1 on Replicate

If you just want to test the concept quickly, you can use Replicate's existing Llama models and add your system prompt:

```python
import replicate

SYSTEM = """You are Ama, a bilingual Twi-English AI assistant created by Angelo Asante..."""

output = replicate.run(
    "meta/meta-llama-3.1-8b-instruct",  # Official Llama on Replicate
    input={
        "prompt": "Wo ho te sɛn?",
        "system_prompt": SYSTEM,
        "max_tokens": 256
    }
)
print(output)
```

This won't have your fine-tuning, but lets you test the API flow first.
