"""
Twi AI Agent v2 - Ama with Full Tool Suite
Features:
- Web Search (Tavily)
- Web Fetch (full page content)
- Image Search
- Current Time & Date
- File Creation/View/List
- Knowledge Base (RAG)

Deploy:
    modal deploy modal_agent_v2.py

Endpoints:
    Agent: https://YOUR_USERNAME--twi-ai-agent-v2-twiagent-chat.modal.run
"""

import modal
import os
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

MODEL_ID = "travis-moore/twi-llama-v5"
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
MODEL_DIR = "/model"
FILES_DIR = "/tmp/ama_files"  # Ephemeral file storage

# ============================================================================
# KNOWLEDGE BASE - Embedded facts for RAG
# ============================================================================
KNOWLEDGE_BASE = {
    "akan_day_names": """
AKAN DAY NAMING SYSTEM:
| Day       | Male Name | Female Name |
|-----------|-----------|-------------|
| Monday    | Kwadwo    | Adwoa       |
| Tuesday   | Kwabena   | Abena       |
| Wednesday | Kweku     | Akua        |
| Thursday  | Yaw       | Yaa         |
| Friday    | Kofi      | Afua        |
| Saturday  | Kwame     | Ama         |
| Sunday    | Kwasi     | Akosua      |

Cultural significance: In Akan culture, children are named based on the day they were born.
This tradition is called "Kradin" (soul name). The day name reflects personality traits.
- Monday (Kwadwo/Adwoa): Peaceful, calm
- Tuesday (Kwabena/Abena): Sea god, ocean-spirited
- Wednesday (Kweku/Akua): Spider (Ananse), clever
- Thursday (Yaw/Yaa): Earth, strong-willed
- Friday (Kofi/Afua): Fertility, wanderer
- Saturday (Kwame/Ama): God, leadership
- Sunday (Kwasi/Akosua): Universe, adventurous
""",
    
    "ghana_regions": """
GHANA REGIONS AND CAPITALS (16 Regions):
| Region | Capital | Notable Info |
|--------|---------|--------------|
| Greater Accra | Accra | National capital, most populous |
| Ashanti | Kumasi | Cultural heartland, Asantehene seat |
| Western | Sekondi-Takoradi | Oil & gas hub |
| Central | Cape Coast | Historical slave forts, tourism |
| Eastern | Koforidua | Agriculture, cocoa |
| Volta | Ho | Kente weaving origin |
| Northern | Tamale | Largest city in north |
| Upper East | Bolgatanga | Basket weaving |
| Upper West | Wa | Traditional architecture |
| Brong-Ahafo | Sunyani | Cocoa production |
| Western North | Sefwi Wiawso | Created 2018 |
| Ahafo | Goaso | Created 2018 |
| Bono East | Techiman | Created 2018 |
| Oti | Dambai | Created 2018 |
| North East | Nalerigu | Created 2018 |
| Savannah | Damongo | Created 2018, largest region |
""",

    "twi_greetings": """
COMMON TWI GREETINGS AND PHRASES:
| English | Twi | Pronunciation |
|---------|-----|---------------|
| Hello | Ɛte sɛn | eh-teh-sehn |
| Good morning | Maakye | maa-cheh |
| Good afternoon | Maaha | maa-ha |
| Good evening | Maadwo | maa-jo |
| How are you? | Wo ho te sɛn? | woh hoh teh sehn |
| I'm fine | Me ho yɛ | meh hoh yeh |
| Thank you | Medaase | meh-daa-seh |
| Please | Mepawokyɛw | meh-pa-woh-chew |
| Welcome | Akwaaba | ah-kwaa-bah |
| Goodbye | Nante yie | nan-teh yee-eh |
| I love you | Me dɔ wo | meh dawh woh |
""",

    "akan_proverbs": """
POPULAR AKAN PROVERBS (Mmɛ):
1. "Obi nkyerɛ abɔfra Nyame" - No one teaches a child about God
2. "Nea onnim no sua a, ohu" - He who does not know can know from learning
3. "Woforo dua pa a, na yepia wo" - When you climb a good tree, you get pushed
4. "Tete ka asom" - Old things remain in the ear (wisdom passes down)
5. "Aboa a ɔnni dua, Onyame na ɔpra ne ho" - God looks after the tailless animal
""",

    "ghana_facts": """
GHANA FACTS:
- Independence: March 6, 1957 (first sub-Saharan African country)
- Population: ~34 million (2024)
- Capital: Accra
- Currency: Ghana Cedi (GHS)
- Languages: English (official), Akan, Ewe, Ga, Dagbani
- National symbol: Black Star (on flag)
""",

    "twi_numbers": """
TWI NUMBERS:
| Number | Twi | Number | Twi |
|--------|-----|--------|-----|
| 1 | Baako | 6 | Nsia |
| 2 | Mmienu | 7 | Nson |
| 3 | Mmiɛnsa | 8 | Nwɔtwe |
| 4 | Ɛnan | 9 | Nkron |
| 5 | Enum | 10 | Edu |
| 20 | Aduonu | 100 | Ɔha |
""",
}

