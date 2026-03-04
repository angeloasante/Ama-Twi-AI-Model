# Twi AI Agent - Technical Documentation

> Detailed documentation on the agent architecture, tools, and implementation.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tool Implementation](#tool-implementation)
3. [Intent Detection System](#intent-detection-system)
4. [API Specification](#api-specification)
5. [Adding New Tools](#adding-new-tools)
6. [Configuration](#configuration)
7. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Design Philosophy

The Twi AI Agent v3 uses a **unified endpoint architecture** where all functionality is accessed through a single API endpoint. The agent automatically detects user intent and orchestrates the appropriate tools.

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Request                             │
│           {"message": "What time is it in Tokyo?"}              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Intent Detection                            │
│  • Keyword matching (TIME_KEYWORDS: "time", "date", "what day") │
│  • URL detection (regex for http/https)                         │
│  • Explicit action parameter check                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Tool Execution                               │
│  • get_current_time("tokyo") → resolves to Asia/Tokyo           │
│  • Returns formatted time with Akan day name                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Context Injection                             │
│  • Tool results added to prompt context                         │
│  • Model generates response using context                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Response                                 │
│  {                                                              │
│    "success": true,                                             │
│    "response": "It's 2:30 PM in Tokyo...",                      │
│    "tools_used": ["time"],                                      │
│    "tool_results": {"time": "..."},                             │
│    "timezone": "Asia/Tokyo"                                     │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
modal_agent_v3.py
├── Configuration
│   ├── MODEL_ID = "travis-moore/twi-llama-v5"
│   ├── GPU_CONFIG = "A100-40GB"
│   └── SYSTEM_PROMPT
│
├── Keyword Definitions
│   ├── NEWS_KEYWORDS
│   ├── POLITICAL_KEYWORDS
│   ├── TIME_KEYWORDS
│   ├── IMAGE_KEYWORDS
│   ├── FILE_CREATE_KEYWORDS
│   ├── FILE_LIST_KEYWORDS
│   └── FILE_VIEW_KEYWORDS
│
├── Timezone Aliases
│   └── TIMEZONE_ALIASES (30+ friendly names)
│
├── Tool Functions
│   ├── web_search(query, max_results)
│   ├── web_fetch(url)
│   ├── image_search(query, max_results)
│   ├── get_current_time(timezone)
│   ├── create_file(filename, content)
│   ├── view_file(file_id)
│   ├── list_files()
│   └── search_knowledge_base(query)
│
├── Intent Detection
│   └── detect_intent(message) → dict
│
├── Agent Class
│   ├── load_model() - @modal.enter()
│   ├── generate_response(prompt, context)
│   └── agent(request) - @modal.fastapi_endpoint
│
└── Health Endpoint
    └── health() - @modal.fastapi_endpoint(GET)
```

---

## Tool Implementation

### 1. Web Search (`web_search`)

**Purpose:** Search the web for current information using Tavily API.

**Implementation:**
```python
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily API."""
    import httpx
    
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return "Web search unavailable (no API key configured)"
    
    response = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": tavily_key,
            "query": query,
            "max_results": max_results,
            "include_answer": True,
        },
        timeout=30.0
    )
    
    # Parse and format results
    data = response.json()
    results = []
    
    if data.get("answer"):
        results.append(f"**Summary:** {data['answer']}\n")
    
    for i, result in enumerate(data.get("results", [])[:max_results], 1):
        title = result.get("title", "No title")
        url = result.get("url", "")
        content = result.get("content", "")[:300]
        results.append(f"{i}. **{title}**\n   {content}\n   Source: {url}\n")
    
    return "\n".join(results) if results else "No results found"
```

**Auto-trigger keywords:**
- `NEWS_KEYWORDS`: "news", "latest", "today", "recent", "current", "happening", "2024", "2025", "2026"
- `POLITICAL_KEYWORDS`: "president", "vice president", "government", "minister", "election", "parliament", "prime minister", "congress", "senate"

**Dependencies:**
- `httpx` for HTTP requests
- Tavily API key (stored in Modal secret `tavily`)

---

### 2. Web Fetch (`web_fetch`)

**Purpose:** Extract readable content from web pages.

**Implementation:**
```python
def web_fetch(url: str) -> str:
    """Fetch and extract content from a web page."""
    import httpx
    from bs4 import BeautifulSoup
    
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TwiAI/1.0)"}
    response = httpx.get(url, headers=headers, timeout=30.0, follow_redirects=True)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        
        # Remove non-content elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        
        # Extract text
        text = soup.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        content = "\n".join(lines[:100])  # Limit to ~100 lines
        
        return f"**Content from {url}:**\n\n{content[:4000]}"
    else:
        return f"Failed to fetch URL: HTTP {response.status_code}"
```

**Auto-trigger:** URL regex detection (`https?://[^\s]+`)

**Dependencies:**
- `httpx` for HTTP requests
- `beautifulsoup4` for HTML parsing
- `lxml` for fast XML/HTML parsing

---

### 3. Image Search (`image_search`)

**Purpose:** Find images related to a query.

**Implementation:**
```python
def image_search(query: str, max_results: int = 5) -> str:
    """Search for images using Tavily."""
    import httpx
    
    tavily_key = os.environ.get("TAVILY_API_KEY")
    
    response = httpx.post(
        "https://api.tavily.com/search",
        json={
            "api_key": tavily_key,
            "query": f"{query} images",
            "max_results": max_results,
            "include_images": True,
        },
        timeout=30.0
    )
    
    data = response.json()
    images = data.get("images", [])
    
    if images:
        results = [f"**Image results for '{query}':**\n"]
        for i, img_url in enumerate(images[:max_results], 1):
            results.append(f"{i}. {img_url}")
        return "\n".join(results)
    else:
        return f"No images found for '{query}'"
```

**Auto-trigger keywords:**
- `IMAGE_KEYWORDS`: "image of", "picture of", "photo of", "show me", "images of", "pictures of"

---

### 4. Current Time (`get_current_time`)

**Purpose:** Get current date/time in any timezone with Akan day names.

**Implementation:**
```python
def get_current_time(timezone: str = "UTC") -> str:
    """Get current date and time in specified timezone."""
    import pytz
    
    resolved_tz = resolve_timezone(timezone)
    tz = pytz.timezone(resolved_tz)
    now = datetime.now(tz)
    
    # Akan day names
    akan_days = {
        0: "Ɛdwoada (Monday)",
        1: "Ɛbenada (Tuesday)", 
        2: "Wukuada (Wednesday)",
        3: "Yawoada (Thursday)",
        4: "Efiada (Friday)",
        5: "Memeneda (Saturday)",
        6: "Kwasiada (Sunday)",
    }
    
    akan_day = akan_days.get(now.weekday(), "")
    
    return (
        f"**Current Date & Time ({resolved_tz}):**\n"
        f"- Date: {now.strftime('%A, %B %d, %Y')}\n"
        f"- Twi Day: {akan_day}\n"
        f"- Time: {now.strftime('%I:%M %p')}"
    )
```

**Timezone Resolution:**
```python
TIMEZONE_ALIASES = {
    "ghana": "Africa/Accra",
    "accra": "Africa/Accra",
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "tokyo": "Asia/Tokyo",
    "london": "Europe/London",
    # ... 30+ aliases
}

def resolve_timezone(tz_input: str) -> str:
    """Resolve timezone from alias or direct name."""
    tz_lower = tz_input.lower().strip()
    
    # Check aliases first
    if tz_lower in TIMEZONE_ALIASES:
        return TIMEZONE_ALIASES[tz_lower]
    
    # Try direct timezone name
    try:
        pytz.timezone(tz_input)
        return tz_input
    except:
        return "UTC"
```

**Auto-trigger keywords:**
- `TIME_KEYWORDS`: "time", "date", "what day", "what's the time", "current time"

**Dependencies:**
- `pytz` for timezone handling

---

### 5. File Management

**Purpose:** Create, store, list, and retrieve files.

**Storage:** In-memory dictionary (ephemeral - lost on container restart)

```python
FILES_STORAGE = {}  # Global storage

def create_file(filename: str, content: str) -> dict:
    """Create a file with given content."""
    file_id = str(uuid.uuid4())[:8]
    
    FILES_STORAGE[file_id] = {
        "filename": filename,
        "content": content,
        "created_at": datetime.utcnow().isoformat(),
        "size": len(content)
    }
    
    return {
        "success": True,
        "file_id": file_id,
        "filename": filename,
        "size": len(content),
        "message": f"File '{filename}' created successfully with ID: {file_id}"
    }

def view_file(file_id: str) -> dict:
    """View contents of a file by ID."""
    if file_id in FILES_STORAGE:
        file_data = FILES_STORAGE[file_id]
        return {
            "success": True,
            "filename": file_data["filename"],
            "content": file_data["content"],
            "created_at": file_data["created_at"]
        }
    else:
        return {"success": False, "error": f"File with ID '{file_id}' not found"}

def list_files() -> dict:
    """List all created files."""
    if not FILES_STORAGE:
        return {"success": True, "files": [], "message": "No files have been created yet."}
    
    files_list = []
    for file_id, data in FILES_STORAGE.items():
        files_list.append({
            "id": file_id,
            "filename": data["filename"],
            "size": data["size"],
            "created_at": data["created_at"]
        })
    
    return {"success": True, "files": files_list, "count": len(files_list)}
```

**Auto-trigger keywords:**
- `FILE_CREATE_KEYWORDS`: "create a file", "make a file", "write a file", "save to file"
- `FILE_LIST_KEYWORDS`: "list files", "show files", "my files", "what files"
- `FILE_VIEW_KEYWORDS`: "view file", "read file", "show file", "open file", "get file"

---

### 6. Knowledge Base (`search_knowledge_base`)

**Purpose:** Provide instant answers about Twi/Akan culture without web search.

**Implementation:**
```python
KNOWLEDGE_BASE = {
    "akan_names": "In Akan culture, children are named based on the day they were born...",
    "akan_proverbs": "Some Akan proverbs: 'Obi nkyerɛ abɔfra Nyame'...",
    "twi_greetings": "Common Twi greetings: Maakye (Good morning)...",
    "akan_culture": "The Akan people are the largest ethnic group in Ghana...",
    "ghana_general": "Ghana, officially the Republic of Ghana, is a West African country...",
}

def search_knowledge_base(query: str) -> str:
    """Search internal knowledge base."""
    query_lower = query.lower()
    results = []
    
    for key, value in KNOWLEDGE_BASE.items():
        # Match if query words appear in key or value
        if any(word in query_lower for word in key.split("_")) or \
           any(word in value.lower() for word in query_lower.split()):
            results.append(f"**{key.replace('_', ' ').title()}:**\n{value}")
    
    return "\n\n".join(results) if results else ""
```

**Auto-trigger keywords:**
- `twi_keywords`: "twi", "akan", "ghana", "ashanti", "kente", "adinkra", "akwaaba"

---

## Intent Detection System

The `detect_intent` function analyzes user messages to determine which tools should be invoked.

```python
def detect_intent(message: str) -> dict:
    """Detect user intent and required tools from message."""
    message_lower = message.lower()
    intent = {
        "needs_web_search": False,
        "needs_web_fetch": False,
        "needs_image_search": False,
        "needs_time": False,
        "needs_file_create": False,
        "needs_file_list": False,
        "needs_file_view": False,
        "needs_knowledge": False,
        "search_query": None,
        "url_to_fetch": None,
        "image_query": None,
        "file_id": None,
    }
    
    # URL detection
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, message)
    if urls:
        intent["needs_web_fetch"] = True
        intent["url_to_fetch"] = urls[0]
    
    # Keyword matching
    if any(kw in message_lower for kw in NEWS_KEYWORDS + POLITICAL_KEYWORDS):
        intent["needs_web_search"] = True
        intent["search_query"] = message
    
    if any(kw in message_lower for kw in TIME_KEYWORDS):
        intent["needs_time"] = True
    
    # ... more keyword checks
    
    return intent
```

### Intent Priority

When multiple tools are detected, they all execute and their results are combined:

1. **Web Fetch** - If URL detected
2. **Web Search** - If news/political keywords
3. **Time** - If time keywords
4. **Image Search** - If image keywords  
5. **File Operations** - If file keywords
6. **Knowledge Base** - If culture keywords

---

## API Specification

### Endpoints

Twi AI is available via two deployment options:

| Endpoint | URL | Best For |
|----------|-----|----------|
| **HuggingFace** (Recommended) | `https://vs68t0qrfr3hsfp3.us-east-1.aws.endpoints.huggingface.cloud` | Production, lower cost |
| **Modal** | `https://angeloasante--twi-ai-agent-v3-twiagent-agent.modal.run` | Development, testing |

### HuggingFace Request Schema

```json
{
  "inputs": "string (the user message)",
  "parameters": {
    "timezone": "string (optional, default: UTC)",
    "action": "string (optional, for explicit actions)",
    "data": {
      "filename": "string",
      "content": "string",
      "file_id": "string",
      "query": "string",
      "url": "string"
    }
  }
}
```

**Required Header:** `Authorization: Bearer YOUR_HF_TOKEN`

### Modal Request Schema

```json
{
  "message": "string (required for auto-detection)",
  "timezone": "string (optional, default: UTC)",
  "action": "string (optional, for explicit actions)",
  "data": {
    "filename": "string",
    "content": "string", 
    "file_id": "string",
    "query": "string",
    "url": "string"
  }
}
```

### Explicit Actions

| Action | Required Data | Description |
|--------|---------------|-------------|
| `create_file` | `filename`, `content` | Create a new file |
| `list_files` | - | List all files |
| `view_file` | `file_id` | View file contents |
| `search` | `query` | Web search |
| `image_search` | `query` | Image search |
| `fetch` | `url` | Fetch web page |
| `time` | - | Get current time |

### Response Schema

**Chat Response:**
```json
{
  "success": true,
  "response": "AI-generated response",
  "tools_used": ["web_search", "knowledge_base"],
  "tool_results": {
    "web_search": {
      "query": "...",
      "results": "..."
    },
    "knowledge_base": "..."
  },
  "timezone": "UTC"
}
```

**Explicit Action Response:**
```json
{
  "success": true,
  "action": "create_file",
  "result": {
    "success": true,
    "file_id": "abc12345",
    "filename": "notes.txt",
    "size": 100,
    "message": "File created successfully"
  }
}
```

---

## Adding New Tools

### Step 1: Create Tool Function

```python
def my_new_tool(param1: str, param2: int = 10) -> str:
    """
    Description of what the tool does.
    
    Args:
        param1: Description
        param2: Description
        
    Returns:
        Formatted string result
    """
    # Implementation
    result = do_something(param1, param2)
    return f"**Result:**\n{result}"
```

### Step 2: Add Trigger Keywords

```python
MY_TOOL_KEYWORDS = ["keyword1", "keyword2", "trigger phrase"]
```

### Step 3: Update Intent Detection

```python
def detect_intent(message: str) -> dict:
    intent = {
        # ... existing intents
        "needs_my_tool": False,
        "my_tool_param": None,
    }
    
    # Add detection logic
    if any(kw in message_lower for kw in MY_TOOL_KEYWORDS):
        intent["needs_my_tool"] = True
        intent["my_tool_param"] = extract_param(message)
    
    return intent
```

### Step 4: Execute Tool in Agent

```python
# In TwiAgent.agent():
if intent["needs_my_tool"]:
    tool_result = my_new_tool(intent["my_tool_param"])
    context_parts.append(f"**My Tool Results:**\n{tool_result}")
    tools_used.append("my_tool")
    tool_results["my_tool"] = tool_result
```

### Step 5: Add Explicit Action (Optional)

```python
# In TwiAgent.agent():
if explicit_action == "my_tool":
    result = my_new_tool(data.get("param1", ""), data.get("param2", 10))
    return {"success": True, "action": "my_tool", "result": result}
```

---

## Configuration

### HuggingFace Inference Endpoint Configuration

| Setting | Value |
|---------|-------|
| **Endpoint URL** | `https://vs68t0qrfr3hsfp3.us-east-1.aws.endpoints.huggingface.cloud` |
| **Model** | `travis-moore/twi-llama-v5` |
| **GPU** | Nvidia L4 (24GB) |
| **Region** | AWS us-east-1 |
| **Scale-to-zero** | After 1 hour idle |
| **Cost** | $0.80/hour while running |

**Environment Variables (HuggingFace):**
| Variable | Description |
|----------|-------------|
| `TAVILY_API_KEY` | Tavily web search API key |

### Modal Configuration

**Environment Variables (Modal Secrets):**

| Secret Name | Variable | Description |
|-------------|----------|-------------|
| `huggingface` | `HF_TOKEN` | HuggingFace API token |
| `tavily` | `TAVILY_API_KEY` | Tavily web search API key |

### Model Configuration

```python
MODEL_ID = "travis-moore/twi-llama-v5"  # HuggingFace model
GPU_CONFIG = "A100-40GB"  # Modal GPU type (L4 for HuggingFace)
```

### Container Settings

```python
@app.cls(
    gpu="A100-40GB",
    image=image,
    secrets=[
        modal.Secret.from_name("huggingface"),
        modal.Secret.from_name("tavily"),
    ],
    timeout=600,  # 10 minutes max request time
    scaledown_window=300,  # 5 minutes idle before scale down
)
```

### System Prompt

The system prompt defines Ama's personality and capabilities:

```python
SYSTEM_PROMPT = """You are Ama (Twi AI), a bilingual AI assistant fluent in both Twi and English.

LANGUAGE RULES:
- If the user writes in Twi, respond primarily in Twi with English translations in parentheses
- If the user writes in English, respond in English but include relevant Twi phrases

CAPABILITIES:
- Answer questions on any topic
- Search the web for current information
- Fetch and analyze web pages
- Search for images
- Tell the current time in any timezone
- Create, view, and manage files
- Provide knowledge about Twi language and Akan culture

AKAN DAY NAMES:
- Sunday = Kwasiada, Monday = Ɛdwoada, Tuesday = Ɛbenada
- Wednesday = Wukuada, Thursday = Yawoada, Friday = Efiada, Saturday = Memeneda
"""
```

---

## Troubleshooting

### Common Issues

**1. Cold Start Timeout**
- First request after idle takes 30-60 seconds
- Solution: Send a health check request to warm up the container

**2. Web Search Not Working**
- Check `TAVILY_API_KEY` is configured in Modal secrets
- Verify Tavily API quota hasn't been exceeded

**3. Files Not Persisting**
- Files are stored in-memory and lost on container restart
- For persistent storage, implement Modal Volume or external storage

**4. Timezone Not Recognized**
- Use friendly names from `TIMEZONE_ALIASES` or valid IANA timezone IDs
- Unknown timezones default to UTC

**5. Model Loading Errors**
- Ensure `HF_TOKEN` has access to the model
- Check HuggingFace model exists and is accessible

### Debugging

```bash
# Check health
curl https://angeloasante--twi-ai-agent-v3-health.modal.run

# Test with minimal request
curl -X POST https://angeloasante--twi-ai-agent-v3-twiagent-agent.modal.run \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# Check Modal logs
modal app logs twi-ai-agent-v3
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1 | 2026-03-04 | Basic chat API |
| v2 | 2026-03-04 | Added tools (5 endpoints) |
| v3 | 2026-03-04 | Unified endpoint, global timezone, tool_results |

---

**Last Updated:** March 4, 2026
