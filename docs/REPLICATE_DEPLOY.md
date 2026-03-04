# Deploying Twi AI to Replicate

Deploy your fine-tuned model to Replicate for cheap, pay-per-use API access.

## Cost Estimate
- **~$0.001-0.003 per request** (varies with response length)
- No minimum, no monthly fees - only pay when you use it
- Uses A40/A100 GPUs on-demand

## Prerequisites

1. **Replicate account**: Sign up at [replicate.com](https://replicate.com)
2. **API Token**: Get your token at [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens)
3. **Model on HuggingFace**: Your model at `travis-moore/twi-llama-v5`

## Quick Start (Using Colab)

The easiest way to push to Replicate is using Google Colab with a GPU runtime:

1. Open `notebooks/push_to_replicate.ipynb` in Colab
2. Set your `REPLICATE_API_TOKEN`
3. Run all cells
4. Your model will be available at: `https://replicate.com/travis-moore/twi-llama-v5`

## Manual Setup

### Step 1: Create Model on Replicate

1. Go to [replicate.com/create](https://replicate.com/create)
2. Fill in:
   - **Owner**: travis-moore (your username)
   - **Model name**: twi-llama-v5
   - **Visibility**: Public (or Private)
   - **Hardware**: GPU (A40 Large recommended for 8B model)
3. Click "Create model"

### Step 2: Install Cog

On a machine with a GPU:

```bash
sudo curl -o /usr/local/bin/cog -L "https://github.com/replicate/cog/releases/latest/download/cog_$(uname -s)_$(uname -m)"
sudo chmod +x /usr/local/bin/cog
```

### Step 3: Create Project Files

Create a directory with these files:

**cog.yaml**:
```yaml
build:
  gpu: true
  cuda: "12.1"
  python_version: "3.11"
  python_packages:
    - "torch==2.1.2"
    - "transformers==4.40.0"
    - "accelerate==0.27.2"
    - "huggingface_hub>=0.20.0"
    - "sentencepiece>=0.1.99"
    - "protobuf>=3.20.0"
  run:
    - pip install flash-attn --no-build-isolation

predict: "predict.py:Predictor"
```

**predict.py** - See `replicate/predict.py` in this repo.

### Step 4: Push to Replicate

```bash
# Login
cog login

# Push (this will take a while - downloads model + builds container)
cog push r8.im/travis-moore/twi-llama-v5
```

## Using Your Deployed Model

### Python Client

```python
import replicate

output = replicate.run(
    "travis-moore/twi-llama-v5",
    input={
        "prompt": "Wo ho te sɛn?",
        "system_prompt": "You are Ama, a bilingual AI assistant...",
        "max_tokens": 256,
        "temperature": 0.7
    }
)
print(output)
```

### cURL/HTTP API

```bash
curl -X POST https://api.replicate.com/v1/predictions \
  -H "Authorization: Bearer $REPLICATE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "YOUR_VERSION_ID",
    "input": {
      "prompt": "Wo ho te sɛn?",
      "system_prompt": "You are Ama...",
      "max_tokens": 256
    }
  }'
```

### JavaScript/Node.js

```javascript
import Replicate from "replicate";

const replicate = new Replicate({
  auth: process.env.REPLICATE_API_TOKEN,
});

const output = await replicate.run(
  "travis-moore/twi-llama-v5",
  {
    input: {
      prompt: "Wo ho te sɛn?",
      system_prompt: "You are Ama...",
      max_tokens: 256
    }
  }
);
console.log(output);
```

## Hardware Options

| Hardware | Cost/sec | Best For |
|----------|----------|----------|
| Nvidia T4 | ~$0.000225 | Small models (<7B) |
| Nvidia A40 | ~$0.000725 | Medium models (7B-13B) ✓ |
| Nvidia A40 Large | ~$0.00145 | Large models (13B+) |
| Nvidia A100 40GB | ~$0.0023 | Very large models |

For Llama 3.1 8B, **A40** should work well.

## Streaming Responses

Replicate supports streaming for real-time output:

```python
import replicate

for event in replicate.stream(
    "travis-moore/twi-llama-v5",
    input={"prompt": "Tell me about Twi language"}
):
    print(str(event), end="")
```

## Troubleshooting

### Push is slow
The first push downloads your model (~16GB) and builds a Docker container. Subsequent pushes are faster.

### Out of memory
Increase to A40 Large or A100 hardware in your model settings.

### Model not loading
Ensure your HuggingFace model is public or provide `HF_TOKEN` as a secret in Replicate model settings.

## Resources

- [Replicate Docs](https://replicate.com/docs)
- [Cog GitHub](https://github.com/replicate/cog)
- [Replicate Python Client](https://github.com/replicate/replicate-python)