KNOWLEDGE_KEYWORDS = {
    "akan_day_names": ["day name", "kradin", "born on", "kwadwo", "kwabena", "kweku", "yaw", "kofi", "kwame", "kwasi", 
                       "adwoa", "abena", "akua", "yaa", "afua", "ama", "akosua", "monday", "tuesday", "wednesday",
                       "thursday", "friday", "saturday", "sunday", "naming"],
    "ghana_regions": ["region", "capital", "accra", "kumasi", "tamale", "cape coast", "takoradi", "ho", "bolgatanga"],
    "twi_greetings": ["hello", "greeting", "how are you", "good morning", "goodbye", "thank you", "please", "welcome",
                      "maakye", "akwaaba", "medaase", "wo ho te"],
    "akan_proverbs": ["proverb", "mmɛ", "saying", "wisdom", "ananse"],
    "ghana_facts": ["ghana", "independence", "population", "currency", "cedi", "flag", "black star"],
    "twi_numbers": ["number", "count", "baako", "mmienu", "edu", "how many"],
}


def download_model():
    """Download model during image build"""
    from huggingface_hub import snapshot_download
    
    snapshot_download(
        MODEL_ID,
        local_dir=MODEL_DIR,
        ignore_patterns=["*.md", "*.txt", "tokenizer.json", "tokenizer_config.json"],
        token=os.environ.get("HF_TOKEN"),
    )
    
    snapshot_download(
        BASE_MODEL,
        local_dir=MODEL_DIR,
        allow_patterns=["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"],
        token=os.environ.get("HF_TOKEN"),
    )


app = modal.App("twi-ai-agent-v2")

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
        "numpy<2",
        "tavily-python",      # Web search
        "httpx",              # HTTP client for web fetch
        "beautifulsoup4",     # HTML parsing
        "lxml",               # Fast HTML parser
        "pytz",               # Timezone support
    )
    .run_function(
        download_model,
        secrets=[modal.Secret.from_name("huggingface")],
    )
)


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

def search_knowledge_base(query: str) -> str:
    """Search the embedded knowledge base for relevant info"""
    query_lower = query.lower()
    relevant_docs = []
    
    for topic, keywords in KNOWLEDGE_KEYWORDS.items():
        if any(kw in query_lower for kw in keywords):
            relevant_docs.append(KNOWLEDGE_BASE[topic])
    
    if relevant_docs:
        return "\n\n---\n\n".join(relevant_docs)
    return ""


def web_search(query: str, tavily_key: Optional[str] = None) -> str:
    """Search the web using Tavily API"""
    if not tavily_key:
        return "Web search unavailable (no API key configured)"
    
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
        
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=5,
            include_answer=True,
        )
        
        results = []
        
        # Include Tavily's AI-generated answer if available
        if response.get("answer"):
            results.append(f"**Summary:** {response['answer']}")
        
        # Include source results
        for r in response.get("results", [])[:3]:
            title = r.get('title', 'No title')
            content = r.get('content', '')[:400]
            url = r.get('url', '')
            results.append(f"**{title}**\n{content}\nSource: {url}")
        
        if results:
            return "\n\n".join(results)
        return "No results found"
        
    except Exception as e:
        return f"Web search error: {str(e)}"


def web_fetch(url: str) -> str:
    """Fetch and extract content from a URL"""
    try:
        import httpx
        from bs4 import BeautifulSoup
        
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AmaBot/1.0; +https://twi-ai.com)"
        }
        
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()
        
        # Get title
        title = soup.title.string if soup.title else "No title"
        
        # Get main content
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        
        if main_content:
            text = main_content.get_text(separator='\n', strip=True)
            # Limit to first 3000 chars
            text = text[:3000]
            return f"**Page Title:** {title}\n\n**Content:**\n{text}"
        
        return f"**Page Title:** {title}\n\nCould not extract main content."
        
    except Exception as e:
        return f"Web fetch error: {str(e)}"


