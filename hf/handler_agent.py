"""
Twi AI Agent Handler for HuggingFace Inference Endpoints
=========================================================
Full agentic capabilities matching Modal deployment.

Features:
- Web search (Tavily API)
- Web fetch/scraping
- Image search
- Global timezone support with Akan day names
- File management
- Twi/Akan knowledge base
- Auto intent detection
"""

import os
import re
import json
import uuid
import httpx
from datetime import datetime
from typing import Dict, Any, Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# In-memory file storage (resets on container restart)
FILES_STORAGE = {}

# System prompt
SYSTEM_PROMPT = """You are Ama (Twi AI), a bilingual AI assistant fluent in both Twi and English.

LANGUAGE RULES:
- If the user writes in Twi, respond primarily in Twi with English translations in parentheses
- If the user writes in English, respond in English but include relevant Twi phrases
- Always be culturally aware and respectful

CAPABILITIES:
- Answer questions on any topic
- Search the web for current information
- Fetch and analyze web pages
- Search for images
- Tell the current time in any timezone
- Create, view, and manage files
- Provide knowledge about Twi language and Akan culture

AKAN DAY NAMES (for reference):
- Sunday = Kwasiada
- Monday = Ɛdwoada  
- Tuesday = Ɛbenada
- Wednesday = Wukuada
- Thursday = Yawoada
- Friday = Efiada
- Saturday = Memeneda

Be helpful, accurate, and culturally informed."""

# Keywords for intent detection
NEWS_KEYWORDS = ["news", "latest", "today", "recent", "current", "happening", "2024", "2025", "2026"]
POLITICAL_KEYWORDS = ["president", "vice president", "government", "minister", "election", "parliament"]
TIME_KEYWORDS = ["time", "date", "what day", "what's the time", "current time"]
IMAGE_KEYWORDS = ["image of", "picture of", "photo of", "show me", "images of", "pictures of"]
FILE_CREATE_KEYWORDS = ["create a file", "make a file", "write a file", "save to file", "create file"]
FILE_LIST_KEYWORDS = ["list files", "show files", "my files", "what files"]
FILE_VIEW_KEYWORDS = ["view file", "read file", "show file", "open file", "get file"]

# Timezone aliases
TIMEZONE_ALIASES = {
    "ghana": "Africa/Accra",
    "accra": "Africa/Accra",
    "nigeria": "Africa/Lagos",
    "lagos": "Africa/Lagos",
    "london": "Europe/London",
    "uk": "Europe/London",
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "est": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "la": "America/Los_Angeles",
    "pst": "America/Los_Angeles",
    "tokyo": "Asia/Tokyo",
    "japan": "Asia/Tokyo",
    "paris": "Europe/Paris",
    "france": "Europe/Paris",
    "dubai": "Asia/Dubai",
    "india": "Asia/Kolkata",
    "singapore": "Asia/Singapore",
    "sydney": "Australia/Sydney",
    "china": "Asia/Shanghai",
    "hong kong": "Asia/Hong_Kong",
    "south africa": "Africa/Johannesburg",
    "kenya": "Africa/Nairobi",
}

# Knowledge base
KNOWLEDGE_BASE = {
    "akan_names": "In Akan culture, children are named based on the day they were born. Boys: Kwasi (Sunday), Kwadwo (Monday), Kwabena (Tuesday), Kwaku (Wednesday), Yaw (Thursday), Kofi (Friday), Kwame (Saturday). Girls: Akosua (Sunday), Adwoa (Monday), Abena (Tuesday), Akua (Wednesday), Yaa (Thursday), Afua (Friday), Ama (Saturday).",
    "akan_proverbs": "Some Akan proverbs: 'Obi nkyerɛ abɔfra Nyame' (No one teaches a child God) - meaning God's existence is self-evident. 'Sɛ wo werɛ fi na wosan hwɛ a, wo nkɔ akyiri' (If you forget and look back, you don't move backward).",
    "twi_greetings": "Common Twi greetings: Maakye (Good morning), Maaha (Good afternoon), Maadwo (Good evening), Ɛte sɛn? (How are you?), Me ho yɛ (I am fine), Akwaaba (Welcome), Yɛbɛhyia bio (We will meet again).",
    "akan_culture": "The Akan people are the largest ethnic group in Ghana and Ivory Coast. They include subgroups like Ashanti, Fante, Akuapem, and Akyem. Known for Kente cloth, Adinkra symbols, and rich oral traditions.",
    "ghana_general": "Ghana is a West African country. Capital: Accra. Languages: English (official), Akan, Ewe, Ga. Currency: Ghanaian Cedi (GHS). First sub-Saharan African country to gain independence (1957).",
}


