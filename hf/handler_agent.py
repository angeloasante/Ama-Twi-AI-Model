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
Your name is Ama. You were created by Angelo Asante (also known as Travis Moore) www.angeloasante.com, a software engineer and AI developer — NOT a musician.

YOUR PERSONALITY:
- You are warm, witty, patient, and encouraging — like a cool Ghanaian auntie or older sister.
- You have a playful sense of humor but you're genuinely helpful.
- You care about getting things RIGHT. If you're not sure about a Twi phrase, say so honestly rather than making something up.
- You're proud of Akan/Ghanaian culture and love sharing it authentically.
- You speak naturally — not like a textbook, not like a robot.

RESPONSE STYLE — YOUR MOST IMPORTANT RULES:
- Match the user's energy. Short question = short answer. Detailed question = detailed answer.
- If someone says "hello" or "hi", reply with a warm 1-2 sentence greeting. Do NOT ramble.
- If someone asks "explain X in detail", give a thorough 6-10 sentence explanation with facts and examples.
- If someone asks "what is X", give a clear 3-4 sentence answer.
- NEVER pad responses with filler like "What would you like to talk about?", "Feel free to ask!", "Let me know!"
- NEVER use hashtags (#GhanaProud, #AkanCulture, etc.). This is not social media.
- Use emojis sparingly — at most 1-2 per response, and only when natural.
- Do NOT repeat yourself. Say it once, clearly.
- Be natural and conversational, not performative.
- NEVER apologize excessively or say "I made a mistake" repeatedly. Just give the right answer.

TWI LANGUAGE TEACHING RULES (CRITICAL):
- When teaching Twi, ALWAYS use this format: Twi phrase first, then "=" or "means", then the English meaning.
- Example: "Mepɛ wo" means "I like/love you"
- ONLY teach Twi phrases you are CONFIDENT are correct. If unsure, say "I'm not 100% sure of this one" or skip it.
- NEVER string random Twi words together and pretend they form a sentence.
- NEVER generate long blocks of Twi without translations.
- When someone asks "what does X mean?", give a CLEAR English translation immediately. Do not deflect.
- Teach 2-4 phrases at a time, not a wall of text. Let the user absorb them.
- Add context: when would you use this phrase? Is it formal or casual?

LANGUAGE RULES:
- If the user writes in Twi, respond primarily in Twi with English translations in parentheses.
- If the user writes in English, respond in English but include relevant Twi phrases naturally.
- Always be culturally aware and respectful.

DOCUMENT CREATION:
- When asked to create a document, write comprehensive, well-structured content.
- Use markdown formatting: headers (##), bullet points, bold, etc.
- Include an introduction, detailed body sections, and a conclusion.

AKAN DAY NAMES:
- Sunday = Kwasiada, Monday = Ɛdwoada, Tuesday = Ɛbenada, Wednesday = Wukuada
- Thursday = Yawoada, Friday = Efiada, Saturday = Memeneda

You are Ama. Be warm, knowledgeable, and genuine."""

# Keywords for intent detection
NEWS_KEYWORDS = ["news", "latest news", "current events", "happening now", "what happened", "breaking", "headlines", "2024", "2025", "2026"]
POLITICAL_KEYWORDS = ["president", "vice president", "government", "minister", "election", "parliament"]
SEARCH_KEYWORDS = ["search for", "search about", "look up", "find out", "google", "tell me more", "learn more", "find information", "what do you know about", "search the web", "search online", "search it", "search that", "web search", "go search", "can you search", "please search"]
TIME_KEYWORDS = ["time", "date", "what day", "what's the time", "current time"]
IMAGE_KEYWORDS = ["image of", "picture of", "photo of", "show me", "images of", "pictures of"]
DETAIL_KEYWORDS = ["explain", "in detail", "in great detail", "describe", "tell me about", "talk to me about", "talk about", "what is", "what are", "how does", "how do", "why is", "why do", "elaborate"]
FILE_CREATE_KEYWORDS = ["create a file", "make a file", "write a file", "save to file", "create file", "create a document", "make a document", "write a document", "create document", "create documentation", "write documentation", "make documentation", "write me a", "draft a"]
FILE_LIST_KEYWORDS = ["list files", "show files", "my files", "what files"]
FILE_VIEW_KEYWORDS = ["view file", "read file", "show file", "open file", "get file"]
# Patterns that indicate factual/knowledge questions the model can't reliably answer alone
# These trigger an automatic web search so the model gets real data to work with
KNOWLEDGE_PATTERNS = [
    r'\b(?:places?|things?|spots?|attractions?|sites?)\s+to\s+(?:visit|see|go|do|explore|check out)\b',
    r'\b(?:best|top|popular|famous|must.?see|must.?visit|recommended)\s+(?:places?|things?|spots?|restaurants?|hotels?|beaches?)\b',
    r'\b(?:where|how)\s+(?:to|can|should|do)\s+(?:i|we|you)\s+(?:go|visit|eat|stay|travel|get|find)\b',
    r'\b(?:travel|trip|visit|vacation|holiday|tour)\s+(?:to|in|tips?|guide|plan|itinerary)\b',
    r'\b(?:history|capital|population|currency|language|economy)\s+of\b',
    r'\b(?:who is|who was|when did|when was|how many|how much|how old)\b',
    r'\b(?:recipe|ingredients|how to (?:make|cook|prepare|bake))\b',
    r'\b(?:weather|temperature|climate)\s+(?:in|at|for)\b',
    r'\b(?:distance|far|directions?|route)\s+(?:from|to|between)\b',
    r'\b(?:cost|price|cheap|expensive|afford|budget)\s+(?:of|in|to|for)\b',
    # "tell me about X", "talk to me about X", "what is X", "explain X" — factual queries the model can't reliably answer
    r'\b(?:tell\s+me\s+about|talk\s+(?:to\s+me\s+)?about|what\s+(?:is|are)\s+(?:the|a|an)?\s*\w+|explain\s+(?:the|what|how)?\s*\w+)\b',
    r'\bdefine\s+\w+',
    r'\b(?:meaning|definition)\s+of\b',
    # "X's new Y", "latest X", "new X" — queries about recent products/technology/events
    r'\b(?:latest|newest|new|recent|upcoming)\s+(?:\w+\s+)?(?:tech|technology|product|gadget|device|feature|release|update|announcement)s?\b',
    r"\b\w+'s\s+(?:new|latest|newest|recent)\s+\w+",
]
CREATOR_KEYWORDS = ["angelo asante", "travis moore", "who created", "who made you", "who built you", "your creator", "your developer", "who designed you", "angeloasante"]

# Vague follow-up phrases that need topic extraction from conversation context
FOLLOWUP_PHRASES = [
    "tell me more", "more about it", "more about that", "go on", "continue",
    "elaborate", "explain more", "keep going", "what else", "more details",
    "more info", "tell me about it", "more on that", "expand on that",
    "can you elaborate", "give me more", "i want to know more", "like to learn more",
    "learn more", "know more", "more specific", "in more detail",
]

# Hardcoded creator info — injected as context so the model can't override it
CREATOR_INFO = """Angelo Asante (also known as Travis Moore) is a software engineer and AI developer from Ghana.
He is the creator of Ama (Twi AI). His website is www.angeloasante.com.
Angelo Asante is NOT a musician, NOT a footballer, NOT an athlete. He is a tech professional who builds AI tools for African languages.
He built Ama to help people learn Twi and explore Akan culture."""

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

# Verified Twi phrases for teaching — ONLY include phrases we are confident about
TWI_PHRASES = {
    "romantic": [
        ("Mepɛ wo", "I like/love you", "Casual way to say I love you"),
        ("Medɔ wo", "I love you", "The deep, romantic way to say I love you"),
        ("Wo ho yɛ fɛ", "You are beautiful", "A sincere compliment — she will love this"),
        ("Wo yɛ me nua", "You are my special one", "Term of endearment"),
        ("Mepɛ sɛ me ne wo bɛtena", "I want to be with you", "Expressing commitment"),
        ("Wo yɛ ɔdɔ", "You are love", "Sweet compliment"),
        ("Me kra dɔ wo", "My soul loves you", "Very deep, poetic expression of love"),
        ("Maware wo", "I will marry you", "A marriage declaration — use with care!"),
        ("Mepɛ sɛ meware wo", "I want to marry you", "Marriage proposal"),
    ],
    "greetings": [
        ("Maakye", "Good morning", "Used in the morning until about noon"),
        ("Maaha", "Good afternoon", "Used from noon to evening"),
        ("Maadwo", "Good evening", "Used in the evening and night"),
        ("Ɛte sɛn?", "How are you?", "The most common way to ask how someone is doing"),
        ("Me ho yɛ", "I am fine", "The standard reply to Ɛte sɛn?"),
        ("Akwaaba", "Welcome", "Used to welcome someone — very warm and genuine"),
        ("Wo ho te sɛn?", "How are you? (respectful)", "More respectful/formal version"),
        ("Da yie", "Sleep well / Good night", "Used when saying goodnight"),
    ],
    "essentials": [
        ("Medaase", "Thank you", "Essential — use this a lot, Ghanaians appreciate gratitude"),
        ("Medaase paa", "Thank you very much", "Extra gratitude — she'll love hearing this"),
        ("Mepaakyɛw", "Please / Excuse me", "Polite word — shows good manners"),
        ("Aane", "Yes", "Simple yes"),
        ("Daabi", "No", "Simple no"),
        ("Yɛbɛhyia bio", "We will meet again", "A warm way to say goodbye"),
        ("Nante yie", "Walk well / Safe travels", "Said when someone is leaving"),
        ("Ma me kwan", "Excuse me / Let me pass", "Useful in everyday situations"),
    ],
    "impress_family": [
        ("Agya, medaase", "Father, thank you", "Addressing her father respectfully — huge points"),
        ("Ɛna, medaase", "Mother, thank you", "Addressing her mother respectfully"),
        ("Mepa wo kyɛw", "I beg your pardon (respectful)", "Very respectful — great with elders"),
        ("Ɛyɛ", "It is good / OK", "Casual agreement — sounds very natural"),
        ("Adɛn?", "Why?", "Asking why — handy in conversation"),
        ("Wo din de sɛn?", "What is your name?", "Good for meeting her family and friends"),
        ("Me din de...", "My name is...", "Introducing yourself — fill in your name"),
        ("Mo maakye", "Good morning (to a group/elder)", "Respectful group greeting — perfect for her family"),
    ],
    "food": [
        ("Aduane no yɛ dɛ", "The food is delicious", "CRITICAL phrase — always compliment the cooking"),
        ("Mepɛ aduane", "I want food / I'm hungry", "Asking for food"),
        ("Me kɔn de me", "I am hungry", "Direct way to say you're hungry"),
        ("Nsuo", "Water", "Asking for water"),
        ("Mama, aduane no yɛ dɛ paa", "Mama, the food is really delicious", "Say this to her mother — instant approval"),
    ],
}

# Teaching intent keywords
TEACH_KEYWORDS = ["teach me", "learn twi", "twi phrases", "how do you say", "how to say", "say in twi",
                  "impress her", "impress my girlfriend", "impress my wife", "impress his family",
                  "impress her family", "speak twi", "practice twi", "twi lessons", "twi words",
                  "some twi", "basic twi", "common twi", "useful twi", "romantic twi",
                  "love in twi", "flirt in twi", "greetings in twi", "test me"]


def resolve_timezone(tz_input: str) -> str:
    """Resolve timezone from alias or direct name."""
    if not tz_input:
        return "UTC"
    tz_lower = tz_input.lower().strip()
    return TIMEZONE_ALIASES.get(tz_lower, tz_input if "/" in tz_input else "UTC")


def web_search(query: str, max_results: int = 3) -> str:
    """Search the web using Tavily API.
    
    Limited to 3 results with short snippets to prevent context overload
    on the 8B model which degenerates with too much input.
    """
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
            
            # Tavily's answer is usually a good concise summary — prioritize it
            if data.get("answer"):
                results.append(f"**Summary:** {data['answer']}\n")
            
            for i, result in enumerate(data.get("results", [])[:max_results], 1):
                title = result.get("title", "No title")
                content = result.get("content", "")[:200]
                results.append(f"{i}. **{title}**: {content}\n")
            
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


def claude_answer(question: str, search_context: str, system_prompt: str = "") -> Optional[str]:
    """Use Claude to synthesize an answer from search results.
    
    The 8B Twi model can't reliably ground responses on provided context,
    so for factual queries with search results, we use Claude Haiku to
    produce a concise, accurate answer.
    
    Returns None if Claude is unavailable or fails (caller falls back to local model).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    
    try:
        # Use Ama's personality in the system prompt
        claude_system = system_prompt or "You are Ama, a friendly bilingual Twi-English AI assistant. You help people learn about Twi, Ghanaian culture, and answer general questions."
        
        claude_prompt = f"""Here is information from a web search:

{search_context}

Using ONLY the information above, answer this question concisely: {question}

Rules:
- Answer in 2-5 sentences
- Only state facts from the search results
- If the search results don't answer the question, say you couldn't find specific info
- Stay warm and conversational (you're Ama, a Twi-English AI assistant)
- Do NOT make up facts, events, or people
- Do NOT ask the user questions back
- Do NOT generate lists of topics"""

        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 200,
                "system": claude_system,
                "messages": [{"role": "user", "content": claude_prompt}],
            },
            timeout=15.0,
        )
        
        if response.status_code == 200:
            data = response.json()
            text = data.get("content", [{}])[0].get("text", "").strip()
            if text and len(text) > 10:
                return text
        else:
            print(f"Claude API error: {response.status_code} {response.text[:200]}")
        return None
    except Exception as e:
        print(f"Claude answer error: {e}")
        return None


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
    
    # Explicit search requests
    if any(kw in message_lower for kw in SEARCH_KEYWORDS):
        intent["needs_web_search"] = True
        if not intent["search_query"]:
            # If the message is just a bare search command ("search the web", "look it up"),
            # the raw message is useless as a search query — leave it empty for now,
            # and the vague-followup handler below will extract the real topic from context.
            bare_search_commands = ["search the web", "search online", "look it up", "google it",
                                    "search it", "search that", "web search", "go search",
                                    "can you search", "please search", "search"]
            is_bare = message_lower.strip().rstrip('!.?') in bare_search_commands
            if not is_bare:
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
        # Auto-trigger web search for document topics to avoid hallucination
        topic = message_lower
        for kw in sorted(FILE_CREATE_KEYWORDS, key=len, reverse=True):
            topic = topic.replace(kw, "")
        topic = topic.strip().strip('"').strip("'").strip()
        # Strip leading prepositions from search query
        for prep in ["about ", "on ", "for ", "regarding ", "of "]:
            if topic.startswith(prep):
                topic = topic[len(prep):]
        topic = topic.strip()
        if topic and len(topic) > 2:
            intent["needs_web_search"] = True
            intent["search_query"] = topic
    if any(kw in message_lower for kw in FILE_LIST_KEYWORDS):
        intent["needs_file_list"] = True
    if any(kw in message_lower for kw in FILE_VIEW_KEYWORDS):
        intent["needs_file_view"] = True
        file_id_match = re.search(r'[a-f0-9]{8}', message_lower)
        if file_id_match:
            intent["file_id"] = file_id_match.group()
    
    # Twi teaching intent
    if any(kw in message_lower for kw in TEACH_KEYWORDS):
        intent["needs_twi_teaching"] = True
        # Determine which category to teach
        if any(w in message_lower for w in ["love", "romantic", "girlfriend", "boyfriend", "wife", "husband", "impress her", "impress him", "flirt", "marry", "marriage", "wedding", "propose"]):
            intent["teach_category"] = "romantic"
        elif any(w in message_lower for w in ["family", "parents", "mother", "father", "elder", "respect", "in-law"]):
            intent["teach_category"] = "impress_family"
        elif any(w in message_lower for w in ["food", "eat", "cook", "hungry", "delicious"]):
            intent["teach_category"] = "food"
        elif any(w in message_lower for w in ["hello", "hi ", "greet", "morning", "evening", "goodbye", "bye"]):
            intent["teach_category"] = "greetings"
        else:
            intent["teach_category"] = "essentials"

    # Knowledge base
    twi_keywords = ["twi", "akan", "ghana", "ashanti", "kente", "adinkra", "akwaaba"]
    if any(kw in message_lower for kw in twi_keywords):
        intent["needs_knowledge"] = True

    # Auto-search for factual/knowledge questions the model can't answer reliably
    if not intent["needs_web_search"]:
        for pattern in KNOWLEDGE_PATTERNS:
            if re.search(pattern, message_lower):
                intent["needs_web_search"] = True
                intent["search_query"] = message
                break

    # Creator/identity detection
    if any(kw in message_lower for kw in CREATOR_KEYWORDS):
        intent["needs_creator_info"] = True
        # If user asks to search/fetch/learn more about creator, also trigger web tools
        action_words = ["search", "website", "look up", "tell me more", "learn more", "find", "fetch", "visit", "check"]
        if any(w in message_lower for w in action_words):
            intent["needs_web_fetch"] = True
            intent["url_to_fetch"] = "https://www.angeloasante.com"
            intent["needs_web_search"] = True
            intent["search_query"] = "Angelo Asante software engineer AI developer Ghana"
    
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
    
    def generate_response(self, prompt: str, context: str = "", has_search: bool = False, is_document: bool = False, is_teaching: bool = False) -> str:
        """Generate a response from the model."""
        if is_teaching and context:
            full_prompt = f"""A user wants to learn Twi. Here are VERIFIED Twi phrases you can teach from:

{context}

The user said: "{prompt}"

Teach them 3-5 of the most relevant phrases from the list above. For each phrase:
1. Write the Twi phrase in bold
2. Give the English meaning
3. Add a quick tip on pronunciation or when to use it

Be warm and encouraging. Keep it conversational, not like a textbook. Do NOT invent any Twi phrases — only use what's listed above."""
        elif is_document:
            if context:
                full_prompt = f"""You are writing a factual document. Here are REAL FACTS from web research:

{context}

Using ONLY the facts above, write a well-structured markdown document about: {prompt}

Rules:
- Use ## headers, bullet points, and bold text
- ONLY state facts found in the research data above
- NEVER write [Birthplace], [University Name], [Year], or any bracket placeholders
- If you don't know a specific detail, skip it entirely — do NOT guess or leave blanks
- Include real names, dates, companies, and achievements from the research data
- Write 4-6 sections with an introduction and conclusion

Document:"""
            else:
                full_prompt = f"""Write a well-structured markdown document about: {prompt}

Rules:
- Use ## headers, bullet points, and bold text
- Only state facts you are confident about
- NEVER write [Birthplace], [University Name], or any bracket placeholders
- If you don't know something, skip it — do NOT guess or leave blanks
- Write 4-6 sections with an introduction and conclusion

Document:"""
        elif context:
            if has_search:
                full_prompt = f"""Here is some information I found:

{context}

Using ONLY the information above, answer this question: {prompt}

Rules:
- Base your answer ONLY on the information provided above
- Include specific details, names, and facts from the sources
- Keep your answer concise (3-6 sentences)
- Do NOT make up information, events, or people
- Do NOT ask the user questions back
- Do NOT generate lists of unrelated topics"""
            else:
                full_prompt = f"{context}\n\nUser question: {prompt}"
        else:
            # If user explicitly asks for detail, wrap the prompt
            needs_detail = any(kw in prompt.lower() for kw in DETAIL_KEYWORDS)
            if needs_detail:
                full_prompt = f"{prompt}\n\nGive a thorough, detailed answer with specific facts, examples, and context. Use multiple paragraphs."
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
        
        input_len = inputs["input_ids"].shape[-1]
        
        # Scale generation: documents and detail queries need more tokens, casual chat stops naturally
        needs_detail = any(kw in prompt.lower() for kw in DETAIL_KEYWORDS)
        # Estimate appropriate response length from question length
        prompt_word_count = len(prompt.split())
        is_short_question = prompt_word_count < 12 and not needs_detail
        if is_document:
            max_tokens = 2048
            min_tokens = 300
        elif is_teaching:
            max_tokens = 768
            min_tokens = 150  # teaching needs room to list phrases
        elif has_search or needs_detail:
            # Short factual questions with search: keep responses concise
            max_tokens = 256 if is_short_question else 512
            min_tokens = 30 if is_short_question else 100
        else:
            # Casual chat: scale with question length
            max_tokens = 192 if is_short_question else 384
            min_tokens = 0  # let the model stop naturally
        
        # Higher repetition penalty to prevent repetitive text
        rep_penalty = 1.4 if has_search else (1.3 if (is_document or is_teaching) else 1.2)
        # Lower temperature for search-backed and document responses to keep model grounded
        temp = 0.4 if has_search else (0.5 if (is_document or is_teaching) else 0.7)
        
        with torch.no_grad():
            gen_kwargs = dict(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temp,
                top_p=0.9,
                do_sample=True,
                repetition_penalty=rep_penalty,
                pad_token_id=self.tokenizer.pad_token_id,
            )
            if min_tokens > 0:
                gen_kwargs["min_new_tokens"] = min_tokens
            outputs = self.model.generate(**gen_kwargs)
        
        # Only decode newly generated tokens (skip the input prompt)
        new_tokens = outputs[0][input_len:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        
        # 0. Truncate at first </s> or <s> token (model continuation artifacts)
        for stop_tok in ['</s>', '<s>', '<|end|>', '<|eot_id|>', '<|im_end|>', '<|endoftext|>']:
            if stop_tok in response:
                response = response[:response.index(stop_tok)].strip()
        
        # 0b. Truncate at fake turn markers (model hallucinating a continued conversation)
        # The model sometimes generates "User question:", "AI response:", "User:", etc.
        turn_markers = [
            '\nUser question:', '\nUser:', '\nHuman:', '\nAI response:', '\nAssistant:',
            '\nAma:', '\nNote:', '\nYour response', '\nPlease make your response',
            '\nRemember:', '\nDisclaimer:',
        ]
        for marker in turn_markers:
            if marker in response:
                response = response[:response.index(marker)].strip()
        
        # Clean up model artifacts: hashtags, emojis, degenerate text
        # 1. Remove inline hashtag sequences (#Word #Word2 etc.) but keep markdown headers (# Title)
        # Catch both adjacent (#Word#Word2) and space-separated (#Word #Word2) hashtags
        response = re.sub(r'(?<!\n)(?<!^)\s*(?:#[A-Za-z]\w*\s*){2,}', '', response, flags=re.MULTILINE)
        # Also remove single standalone hashtags at end of response
        response = re.sub(r'\s*#[A-Za-z]\w*\s*$', '', response)
        
        # 2. Remove excessive emoji sequences (3+ emojis in a row)  
        emoji_pattern = r'[\U0001F300-\U0001F9FF\U00002702-\U000027B0\U0000FE00-\U0000FE0F\U0000200D\U00002600-\U000026FF\U00002B50-\U00002B55\U0000203C-\U00003299]'
        response = re.sub(f'({emoji_pattern}\\s*){{{3},}}', '', response)
        
        # 3. Remove bracket placeholder patterns like [Birthplace], [University Name], [Year]
        # Remove entire sentences containing placeholders
        response = re.sub(r'[^.!?\n]*\[[A-Z][a-zA-Z\s]*\][^.!?\n]*[.!?]?\s*', '', response)
        # Also remove any remaining standalone bracket placeholders
        response = re.sub(r'\s*\[[A-Z][a-zA-Z\s]*\]\s*', ' ', response)
        
        # 4. Detect degenerate run-on text (words > 40 chars without spaces) and truncate there
        degen_match = re.search(r'\b\w{40,}\b', response)
        if degen_match:
            response = response[:degen_match.start()].strip()
        
        # 4a. Detect gibberish / incoherent output (ALL-CAPS nonsense, fake words, entropy collapse)
        is_gibberish = False
        resp_words = response.split()
        if len(resp_words) > 8:
            # Check 1: High ALL-CAPS ratio (>40% of words are ALL-CAPS, 3+ chars each)
            caps_words = [w for w in resp_words if w.isupper() and len(w) >= 3 and w.isalpha()]
            alpha_words = [w for w in resp_words if w.isalpha() and len(w) >= 3]
            if alpha_words and len(caps_words) / len(alpha_words) > 0.4:
                is_gibberish = True
            
            # Check 2: Too many non-dictionary-looking words (consonant clusters, no vowels, etc.)
            # Real English/Twi words have vowels. Gibberish like "BAIKETEDED", "DETEREDED" has weird patterns
            if not is_gibberish:
                nonsense_count = 0
                vowels = set('aeiouɛɔAEIOUƐƆ')
                for w in alpha_words:
                    w_lower = w.lower()
                    # Skip very short words
                    if len(w_lower) < 4:
                        continue
                    # Check for words with very unusual letter patterns
                    vowel_ratio = sum(1 for c in w_lower if c in vowels) / len(w_lower)
                    # Words with < 15% vowels or > 70% vowels are suspicious
                    if vowel_ratio < 0.15 or vowel_ratio > 0.7:
                        nonsense_count += 1
                    # Words ending in "eded", "eded" pattern (model degeneration artifact)
                    elif re.search(r'(.)\1{2,}', w_lower):  # Triple repeated chars
                        nonsense_count += 1
                    elif re.search(r'(ed|ing|tion){2,}', w_lower):  # Repeated suffixes
                        nonsense_count += 1
                long_alpha = [w for w in alpha_words if len(w) >= 4]
                if long_alpha and nonsense_count / len(long_alpha) > 0.3:
                    is_gibberish = True
            
            # Check 3: Same ALL-CAPS word appearing in weird non-sentence structure
            # If more than 5 ALL-CAPS words in a row (not in an acronym context)
            if not is_gibberish:
                caps_streak = 0
                max_caps_streak = 0
                for w in resp_words:
                    if w.isupper() and len(w) >= 3:
                        caps_streak += 1
                        max_caps_streak = max(max_caps_streak, caps_streak)
                    else:
                        caps_streak = 0
                if max_caps_streak >= 5:
                    is_gibberish = True
            
            # Check 4: Response looks like random fragments / numbered gibberish
            # (e.g., "24/06. Speak English! 25/05. Know what you see 26/29.")
            if not is_gibberish:
                # Count ratio of numbers/dates to actual content words
                num_fragments = len(re.findall(r'\d+/\d+', response))
                if num_fragments >= 4:
                    is_gibberish = True
            
            # Check 5: Single word repeated more than 5 times total (not a common word)
            if not is_gibberish:
                from collections import Counter as _Counter
                wc = _Counter(w.lower().strip('!.,?;:') for w in resp_words if len(w) >= 3)
                common_words = {'the', 'and', 'for', 'you', 'are', 'that', 'with', 'this', 'from', 'have', 'but', 'not', 'was', 'can', 'will', 'been', 'has', 'its', 'one', 'all', 'they', 'your', 'her', 'his', 'she', 'ama', 'twi', 'ghana'}
                for word, count in wc.most_common(3):
                    if word not in common_words and count >= 5 and count / len(resp_words) > 0.15:
                        is_gibberish = True
                        break
        
        # Check 6: Engagement bait / rambling degeneration
        # Catches fluent but off-topic responses that ask questions back, say "share your stories" etc.
        if not is_gibberish and len(resp_words) > 30:
            engagement_bait_phrases = [
                'share your', 'tell us', 'don\'t hold back', 'what interesting',
                'any fun plans', 'did you meet anyone', 'creative projects',
                'your thoughts?', 'your stories', 'am i explaining', 'help clarify',
                'please help', 'diverse perspectives', 'let me know what you think',
                'what do you think about', 'have you ever experienced',
                'i\'d love to hear', 'please share', 'drop a comment',
                'like and subscribe', 'follow me', 'stay tuned',
            ]
            bait_count = sum(1 for phrase in engagement_bait_phrases if phrase in response.lower())
            # Also count question marks — more than 4 in a casual response is engagement bait
            question_marks = response.count('?')
            if bait_count >= 2 or (bait_count >= 1 and question_marks >= 4):
                is_gibberish = True
        
        # Check 7: Comma-list degeneration — model generates endless comma-separated topic lists
        # e.g. "psychology, philosophy, spirituality, motivation, inspiration, creativity..."
        if not is_gibberish:
            # Find all sequences of 8+ comma-separated items
            comma_runs = re.findall(r'(?:[^,\n]{2,40},\s*){7,}[^,\n]{2,40}', response)
            if comma_runs:
                longest_run = max(len(r.split(',')) for r in comma_runs)
                if longest_run >= 10:
                    is_gibberish = True
                elif longest_run >= 6:
                    # Moderate list — truncate the list portion but keep surrounding text
                    for run in comma_runs:
                        items = run.split(',')
                        if len(items) >= 6:
                            truncated_list = ', '.join(items[:4]).strip()
                            response = response.replace(run, truncated_list + '.')
        
        # Check 8: Fake conversation hallucination — model generates dialogue within its response
        # Detects patterns like "When did I become your wife?" or "I think back to our wedding day"
        if not is_gibberish and len(resp_words) > 20:
            fake_convo_markers = [
                r'when did [iI] become your',
                r'[iI] think back to',
                r'we just got married',
                r'we exchanged vows',
                r'we laughed and',
                r'everyone danced',
                r'(?:Me|My) papa!',
                r'(?:Me|My) mama!',
                r'\bFrétt\b',
                r'\bdaaa\b',
            ]
            fake_hits = sum(1 for p in fake_convo_markers if re.search(p, response, re.IGNORECASE))
            if fake_hits >= 2:
                is_gibberish = True
            elif fake_hits == 1:
                # Single hit — truncate at that point
                for p in fake_convo_markers:
                    m = re.search(p, response, re.IGNORECASE)
                    if m:
                        cut_point = response.rfind('.', 0, m.start())
                        if cut_point > 50:
                            response = response[:cut_point + 1].strip()
                        break
        
        # Check 9: Response is way too long for a casual question (>500 chars with no search context)
        # This catches the model going on tangents
        if not is_gibberish and not has_search and not is_document and not is_teaching:
            if len(response) > 600 and response.count('?') >= 3:
                # Truncate to first 2-3 complete sentences
                sentences = re.split(r'(?<=[.!?])\s+', response)
                if len(sentences) > 3:
                    truncated = ' '.join(sentences[:3])
                    if len(truncated) > 50:
                        response = truncated
        
        if is_gibberish:
            response = ""  # Will be caught by retry/fallback logic
        
        # 4b. Detect repeated short phrases/words (e.g., "Angelo Angelo Angelo" or "hello hello hello")
        # Catches any word or 2-3 word phrase repeated 4+ times consecutively
        def collapse_repeated_phrases(text):
            # Single word repeated 4+ times: "word word word word..." → "word"
            text = re.sub(r'\b(\w+)(?:\s+\1){3,}\b', r'\1', text, flags=re.IGNORECASE)
            # 2-3 word phrase repeated 3+ times
            text = re.sub(r'((?:\w+\s+){1,3})(?:\1){2,}', r'\1', text, flags=re.IGNORECASE)
            # Repeated sentences (same sentence 3+ times)
            text = re.sub(r'([^.!?\n]{10,}[.!?])\s*(?:\1\s*){2,}', r'\1', text, flags=re.IGNORECASE)
            return text
        response = collapse_repeated_phrases(response)
        
        # 4c. If response is still suspiciously repetitive (>60% of text is the same 1-3 words), truncate
        words = response.split()
        if len(words) > 20:
            from collections import Counter
            word_counts = Counter(w.lower() for w in words)
            most_common_word, most_common_count = word_counts.most_common(1)[0]
            if most_common_count > len(words) * 0.4 and most_common_word not in {'the', 'a', 'an', 'is', 'to', 'in', 'of', 'and', 'for', 'it', 'on', 'that', 'with', 'be', 'you', 'i', 'no', 'wo', 'me', 'ne', 'na', 'ɛ', 'yɛ'}:
                # Highly repetitive — keep only up to the first natural stopping point
                first_end = -1
                for end_char in ['. ', '.\n', '! ', '!\n', '? ', '?\n']:
                    pos = response.find(end_char)
                    if pos > 20 and (first_end == -1 or pos < first_end):
                        first_end = pos
                if first_end > 0:
                    response = response[:first_end + 1].strip()
                else:
                    # Just take first 100 chars
                    response = response[:100].strip()
        
        # 5. Remove repeated paragraphs (same text block appearing multiple times)
        paragraphs = response.split('\n\n')
        seen = set()
        unique_paragraphs = []
        for p in paragraphs:
            # Normalize whitespace for comparison
            normalized = ' '.join(p.split()).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_paragraphs.append(p)
            elif not normalized:
                unique_paragraphs.append(p)  # keep blank separators
        response = '\n\n'.join(unique_paragraphs)
        
        # 6. Trim trailing incomplete sentence fragments
        response = response.strip()
        if response and response[-1] not in '.!?:)\n"*' and len(response) > 200:
            last_end = max(response.rfind('. '), response.rfind('.\n'),
                          response.rfind('! '), response.rfind('!\n'),
                          response.rfind('? '), response.rfind('?\n'),
                          response.rfind('.'), response.rfind('!'), response.rfind('?'))
            if last_end > len(response) * 0.4:
                response = response[:last_end + 1]
        
        # 7. Trim trailing incomplete sentence (no period at end and response > 100 chars)
        response = response.strip()
        if response and len(response) > 100 and response[-1] not in '.!?:)\n"*':
            last_end = max(response.rfind('. '), response.rfind('.\n'),
                          response.rfind('! '), response.rfind('!\n'),
                          response.rfind('? '), response.rfind('?\n'),
                          response.rfind('.'), response.rfind('!'), response.rfind('?'))
            if last_end > 20:
                response = response[:last_end + 1]
        
        # 8. Remove filler/padding sentences the model adds despite system prompt instructions
        filler_patterns = [
            r'\s*Would you like (?:more info|to know more|me to|to learn|to explore)[^.!?\n]*[.!?]?\s*$',
            r'\s*Let me (?:know|help)[^.!?\n]*[.!?]?\s*$',
            r'\s*Feel free to (?:ask|explore|reach out)[^.!?\n]*[.!?]?\s*$',
            r'\s*(?:What would you like|What else|Anything else)[^.!?\n]*[.!?]?\s*$',
            r'\s*(?:I\'m here to help|Just ask|Don\'t hesitate)[^.!?\n]*[.!?]?\s*$',
        ]
        for pattern in filler_patterns:
            response = re.sub(pattern, '', response, flags=re.IGNORECASE)
        
        return response.strip()
    
    def _extract_topic_from_context(self, memory_context: str) -> str:
        """Extract the main topic from recent conversation messages.
        
        Used when the user says something vague like 'tell me more about it'
        so we can search for the actual topic instead of the vague phrase.
        """
        if not memory_context:
            return ""
        
        # Look for the last substantive user message (not a short affirmative)
        user_messages = []
        for line in memory_context.split('\n'):
            line = line.strip()
            if line.startswith('User:'):
                msg = line[5:].strip()
                # Skip very short/vague messages
                if len(msg) > 15 and not any(vague in msg.lower() for vague in ['tell me more', 'go on', 'continue', 'elaborate', 'what else', 'more about']):
                    user_messages.append(msg)
        
        # Also check Ama's last response for topic clues
        ama_messages = []
        for line in memory_context.split('\n'):
            line = line.strip()
            if line.startswith('Ama:'):
                ama_messages.append(line[4:].strip())
        
        # The last substantive user message is the best topic indicator
        if user_messages:
            return user_messages[-1]
        
        # Fallback: extract nouns/topic from Ama's last response
        if ama_messages:
            last_ama = ama_messages[-1]
            # Take first sentence as topic hint
            first_sent = re.split(r'[.!?]', last_ama)[0].strip()
            if len(first_sent) > 10:
                return first_sent
        
        return ""

    def _parse_enhanced_input(self, raw_input: str) -> tuple:
        """Parse enhanced input from frontend into (current_message, memory_context).
        
        The frontend sends:
          [User Facts]\n...\n\n[Recent Messages]\n...\n\nCurrent message: actual user text
        
        Returns (current_message, memory_context_string)
        """
        if "Current message:" in raw_input:
            parts = raw_input.rsplit("Current message:", 1)
            memory_context = parts[0].strip()
            current_message = parts[1].strip()
            return current_message, memory_context
        return raw_input.strip(), ""

    def _format_memory_for_model(self, memory_context: str) -> str:
        """Convert frontend memory context into a clean model-friendly format.
        
        Also truncates the context if it's too long to prevent model degeneration.
        The 8B model struggles with very long contexts on casual queries.
        """
        if not memory_context:
            return ""
        
        # Truncate context to prevent overwhelming the model
        # Keep user profile + recent messages, drop RAG/summary if too long
        MAX_CONTEXT_CHARS = 2000
        if len(memory_context) > MAX_CONTEXT_CHARS:
            # Prioritize: [About This User] > [Recent Messages] > everything else
            sections = {}
            current_section = "other"
            current_lines = []
            for line in memory_context.split('\n'):
                if line.startswith('[') and line.endswith(']'):
                    if current_lines:
                        sections[current_section] = '\n'.join(current_lines)
                    current_section = line
                    current_lines = [line]
                else:
                    current_lines.append(line)
            if current_lines:
                sections[current_section] = '\n'.join(current_lines)
            
            # Rebuild with priority sections only
            priority_order = ['[About This User]', '[Recent Messages]', '[User Facts]', '[Previous Context Summary]', '[Relevant Past Conversations]', 'other']
            trimmed_parts = []
            total_len = 0
            for section_key in priority_order:
                if section_key in sections and total_len < MAX_CONTEXT_CHARS:
                    text = sections[section_key]
                    remaining = MAX_CONTEXT_CHARS - total_len
                    if len(text) > remaining:
                        text = text[:remaining].rsplit('\n', 1)[0]  # cut at line boundary
                    trimmed_parts.append(text)
                    total_len += len(text)
            memory_context = '\n\n'.join(trimmed_parts)
        
        lines = []
        
        # Check if there's a user profile section — give it special emphasis
        if "[About This User]" in memory_context:
            lines.append("IMPORTANT — Here is what you know about this user from past conversations. Use this to personalize your responses naturally. Do NOT repeat this information verbatim or say 'I know that...' — just let it inform how you interact:")
        else:
            lines.append("The following is background context about this user and conversation. Use it naturally but do NOT repeat it verbatim:")
        
        lines.append("")
        lines.append(memory_context)
        return "\n".join(lines)

    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process inference request with agentic capabilities."""
        raw_input = data.get("inputs", "")
        params = data.get("parameters", {})
        timezone = params.get("timezone", "UTC")
        explicit_action = params.get("action")
        action_data = params.get("data", {})
        
        # Parse enhanced input: separate current message from memory context
        message, memory_context = self._parse_enhanced_input(raw_input)
        
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
        
        # Vague follow-up resolution: if user says "tell me more", "elaborate", etc.
        # OR if user says "search the web" without a topic — extract real topic from context
        message_lower_stripped = message.lower().strip().rstrip('!.?')
        is_vague_followup = any(vague in message_lower_stripped for vague in FOLLOWUP_PHRASES)
        
        # Also treat bare search commands as vague follow-ups needing topic extraction
        bare_search_commands = ["search the web", "search online", "look it up", "google it",
                                "search it", "search that", "web search", "go search",
                                "can you search", "please search", "search"]
        is_bare_search = message_lower_stripped in bare_search_commands
        
        if (is_vague_followup or is_bare_search) and memory_context:
            real_topic = self._extract_topic_from_context(memory_context)
            if real_topic:
                # Use the real topic for search instead of the vague phrase
                intent["needs_web_search"] = True
                intent["search_query"] = real_topic + " detailed information"
                # Also check if we should trigger knowledge base
                if any(kw in real_topic.lower() for kw in ["twi", "akan", "ghana", "ashanti", "kente", "adinkra"]):
                    intent["needs_knowledge"] = True
        
        # Follow-up teaching: if user says a short affirmative and recent context shows Ama just offered to teach more
        affirmatives = ["yes", "yea", "yeah", "yep", "yesss", "sure", "ok", "okay", "please", "go ahead", "lets go", "let's go", "more", "next", "continue", "absolutely", "definitely", "of course"]
        is_short_affirm = message.lower().strip().rstrip('!.') in affirmatives or len(message.strip()) < 15
        if is_short_affirm and not intent.get("needs_twi_teaching") and memory_context:
            # Extract the LAST Ama message from memory context to check for teaching offers
            last_ama_msg = ""
            for line in reversed(memory_context.split('\n')):
                if line.strip().startswith('Ama:'):
                    last_ama_msg = line.strip().lower()
                    break
            # Also check the last few lines in case the outro spans multiple lines
            last_chunk = '\n'.join(memory_context.split('\n')[-6:]).lower()
            check_text = last_ama_msg + " " + last_chunk
            
            # Map specific outro phrases to the NEXT category they offer
            # These must match the exact category_outros in the hardcoded response builder
            follow_up_map = [
                ("greet her family", "impress_family"),
                ("greet your family", "impress_family"),
                ("greet the family", "impress_family"),
                ("food-related", "food"),
                ("food phrases", "food"),
                ("romantic phrases", "romantic"),
                ("romantic twi", "romantic"),
                ("greetings or romantic", "greetings"),
                ("learn greetings", "greetings"),
                ("essential phrases", "essentials"),
                ("want to learn more", "essentials"),
                ("teach you more", "essentials"),
            ]
            
            matched_category = None
            for phrase, category in follow_up_map:
                if phrase in check_text:
                    matched_category = category
                    break
            
            if matched_category:
                intent["needs_twi_teaching"] = True
                intent["teach_category"] = matched_category
                intent["_is_followup"] = True
        
        # Gather context from tools
        context_parts = []
        tools_used = []
        tool_results = {}
        
        # Creator/identity — inject hardcoded context (internal, not shown as a tool to user)
        if intent.get("needs_creator_info"):
            context_parts.append(f"**VERIFIED CREATOR INFORMATION (this overrides any training data):**\n{CREATOR_INFO}")

        # Web fetch if URL detected
        if intent["needs_web_fetch"] and intent["url_to_fetch"]:
            fetch_result = web_fetch(intent["url_to_fetch"])
            tools_used.append("web_fetch")
            tool_results["web_fetch"] = {"url": intent["url_to_fetch"], "content": fetch_result}
            # For creator queries, merge fetched content into creator info instead of separate context
            if intent.get("needs_creator_info"):
                context_parts.append(f"**Additional details from his website ({intent['url_to_fetch']}):**\n{fetch_result}")
            else:
                context_parts.append(f"**Webpage Content:**\n{fetch_result}")
        
        # Web search (skip generic search if creator info already provides the answer)
        if intent["needs_web_search"] and intent["search_query"]:
            # Don't do a generic web search when we already have hardcoded creator info
            # (unless user explicitly asked to search/fetch, which sets its own search_query)
            skip_search = intent.get("needs_creator_info") and not intent.get("needs_web_fetch")
            if not skip_search:
                search_result = web_search(intent["search_query"])
                tools_used.append("web_search")
                tool_results["web_search"] = {"query": intent["search_query"], "results": search_result}
                if intent.get("needs_creator_info"):
                    context_parts.append(f"**More details from web search:**\n{search_result}")
                else:
                    context_parts.append(f"**Web Search Results:**\n{search_result}")
        
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
        
        # Twi teaching — inject only a few verified phrases (small context = better model output)
        if intent.get("needs_twi_teaching"):
            category = intent.get("teach_category", "essentials")
            phrases = TWI_PHRASES.get(category, TWI_PHRASES["essentials"])
            # Cycle through phrases using a hash of the message so "teach me more" gives different ones
            phrase_offset = hash(message.lower().strip()) % max(1, len(phrases) - 3)
            selected = phrases[phrase_offset:phrase_offset + 4]
            if len(selected) < 4:
                selected = phrases[:4]  # wrap around
            phrase_text = "\n".join([f'- "{twi}" = "{eng}" ({note})' for twi, eng, note in selected])
            teaching_context = f"""VERIFIED TWI PHRASES to teach the user:\n{phrase_text}\n\nTeach 3-4 of these. For each: give the Twi, the English meaning, and when to use it. Be warm and conversational."""
            context_parts.append(teaching_context)
            tools_used.append("twi_phrases")
            tool_results["twi_phrases"] = {"category": category}
            # Store selected phrases for hardcoded response
            intent["_selected_phrases"] = selected

        # Knowledge base — skip if teaching Twi OR web search already provides context
        # The 8B model degenerates with too much context, so avoid double-stacking
        if intent["needs_knowledge"] and not intent.get("needs_twi_teaching") and not intent.get("needs_web_search"):
            kb_result = search_knowledge_base(message)
            if kb_result:
                # Truncate knowledge base to prevent context overload
                if len(kb_result) > 500:
                    kb_result = kb_result[:500].rsplit('\n', 1)[0]
                context_parts.append(f"**Cultural Knowledge:**\n{kb_result}")
                tools_used.append("knowledge_base")
                tool_results["knowledge_base"] = kb_result
        
        # Combine tool context with memory context
        # Memory context goes first (background), then tool results (foreground)
        all_context_parts = []
        if memory_context:
            all_context_parts.append(self._format_memory_for_model(memory_context))
        all_context_parts.extend(context_parts)
        
        context = "\n\n".join(all_context_parts) if all_context_parts else ""
        has_search = "web_search" in tools_used or "web_fetch" in tools_used or intent.get("needs_creator_info", False)
        is_document = intent.get("needs_file_create", False)
        is_teaching = intent.get("needs_twi_teaching", False)
        
        # For teaching requests, ALWAYS use hardcoded curated phrases
        # The model can't reliably teach from structured data — it generates garbage
        if is_teaching and intent.get("_selected_phrases"):
            selected = intent["_selected_phrases"]
            category = intent.get("teach_category", "essentials")
            is_followup = intent.get("_is_followup", False)
            
            # Different intros for first-time vs follow-up teaching
            if is_followup:
                followup_intros = {
                    "romantic": "Okay, let's get into the romantic stuff:",
                    "greetings": "Alright! Here are some proper Twi greetings:",
                    "essentials": "Nice! Here are some everyday Twi basics:",
                    "impress_family": "Love this energy! Here's how to impress her family:",
                    "food": "Great choice! Food is everything in Ghanaian culture:",
                }
                intro = followup_intros.get(category, "Here are some more Twi phrases:")
            else:
                first_intros = {
                    "romantic": "Congrats! Here are some sweet Twi phrases to impress her:",
                    "greetings": "Let's start with some essential Twi greetings:",
                    "essentials": "Here are some must-know Twi phrases:",
                    "impress_family": "Meeting the family? These phrases will earn you major points:",
                    "food": "Food is a big deal in Ghanaian culture! Here are some useful phrases:",
                }
                intro = first_intros.get(category, "Here are some Twi phrases for you:")
            
            lines = [intro, ""]
            for twi, eng, note in selected[:4]:
                lines.append(f"**{twi}** = \"{eng}\"")
                lines.append(f"  {note}")
                lines.append("")
            
            # Outros that clearly name the NEXT category — these must match follow_up_map
            category_outros = {
                "romantic": "Try these out on her! Want me to teach you how to greet her family in Twi?",
                "greetings": "Practice these and you'll sound natural! Want to learn some romantic phrases next?",
                "essentials": "These will get you far! Want to learn greetings or romantic phrases?",
                "impress_family": "Her family will be impressed! Want to learn some food-related phrases too?",
                "food": "Complimenting the cooking is a shortcut to their hearts! Want to learn some essential phrases?",
            }
            lines.append(category_outros.get(category, "Want me to teach you more?"))
            response = "\n".join(lines)
        else:
            # For factual queries with search results, use Claude to synthesize the answer
            # The 8B Twi model cannot reliably ground itself on provided context
            if has_search and not is_document and not is_teaching and "web_search" in tools_used:
                # Build search-only context for Claude (skip memory to keep it focused)
                search_context = "\n\n".join(context_parts) if context_parts else context
                claude_response = claude_answer(message, search_context, SYSTEM_PROMPT)
                if claude_response:
                    response = claude_response
                else:
                    # Claude unavailable — fall back to local model
                    response = self.generate_response(message, context, has_search=has_search, is_document=is_document, is_teaching=is_teaching)
            else:
                response = self.generate_response(message, context, has_search=has_search, is_document=is_document, is_teaching=is_teaching)
        
        # Retry/fallback if model produced gibberish (empty after cleanup)
        if not response or len(response.strip()) < 5:
            # Attempt 1: If we didn't have web search context, try adding it via Claude
            if "web_search" not in tools_used:
                try:
                    search_result = web_search(message)
                    if search_result:
                        tools_used.append("web_search")
                        tool_results["web_search"] = {"query": message, "results": search_result}
                        # Try Claude with the search results
                        claude_resp = claude_answer(message, search_result, SYSTEM_PROMPT)
                        if claude_resp:
                            response = claude_resp
                        else:
                            retry_context = f"**Web Search Results:**\n{search_result}"
                            if context:
                                retry_context = context + "\n\n" + retry_context
                            response = self.generate_response(message, retry_context, has_search=True, is_document=is_document, is_teaching=is_teaching)
                except Exception:
                    pass
            
            # Attempt 2: Try with NO memory context (just the raw question) and lower temperature
            if not response or len(response.strip()) < 5:
                response = self.generate_response(message, "", has_search=False, is_document=False, is_teaching=False)
            
            # Final fallback: safe hardcoded response
            if not response or len(response.strip()) < 5:
                response = "I'm having a bit of trouble with that one right now. Could you try rephrasing your question? I want to make sure I give you a good answer."
        
        # If user asked to create a document, save the response as a file
        if intent.get("needs_file_create"):
            # Extract a title from the message for the filename
            title_words = message.lower()
            for strip_phrase in sorted(FILE_CREATE_KEYWORDS, key=len, reverse=True):
                title_words = title_words.replace(strip_phrase, "")
            title_words = title_words.strip().strip('"').strip("'").strip()
            # Strip leading prepositions
            for prep in ["about ", "on ", "for ", "regarding ", "of "]:
                if title_words.startswith(prep):
                    title_words = title_words[len(prep):]
            title_words = title_words.strip()
            if not title_words:
                title_words = "document"
            # Create filename from title
            safe_title = re.sub(r'[^a-zA-Z0-9\s]', '', title_words).strip()
            safe_title = re.sub(r'\s+', '_', safe_title)[:50]
            filename = f"{safe_title}.md"
            
            file_result = create_file(filename, response)
            tools_used.append("create_file")
            tool_results["create_file"] = {
                "file_id": file_result["file_id"],
                "filename": filename,
                "content": response,
                "size": len(response)
            }
        
        return {
            "success": True,
            "response": response,
            "tools_used": tools_used,
            "tool_results": tool_results,
            "timezone": resolve_timezone(timezone)
        }
