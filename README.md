# 🇬🇭 Twi AI - Ama

> **The first bilingual Twi-English AI agent with tools**

Created by **Angelo Asante**

---

## 🎯 What is Ama?

Ama is a fine-tuned AI assistant that speaks **Twi** (Ghana's most widely spoken language) and **English**. Built on Meta's Llama 3.1 8B model with an agentic tool system, Ama can:

- 💬 Have natural conversations in Twi and English
- 🔍 Search the web for current information
- 🌐 Fetch and analyze web pages
- 🖼️ Search for images
- 🕐 Tell time in any timezone worldwide
- 📁 Create, view, and manage files
- 📚 Access Akan cultural knowledge base
- 🔄 Translate between Twi and English

---

## 🚀 Quick Start - Agent API

Ama is available via **two endpoints** - choose based on your needs:

| Endpoint | Best For | Cold Start | Cost |
|----------|----------|------------|------|
| **HuggingFace** | Production, lower cost | ~30-60s | $0.80/hr (GPU time) |
| **Modal** | Development, testing | ~30-60s | ~$0.001-0.003/req |

### 🤗 HuggingFace Inference Endpoint (Recommended)
```
https://vs68t0qrfr3hsfp3.us-east-1.aws.endpoints.huggingface.cloud
```

### ⚡ Modal Endpoint (Alternative)
```
https://angeloasante--twi-ai-agent-v3-twiagent-agent.modal.run
```

### Health Check (Modal)
```
https://angeloasante--twi-ai-agent-v3-health.modal.run
```

---

## 📡 API Examples

### Basic Chat - HuggingFace (curl)
```bash
curl -X POST https://vs68t0qrfr3hsfp3.us-east-1.aws.endpoints.huggingface.cloud \
  -H "Authorization: Bearer YOUR_HF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inputs": "Wo ho te sɛn?"}'
```

### Basic Chat - Modal (curl)
```bash
curl -X POST https://angeloasante--twi-ai-agent-v3-twiagent-agent.modal.run \
  -H "Content-Type: application/json" \
  -d '{"message": "Wo ho te sɛn?"}'
```

### Python Example - HuggingFace (Recommended)
```python
import requests

HF_URL = "https://vs68t0qrfr3hsfp3.us-east-1.aws.endpoints.huggingface.cloud"
HF_TOKEN = "your_huggingface_token"  # Get from huggingface.co/settings/tokens

headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}

# Simple chat
response = requests.post(HF_URL, headers=headers, json={
    "inputs": "Hello, how are you?"
})
print(response.json()["response"])

# With timezone
response = requests.post(HF_URL, headers=headers, json={
    "inputs": "What time is it?",
    "parameters": {"timezone": "tokyo"}
})
data = response.json()
print(f"Response: {data['response']}")
print(f"Tools used: {data['tools_used']}")
print(f"Tool results: {data['tool_results']}")

# Web search (auto-triggered by keywords)
response = requests.post(HF_URL, headers=headers, json={
    "inputs": "Who is the president of Ghana in 2026?"
})
data = response.json()
print(f"Response: {data['response']}")
print(f"Search results: {data['tool_results'].get('web_search', {})}")
```

### Python Example - Modal (Alternative)
```python
import requests

MODAL_URL = "https://angeloasante--twi-ai-agent-v3-twiagent-agent.modal.run"

# Simple chat
response = requests.post(MODAL_URL, json={
    "message": "Hello, how are you?"
})
print(response.json()["response"])

# With timezone
response = requests.post(MODAL_URL, json={
    "message": "What time is it?",
    "timezone": "tokyo"
})
print(response.json())

# Explicit file creation
response = requests.post(MODAL_URL, json={
    "action": "create_file",
    "data": {
        "filename": "notes.txt",
        "content": "My notes here"
    }
})
print(response.json()["result"])
```

### JavaScript/TypeScript Example
```javascript
// HuggingFace Endpoint (Recommended)
const HF_URL = "https://vs68t0qrfr3hsfp3.us-east-1.aws.endpoints.huggingface.cloud";
const HF_TOKEN = "your_huggingface_token";

const response = await fetch(HF_URL, {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${HF_TOKEN}`,
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    inputs: "Show me images of Kente cloth",
    parameters: { timezone: "ghana" }
  })
});