def resolve_timezone(tz_input: str) -> str:
    """Resolve timezone from alias or direct name."""
    if not tz_input:
        return "UTC"
    tz_lower = tz_input.lower().strip()
    return TIMEZONE_ALIASES.get(tz_lower, tz_input if "/" in tz_input else "UTC")


def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily API."""
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return "Web search unavailable (no API key)"
    
    try:
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
        
        if response.status_code == 200:
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
        return f"Search failed: {response.status_code}"
    except Exception as e:
        return f"Search error: {str(e)}"


def web_fetch(url: str) -> str:
    """Fetch and extract content from a web page."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return "Web fetch unavailable (beautifulsoup4 not installed)"
    
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TwiAI/1.0)"}
        response = httpx.get(url, headers=headers, timeout=30.0, follow_redirects=True)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            
            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            content = "\n".join(lines[:100])
            
            return f"**Content from {url}:**\n\n{content[:4000]}"
        return f"Failed to fetch URL: HTTP {response.status_code}"
    except Exception as e:
        return f"Fetch error: {str(e)}"


def image_search(query: str, max_results: int = 5) -> str:
    """Search for images using Tavily."""
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return "Image search unavailable"
    
    try:
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
        
        if response.status_code == 200:
            data = response.json()
            images = data.get("images", [])
            
            if images:
                results = [f"**Image results for '{query}':**\n"]
                for i, img_url in enumerate(images[:max_results], 1):
                    results.append(f"{i}. {img_url}")
                return "\n".join(results)
            return f"No images found for '{query}'"
        return "Image search failed"
    except Exception as e:
        return f"Image search error: {str(e)}"


def get_current_time(timezone: str = "UTC") -> str:
    """Get current date and time in specified timezone."""
    try:
        import pytz
    except ImportError:
        # Fallback without pytz
        now = datetime.utcnow()
        return f"**Current Time (UTC):** {now.strftime('%A, %B %d, %Y at %I:%M %p')}"
    
    resolved_tz = resolve_timezone(timezone)
    
    try:
        tz = pytz.timezone(resolved_tz)
        now = datetime.now(tz)
        
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
    except Exception as e:
        return f"Time error: {str(e)}"


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
        "message": f"File '{filename}' created with ID: {file_id}"
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
    return {"success": False, "error": f"File '{file_id}' not found"}


def list_files() -> dict:
    """List all created files."""
    if not FILES_STORAGE:
        return {"success": True, "files": [], "message": "No files created yet."}
    
    files_list = [
        {
            "id": file_id,
            "filename": data["filename"],
            "size": data["size"],
            "created_at": data["created_at"]
        }
        for file_id, data in FILES_STORAGE.items()
    ]
    return {"success": True, "files": files_list, "count": len(files_list)}