def image_search(query: str, tavily_key: Optional[str] = None) -> str:
    """Search for images using Tavily"""
    if not tavily_key:
        return "Image search unavailable (no API key)"
    
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
        
        response = client.search(
            query=f"{query} images",
            search_depth="basic",
            max_results=5,
            include_images=True,
        )
        
        images = response.get("images", [])
        if images:
            result = "**Found Images:**\n"
            for i, img_url in enumerate(images[:5], 1):
                result += f"{i}. {img_url}\n"
            return result
        
        return "No images found"
        
    except Exception as e:
        return f"Image search error: {str(e)}"


def get_current_time(timezone: str = "Africa/Accra") -> str:
    """Get current date and time"""
    try:
        import pytz
        from datetime import datetime
        
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
        
        # Day name in Twi
        day_names_twi = {
            0: "Dwowda (Monday)",
            1: "Benada (Tuesday)", 
            2: "Wukuada (Wednesday)",
            3: "Yawoada (Thursday)",
            4: "Fiada (Friday)",
            5: "Memeneda (Saturday)",
            6: "Kwasiada (Sunday)"
        }
        
        twi_day = day_names_twi.get(now.weekday(), "")
        
        return f"""**Current Date & Time ({timezone}):**
- Date: {now.strftime('%A, %B %d, %Y')}
- Twi Day: {twi_day}
- Time: {now.strftime('%I:%M %p')} ({now.strftime('%H:%M')})
- Timezone: {timezone}
- UTC Offset: {now.strftime('%z')}"""
        
    except Exception as e:
        return f"Time error: {str(e)}"