const data = await response.json();
console.log(data.response);
console.log(data.tools_used);  // ["image_search", "knowledge_base"]
console.log(data.tool_results.image_search);  // Contains image URLs

// IMPORTANT: Use tool_results for accurate real-time data!
if (data.tool_results.web_search) {
  console.log("Search results:", data.tool_results.web_search.results);
}
```

---

## 📋 Agent API Reference

### HuggingFace Request Format
```json
{
  "inputs": "Your message here",
  "parameters": {
    "timezone": "new york",
    "action": "chat",
    "data": {}
  }
}
```

### Modal Request Format
```json
{
  "message": "Your message here",
  "timezone": "new york",
  "action": "chat",
  "data": {}
}
```

### Request Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message` | string | "" | The user's message (auto-detected intent) |
| `timezone` | string | "UTC" | Timezone for time queries (see supported list) |
| `action` | string | null | Explicit action: `create_file`, `list_files`, `view_file`, `search`, `image_search`, `fetch`, `time` |
| `data` | object | {} | Data for explicit actions |

### Response Format
```json
{
  "success": true,
  "response": "AI-generated response text",
  "tools_used": ["web_search", "knowledge_base"],
  "tool_results": {
    "web_search": {
      "query": "...",
      "results": "..."
    }
  },
  "timezone": "America/New_York"
}
```

### Explicit Action Response
```json
{
  "success": true,
  "action": "create_file",
  "result": {
    "success": true,
    "file_id": "abc12345",
    "filename": "notes.txt",
    "size": 100
  }
}
```

---

## 🛠️ Available Tools

### 1. Web Search
Automatically triggered for news, current events, and political queries.

```bash
# Auto-triggered
curl -X POST $API_URL \
  -d '{"message": "Who is the president of Brazil?"}'

# Explicit
curl -X POST $API_URL \
  -d '{"action": "search", "data": {"query": "latest tech news"}}'
```

**Trigger keywords:** news, latest, today, recent, current, president, government, election, parliament

### 2. Web Fetch
Extracts content from URLs. Auto-triggered when URL is detected in message.

```bash
# Auto-triggered
curl -X POST $API_URL \
  -d '{"message": "What does this page say? https://example.com"}'

# Explicit
curl -X POST $API_URL \
  -d '{"action": "fetch", "data": {"url": "https://example.com"}}'
```

### 3. Image Search
Returns image URLs from web search.

```bash
# Auto-triggered
curl -X POST $API_URL \
  -d '{"message": "Show me pictures of Adinkra symbols"}'

# Explicit
curl -X POST $API_URL \
  -d '{"action": "image_search", "data": {"query": "Kente cloth"}}'
```

**Trigger keywords:** image of, picture of, photo of, show me

### 4. Time & Date
Returns current time in any timezone with Akan day names.

```bash
# Auto-triggered
curl -X POST $API_URL \
  -d '{"message": "What time is it?", "timezone": "tokyo"}'

# Explicit
curl -X POST $API_URL \
  -d '{"action": "time"}'
```

**Trigger keywords:** time, date, what day

### 5. File Management
Create, list, and view files (ephemeral storage).

```bash
# Create file
curl -X POST $API_URL \
  -d '{"action": "create_file", "data": {"filename": "notes.txt", "content": "Hello!"}}'

# List files
curl -X POST $API_URL \
  -d '{"action": "list_files"}'

# View file
curl -X POST $API_URL \
  -d '{"action": "view_file", "data": {"file_id": "abc12345"}}'
```

### 6. Knowledge Base
Cultural facts about Twi, Akan, and Ghana. Auto-triggered for related queries.

**Topics covered:**
- Akan day names and naming conventions
- Twi greetings and phrases
- Akan proverbs with meanings
- Ghanaian history and culture

---

## 🌍 Supported Timezones

Use friendly names or standard timezone IDs:

| Alias | Timezone |
|-------|----------|
| ghana, accra | Africa/Accra |
| nigeria, lagos | Africa/Lagos |
| london, uk | Europe/London |
| new york, nyc, est | America/New_York |
| los angeles, la, pst | America/Los_Angeles |
| tokyo, japan | Asia/Tokyo |
| paris, france | Europe/Paris |
| berlin, germany | Europe/Berlin |
| dubai, uae | Asia/Dubai |
| india, mumbai | Asia/Kolkata |
| singapore | Asia/Singapore |
| sydney, australia | Australia/Sydney |
| china, beijing | Asia/Shanghai |
| hong kong | Asia/Hong_Kong |
| brazil | America/Sao_Paulo |
| south africa, johannesburg | Africa/Johannesburg |
| cairo, egypt | Africa/Cairo |
| kenya, nairobi | Africa/Nairobi |

Or use any valid IANA timezone like `Europe/Amsterdam`, `Asia/Seoul`, etc.

---

## 🏗️ Architecture

### Single Unified Endpoint
All functionality through one endpoint - the agent automatically detects intent and uses appropriate tools.

```
User Request → Intent Detection → Tool Execution → Context Injection → LLM Response
```

### Why Unified Endpoint?
| Multiple Endpoints | Unified Endpoint |
|-------------------|------------------|
| Client decides which endpoint | Agent decides what tools to use |
| Multiple integrations needed | Single integration |
| Manual tool orchestration | Automatic tool chaining |
| Separate error handling | Consistent response format |

---

## 🛠️ Deployment Guide