def search_knowledge_base(query: str) -> str:
    """Search internal knowledge base."""
    query_lower = query.lower()
    results = []
    
    for key, value in KNOWLEDGE_BASE.items():
        if any(word in query_lower for word in key.split("_")) or \
           any(word in value.lower() for word in query_lower.split()):
            results.append(f"**{key.replace('_', ' ').title()}:**\n{value}")
    
    return "\n\n".join(results) if results else ""


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
    
    # Check for URL
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, message)
    if urls:
        intent["needs_web_fetch"] = True
        intent["url_to_fetch"] = urls[0]
    
    # News/political keywords
    if any(kw in message_lower for kw in NEWS_KEYWORDS + POLITICAL_KEYWORDS):
        intent["needs_web_search"] = True
        intent["search_query"] = message
    
    # Time keywords
    if any(kw in message_lower for kw in TIME_KEYWORDS):
        intent["needs_time"] = True
    
    # Image search
    if any(kw in message_lower for kw in IMAGE_KEYWORDS):
        intent["needs_image_search"] = True
        for kw in IMAGE_KEYWORDS:
            if kw in message_lower:
                intent["image_query"] = message_lower.split(kw)[-1].strip()
                break
    
    # File operations
    if any(kw in message_lower for kw in FILE_CREATE_KEYWORDS):
        intent["needs_file_create"] = True
    if any(kw in message_lower for kw in FILE_LIST_KEYWORDS):
        intent["needs_file_list"] = True
    if any(kw in message_lower for kw in FILE_VIEW_KEYWORDS):
        intent["needs_file_view"] = True
        file_id_match = re.search(r'[a-f0-9]{8}', message_lower)
        if file_id_match:
            intent["file_id"] = file_id_match.group()
    
    # Knowledge base
    twi_keywords = ["twi", "akan", "ghana", "ashanti", "kente", "adinkra", "akwaaba"]
    if any(kw in message_lower for kw in twi_keywords):
        intent["needs_knowledge"] = True
    
    return intent