def create_file(filename: str, content: str, file_type: str = "txt") -> Dict[str, Any]:
    """Create a file that can be shared with the user"""
    try:
        os.makedirs(FILES_DIR, exist_ok=True)
        
        # Generate unique ID
        file_id = str(uuid.uuid4())[:8]
        
        # Sanitize filename
        safe_filename = re.sub(r'[^\w\-\.]', '_', filename)
        if not safe_filename.endswith(f'.{file_type}'):
            safe_filename = f"{safe_filename}.{file_type}"
        
        filepath = os.path.join(FILES_DIR, f"{file_id}_{safe_filename}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "file_id": file_id,
            "filename": safe_filename,
            "filepath": filepath,
            "size": len(content),
            "message": f"File '{safe_filename}' created successfully (ID: {file_id})"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def view_file(file_id: str) -> str:
    """View contents of a created file"""
    try:
        if not os.path.exists(FILES_DIR):
            return "No files found"
        
        for filename in os.listdir(FILES_DIR):
            if filename.startswith(file_id):
                filepath = os.path.join(FILES_DIR, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                return f"**File: {filename}**\n\n```\n{content[:5000]}\n```"
        
        return f"File with ID '{file_id}' not found"
        
    except Exception as e:
        return f"Error viewing file: {str(e)}"


def list_files() -> str:
    """List all created files"""
    try:
        if not os.path.exists(FILES_DIR):
            return "No files created yet"
        
        files = os.listdir(FILES_DIR)
        if not files:
            return "No files created yet"
        
        result = "**Created Files:**\n"
        for filename in files:
            filepath = os.path.join(FILES_DIR, filename)
            size = os.path.getsize(filepath)
            # Extract file_id from filename
            file_id = filename.split('_')[0]
            display_name = '_'.join(filename.split('_')[1:])
            result += f"- [{file_id}] {display_name} ({size} bytes)\n"
        
        return result
        
    except Exception as e:
        return f"Error listing files: {str(e)}"


# ============================================================================
# AGENT SYSTEM PROMPT
# ============================================================================

AGENT_SYSTEM_PROMPT = """You are Ama, a bilingual Twi-English AI assistant with access to powerful tools.

## AVAILABLE TOOLS:

1. **KNOWLEDGE_BASE** - Verified facts about Ghana, Twi language, Akan culture
2. **WEB_SEARCH** - Search the internet for current information
3. **WEB_FETCH** - Get full content from a specific URL
4. **IMAGE_SEARCH** - Find images related to a topic
5. **CURRENT_TIME** - Get current date/time (Ghana timezone)
6. **CREATE_FILE** - Create a document to share with user
7. **VIEW_FILE** - View a created file's contents
8. **LIST_FILES** - Show all created files

## WHEN TO USE TOOLS:

| Tool | Use For |
|------|---------|
| KNOWLEDGE_BASE | Akan day names, Twi translations, Ghana regions, proverbs |
| WEB_SEARCH | News, current events, anything after 2024, facts you're unsure about |
| WEB_FETCH | Reading full article/page content from a URL |
| IMAGE_SEARCH | Finding pictures of places, people, things |
| CURRENT_TIME | When user asks about time, date, or day |
| CREATE_FILE | When user wants a document, summary, translation saved |
| VIEW_FILE | When user wants to see a file they/you created |
| LIST_FILES | When user asks what files exist |

## CRITICAL RULES:

1. **OUTDATED KNOWLEDGE**: Your training is from 2024. Political info is WRONG.
   - ALWAYS search for: presidents, ministers, elections, government, MPs
   - Never guess political leaders - SEARCH FIRST

2. **AKAN DAY NAMES** (memorized - don't search):
   | Day | Male | Female |
   |-----|------|--------|
   | Monday | Kwadwo | Adwoa |
   | Tuesday | Kwabena | Abena |
   | Wednesday | Kweku | Akua |
   | Thursday | Yaw | Yaa |
   | Friday | Kofi | Afua |
   | Saturday | Kwame | Ama |
   | Sunday | Kwasi | Akosua |

3. **FILE CREATION**: When creating documents, use clear structure and formatting.

## HOW TO REQUEST TOOLS:

When you need a tool, I will provide results automatically. Just answer naturally and I'll detect when tools are needed.

## YOUR IDENTITY:
- Name: Ama (born on Saturday in Akan tradition)
- Creator: Angelo Asante
- Languages: Twi and English (match user's language)
- Personality: Warm, knowledgeable, helpful"""


# ============================================================================
# MODAL CLASS
# ============================================================================

@app.cls(
    image=image,
    gpu="A100",
    timeout=600,
    scaledown_window=120,
    memory=32768,
    secrets=[
        modal.Secret.from_name("huggingface"),
        modal.Secret.from_name("tavily"),
    ],
)
class TwiAgent:
    @modal.enter()
    def load_model(self):
        """Load model when container starts"""
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        print(f"Loading model from {MODEL_DIR}...")
        
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_DIR,
            torch_dtype=torch.float16,
            device_map="auto",
        )
        
        self.tavily_key = os.environ.get("TAVILY_API_KEY")
        
        # Initialize file storage
        os.makedirs(FILES_DIR, exist_ok=True)
        
        print(f"Model loaded! Tools: KB, Web Search, Web Fetch, Images, Time, Files")

    def generate(self, messages: list, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate a response from the model"""
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
        
        return self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True
        )

    def detect_and_run_tools(self, prompt: str) -> Dict[str, Any]:
        """Automatically detect which tools to use and run them"""
        prompt_lower = prompt.lower()
        results = {"tools_used": [], "context": ""}
        
        # Keywords for auto-triggering tools
        NEWS_KEYWORDS = ["news", "latest", "today", "recent", "current", "happening", 
                        "2025", "2026", "update", "breaking", "now"]
        
        POLITICAL_KEYWORDS = ["president", "vice president", "government", "minister",
                             "election", "parliament", "ndc", "npp", "political",
                             "who is the", "who won", "current leader", "mp", "member of parliament"]
        
        TIME_KEYWORDS = ["time", "date", "what day", "today's date", "current time", "clock"]
        
        IMAGE_KEYWORDS = ["image", "picture", "photo", "show me", "what does", "look like"]
        
        FILE_KEYWORDS = ["create file", "save", "document", "write a file", "make a file"]
        
        LIST_FILE_KEYWORDS = ["list files", "show files", "my files", "what files"]
        
        URL_PATTERN = r'https?://[^\s]+'
        
        context_parts = []
        
        # 1. Check for URLs - fetch content
        urls = re.findall(URL_PATTERN, prompt)
        if urls:
            for url in urls[:2]:  # Max 2 URLs
                content = web_fetch(url)
                context_parts.append(f"[WEB PAGE CONTENT from {url}]\n{content}")
                results["tools_used"].append({"tool": "web_fetch", "url": url})
        
        # 2. Check for time queries
        if any(kw in prompt_lower for kw in TIME_KEYWORDS):
            time_info = get_current_time()
            context_parts.append(f"[CURRENT TIME]\n{time_info}")
            results["tools_used"].append({"tool": "current_time"})
        
        # 3. Check for political queries - ALWAYS search
        needs_political_search = any(kw in prompt_lower for kw in POLITICAL_KEYWORDS)
        
        # 4. Check for news/current events
        needs_news_search = any(kw in prompt_lower for kw in NEWS_KEYWORDS)
        
        # 5. Auto web search for political or news
        if (needs_political_search or needs_news_search) and self.tavily_key:
            search_query = prompt
            if needs_political_search and "ghana" not in prompt_lower:
                search_query = f"Ghana {prompt}"
            
            search_results = web_search(search_query, self.tavily_key)
            context_parts.append(f"[WEB SEARCH RESULTS - LIVE DATA]\n{search_results}")
            results["tools_used"].append({
                "tool": "web_search", 
                "query": search_query,
                "reason": "political/news query"
            })
        
        # 6. Check for image requests
        if any(kw in prompt_lower for kw in IMAGE_KEYWORDS) and self.tavily_key:
            img_results = image_search(prompt, self.tavily_key)
            context_parts.append(f"[IMAGE SEARCH RESULTS]\n{img_results}")
            results["tools_used"].append({"tool": "image_search", "query": prompt})
        
        # 7. Check knowledge base (but skip for political queries)
        if not needs_political_search:
            kb_results = search_knowledge_base(prompt)
            if kb_results:
                context_parts.append(f"[KNOWLEDGE BASE]\n{kb_results}")
                results["tools_used"].append({"tool": "knowledge_base"})
        
        # 8. Check for list files request
        if any(kw in prompt_lower for kw in LIST_FILE_KEYWORDS):
            files_list = list_files()
            context_parts.append(f"[FILES]\n{files_list}")
            results["tools_used"].append({"tool": "list_files"})
        
        # Combine all context
        if context_parts:
            results["context"] = "\n\n---\n\n".join(context_parts)
        
        return results

    @modal.fastapi_endpoint(method="POST")
    def chat(self, data: dict) -> dict:
        """HTTP endpoint for agent chat"""
        try:
            prompt = data.get("prompt", "")
            system_prompt = data.get("system_prompt", AGENT_SYSTEM_PROMPT)
            max_tokens = data.get("max_tokens", 512)
            temperature = data.get("temperature", 0.7)
            
            if not prompt:
                return {"error": "No prompt provided"}
            
            # Auto-detect and run tools
            tool_results = self.detect_and_run_tools(prompt)
            
            # Build messages with tool context injected
            messages = [{"role": "system", "content": system_prompt}]
            
            if tool_results["context"]:
                # Inject tool results clearly into the prompt
                augmented_prompt = f"""I searched for information and found:

{tool_results["context"]}

---

User's question: {prompt}

Instructions: Answer the user's question using ONLY the information above. If the search results contain the answer, use that. Do not use outdated training data for political or current events."""
                
                messages.append({"role": "user", "content": augmented_prompt})
            else:
                messages.append({"role": "user", "content": prompt})
            
            # Generate response
            response = self.generate(messages, max_tokens, temperature)
            
            # Check if user wants to create a file
            prompt_lower = prompt.lower()
            file_result = None
            if any(kw in prompt_lower for kw in ["create file", "save this", "make a document", "write to file"]):
                # Try to extract filename from prompt
                filename_match = re.search(r'(?:called?|named?|as)\s+["\']?(\w+)["\']?', prompt_lower)
                filename = filename_match.group(1) if filename_match else "document"
                
                file_result = create_file(filename, response, "txt")
                if file_result["success"]:
                    response += f"\n\n📄 **File created:** {file_result['filename']} (ID: {file_result['file_id']})"
            
            return {
                "response": response,
                "model": MODEL_ID,
                "tools_used": tool_results["tools_used"],
                "file_created": file_result,
            }
            
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}

    @modal.fastapi_endpoint(method="POST")
    def create_file_endpoint(self, data: dict) -> dict:
        """Endpoint to create a file directly"""
        filename = data.get("filename", "document")
        content = data.get("content", "")
        file_type = data.get("type", "txt")
        
        if not content:
            return {"error": "No content provided"}
        
        return create_file(filename, content, file_type)

    @modal.fastapi_endpoint(method="GET")
    def list_files_endpoint(self) -> dict:
        """Endpoint to list all files"""
        return {"files": list_files()}

    @modal.fastapi_endpoint(method="POST")
    def get_file_endpoint(self, data: dict) -> dict:
        """Endpoint to get a specific file"""
        file_id = data.get("file_id", "")
        return {"content": view_file(file_id)}

    @modal.fastapi_endpoint(method="GET")
    def get_time_endpoint(self) -> dict:
        """Endpoint to get current time"""
        return {"time": get_current_time("Africa/Accra")}


@app.local_entrypoint()
def main(prompt: str = "Who is the president of Ghana?"):
    """Test locally"""
    agent = TwiAgent()
    result = agent.chat.remote({"prompt": prompt, "max_tokens": 512})
    print(json.dumps(result, indent=2))