### Prerequisites
1. [Modal](https://modal.com) account (free tier available)
2. [HuggingFace](https://huggingface.co) account with access to Llama 3.1
3. [Tavily](https://tavily.com) API key for web search (free tier available)
4. Python 3.9+

### Step 1: Install Modal CLI
```bash
pip install modal
modal setup  # This opens browser to authenticate
```

### Step 2: Create Secrets
```bash
# HuggingFace token
modal secret create huggingface HF_TOKEN=hf_your_token_here

# Tavily API key (for web search)
modal secret create tavily TAVILY_API_KEY=tvly-your_key_here
```

### Step 3: Deploy
```bash
# Deploy the unified agent
modal deploy modal_agent_v3.py
```

This will output your endpoint URL:
```
✓ Created web endpoint for TwiAgent.agent => https://YOUR_USERNAME--twi-ai-agent-v3-twiagent-agent.modal.run
```

---

## 💰 Cost Comparison

### HuggingFace Inference Endpoint (Recommended for Production)
| Usage Pattern | Estimated Monthly Cost |
|--------------|------------------------|
| Light (100 requests/month, clustered) | **$1-5** |
| Medium (500 requests/month) | **$5-20** |
| Heavy (3000 requests/month) | **$20-50** |
| Always-on (min_replicas=1) | ~$576 |

*Billing: $0.80/hr for L4 GPU, only charged when running. Scale-to-zero after 1hr idle.*

### Modal (Good for Development)
| Service | Cost | Notes |
|---------|------|-------|
| Modal (A100 GPU) | ~$0.001-0.003/request | Pay per use |
| Cold start | ~30-60 seconds | First request after idle |
| Warm requests | ~1-3 seconds | While container is warm |
| Container idle | 5 min timeout | Then scales to 0 |

### External APIs (Both Endpoints)
| Service | Cost | Notes |
|---------|------|-------|
| Tavily API | Free tier: 1000/mo | Web search |

---

## 📊 Project Stats

| Metric | Value |
|--------|-------|
| **Training Data** | 20,000+ curated conversations |
| **Base Model** | meta-llama/Llama-3.1-8B-Instruct |
| **Fine-tuning Method** | LoRA (Low-Rank Adaptation) |
| **Languages** | Twi (Akan), English |
| **GPU** | NVIDIA A100 (40GB) |
| **Model Size** | ~16GB merged |
| **Agent Version** | v3 (Unified) |
| **Tools** | 7 (Web Search, Fetch, Images, Time, Files, Knowledge) |

---

## 💬 Example Conversations

| User | Ama | Tools Used |
|------|-----|------------|
| Wo ho te sɛn? | Me ho yɛ! Wo nso ɛ? | None |
| What time is it in Tokyo? | It's 2:30 PM, Ɛbenada (Tuesday) | time |
| Who is the president of Ghana? | John Dramani Mahama yɛ Ghana President | web_search |
| Show me images of Kente | Here are beautiful Kente images! | image_search, knowledge_base |
| Translate "I love you" to Twi | "Me dɔ wo" | None |

---

## 🏗️ Project Structure

```
twi-ai/
├── modal_agent_v3.py         # Unified agent deployment (MAIN FILE!)
├── modal_agent_v2.py         # Previous version (deprecated)
├── modal_agent_deploy.py     # Original agent (deprecated)
├── modal_deploy.py           # Simple chat API (deprecated)
├── README.md                 # This file
├── AGENT_DOCS.md             # Detailed agent documentation
├── train_twi_llama.py        # Training script
├── train_h100.py             # H100 training variant
├── checkpoints/              # Model checkpoints
│   └── checkpoint-10000/     # Latest checkpoint
├── twi-dataset/              # Training data
│   ├── conversations.jsonl   # Training conversations
│   └── conversations_val.jsonl # Validation set
└── twi-voice*/               # Voice data (future TTS)
```

---

## 🔧 Local Development

### Run Model Locally (requires GPU)
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model = AutoModelForCausalLM.from_pretrained(
    "travis-moore/twi-llama-v5",
    torch_dtype=torch.float16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("travis-moore/twi-llama-v5")

messages = [
    {"role": "system", "content": "You are Ama, a helpful Twi AI assistant."},
    {"role": "user", "content": "Wo ho te sɛn?"}
]
prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=100)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

### Test Deployed Agent API
```bash
# Simple chat
curl -X POST https://angeloasante--twi-ai-agent-v3-twiagent-agent.modal.run \
  -H "Content-Type: application/json" \
  -d '{"message": "Akwaaba!"}'

# With tools
curl -X POST https://angeloasante--twi-ai-agent-v3-twiagent-agent.modal.run \
  -H "Content-Type: application/json" \
  -d '{"message": "What time is it in London?", "timezone": "london"}'

# Health check
curl https://angeloasante--twi-ai-agent-v3-health.modal.run
```

---

## 📁 Training Data Topics

21 categories covering:

| Topics |
|--------|
| Greetings & Pleasantries, Culture & Traditions, Identity (Who is Ama?) |
| Code-switching, Family & Relationships, Travel & Directions |
| Shopping & Money, Health & Wellness, Weather & Seasons |
| Sports & Football, Education & Learning, Politics & Government |
| Work & Career, Music & Entertainment, Technology & Phones |
| Religion & Spirituality, Compliments & Encouragement |
| Animals & Nature, Numbers & Counting, Home & Daily Life |
| General Intelligence, Current Events, Translations |

---

## 🔗 Links

### Endpoints
- **HuggingFace (Production):** `https://vs68t0qrfr3hsfp3.us-east-1.aws.endpoints.huggingface.cloud`
- **Modal (Development):** `https://angeloasante--twi-ai-agent-v3-twiagent-agent.modal.run`
- **Health Check:** `https://angeloasante--twi-ai-agent-v3-health.modal.run`

### Resources
- **Model:** [huggingface.co/travis-moore/twi-llama-v5](https://huggingface.co/travis-moore/twi-llama-v5)
- **HuggingFace Endpoints:** [ui.endpoints.huggingface.co](https://ui.endpoints.huggingface.co)
- **Modal Dashboard:** [modal.com](https://modal.com)
- **Creator:** Angelo Asante

---

## 🙏 Acknowledgments

- Meta AI for Llama 3.1
- Modal for serverless GPU infrastructure
- Hugging Face for model hosting
- Tavily for web search API
- The Twi-speaking community of Ghana

---

## 📜 License

This project uses the Llama 3.1 Community License. See [Meta's license](https://llama.meta.com/llama3_1/license/) for details.

---

## 🚧 Future Plans

- [x] ~~Web search integration~~ ✅ Done
- [x] ~~Image search~~ ✅ Done
- [x] ~~Global timezone support~~ ✅ Done
- [x] ~~File management~~ ✅ Done
- [x] ~~Unified agent endpoint~~ ✅ Done
- [ ] Twi Text-to-Speech (TTS) integration
- [ ] Mobile app
- [ ] Persistent file storage
- [ ] More Ghanaian languages (Ga, Ewe, Fante)
- [ ] Voice assistant capabilities
- [ ] API key authentication
- [ ] Conversation memory/history

---

**Made with ❤️ for Ghana 🇬🇭**