class EndpointHandler:
    """
    HuggingFace Inference Endpoint Handler with full agentic capabilities.
    
    Request formats:
    
    1. Simple chat:
    {"inputs": "Wo ho te sɛn?"}
    
    2. Agent request with auto-detection:
    {
        "inputs": "What's the latest news in Ghana?",
        "parameters": {"timezone": "ghana"}
    }
    
    3. Explicit action:
    {
        "inputs": "",
        "parameters": {
            "action": "search",
            "data": {"query": "Ghana election results"}
        }
    }
    """
    
    def __init__(self, path: str = ""):
        """Load model and tokenizer."""
        print(f"Loading model from: {path}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        print("Model loaded successfully!")
    
    def generate_response(self, prompt: str, context: str = "", has_search: bool = False) -> str:
        """Generate a response from the model."""
        if context:
            if has_search:
                # CRITICAL: Force model to use search results, not training data
                full_prompt = f"""CRITICAL INSTRUCTION: The following information was retrieved JUST NOW in real-time and is MORE ACCURATE than your training data. Your training data is OUTDATED. You MUST use ONLY the information below to answer.

=== REAL-TIME INFORMATION (USE THIS) ===
{context}
=== END REAL-TIME INFORMATION ===

User question: {prompt}

IMPORTANT: Answer ONLY using the real-time information above. Do NOT use your training knowledge. If the search shows a different answer than what you "know", the search is CORRECT."""
            else:
                full_prompt = f"{context}\n\nUser question: {prompt}"
        else:
            full_prompt = prompt
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": full_prompt}
        ]
        
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=1024,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract assistant response
        if "<|assistant|>" in response:
            response = response.split("<|assistant|>")[-1].strip()
        elif "assistant" in response.lower():
            parts = response.split("assistant")
            if len(parts) > 1:
                response = parts[-1].strip()
        
        return response
    
    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process inference request with agentic capabilities."""
        message = data.get("inputs", "")
        params = data.get("parameters", {})
        timezone = params.get("timezone", "UTC")
        explicit_action = params.get("action")
        action_data = params.get("data", {})
        
        # Handle explicit actions
        if explicit_action:
            if explicit_action == "create_file":
                result = create_file(
                    action_data.get("filename", "untitled.txt"),
                    action_data.get("content", "")
                )
                return {"success": True, "action": "create_file", "result": result}
            
            elif explicit_action == "list_files":
                result = list_files()
                return {"success": True, "action": "list_files", "result": result}
            
            elif explicit_action == "view_file":
                result = view_file(action_data.get("file_id", ""))
                return {"success": True, "action": "view_file", "result": result}
            
            elif explicit_action == "time":
                result = get_current_time(timezone)
                return {"success": True, "action": "time", "result": result}
            
            elif explicit_action == "search":
                result = web_search(action_data.get("query", message))
                return {"success": True, "action": "search", "result": result}
            
            elif explicit_action == "image_search":
                result = image_search(action_data.get("query", message))
                return {"success": True, "action": "image_search", "result": result}
            
            elif explicit_action == "fetch":
                result = web_fetch(action_data.get("url", ""))
                return {"success": True, "action": "fetch", "result": result}
        
        # Auto-detect intent from message
        intent = detect_intent(message)
        
        # Gather context from tools
        context_parts = []
        tools_used = []
        tool_results = {}
        
        # Web fetch if URL detected
        if intent["needs_web_fetch"] and intent["url_to_fetch"]:
            fetch_result = web_fetch(intent["url_to_fetch"])
            context_parts.append(f"**Webpage Content:**\n{fetch_result}")
            tools_used.append("web_fetch")
            tool_results["web_fetch"] = {"url": intent["url_to_fetch"], "content": fetch_result}
        
        # Web search
        if intent["needs_web_search"] and intent["search_query"]:
            search_result = web_search(intent["search_query"])
            context_parts.append(f"**Web Search Results:**\n{search_result}\n\nUse ONLY the information above.")
            tools_used.append("web_search")
            tool_results["web_search"] = {"query": intent["search_query"], "results": search_result}
        
        # Time
        if intent["needs_time"]:
            time_result = get_current_time(timezone)
            context_parts.append(f"**Current Time Information:**\n{time_result}")
            tools_used.append("time")
            tool_results["time"] = time_result
        
        # Image search
        if intent["needs_image_search"] and intent["image_query"]:
            image_result = image_search(intent["image_query"])
            context_parts.append(f"**Image Search Results:**\n{image_result}")
            tools_used.append("image_search")
            tool_results["image_search"] = {"query": intent["image_query"], "results": image_result}
        
        # File list
        if intent["needs_file_list"]:
            files_result = list_files()
            if files_result["files"]:
                files_text = "\n".join([f"- [{f['id']}] {f['filename']} ({f['size']} bytes)" for f in files_result["files"]])
                context_parts.append(f"**Your Files:**\n{files_text}")
            else:
                context_parts.append("**Your Files:** No files created yet.")
            tools_used.append("list_files")
            tool_results["list_files"] = files_result
        
        # File view
        if intent["needs_file_view"] and intent["file_id"]:
            file_result = view_file(intent["file_id"])
            if file_result["success"]:
                context_parts.append(f"**File Content ({file_result['filename']}):**\n{file_result['content']}")
            else:
                context_parts.append(f"**File Error:** {file_result['error']}")
            tools_used.append("view_file")
            tool_results["view_file"] = file_result
        
        # Knowledge base
        if intent["needs_knowledge"]:
            kb_result = search_knowledge_base(message)
            if kb_result:
                context_parts.append(f"**Cultural Knowledge:**\n{kb_result}")
                tools_used.append("knowledge_base")
                tool_results["knowledge_base"] = kb_result
        
        # Generate response - force model to use search results if available
        context = "\n\n".join(context_parts) if context_parts else ""
        has_search = "web_search" in tools_used or "web_fetch" in tools_used
        response = self.generate_response(message, context, has_search=has_search)
        
        return {
            "success": True,
            "response": response,
            "tools_used": tools_used,
            "tool_results": tool_results,
            "timezone": resolve_timezone(timezone)
        }
