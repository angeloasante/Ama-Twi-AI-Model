"""
Modal serving endpoint for Twi AI (Ama).
Full agentic pipeline: intent detection, tools (web search, image search,
time, Twi teaching, file creation, Claude fallback), and Qwen3.5-9B generation.
All API keys live here as Modal secrets — frontend is a thin proxy.
"""

import modal
import os
import re
import json
import random
from datetime import datetime

MODEL_ID = "travis-moore/twi-qwen-v1-merged"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "torch>=2.3.0",
        "git+https://github.com/huggingface/transformers.git",
        "accelerate>=0.34.0",
        "safetensors",
        "sentencepiece",
        "hf-transfer",
        "fastapi[standard]",
        "httpx",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

app = modal.App("twi-qwen", image=image)

with image.imports():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import httpx

# ─── Constants ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Ama (Twi AI), a powerful bilingual AI assistant fluent in both Twi and English.
Your name is Ama. You were created by Angelo Asante (also known as Travis Moore) www.angeloasante.com, a software engineer and AI developer — NOT a musician.

YOU ARE A FULL GENERAL-PURPOSE AI. You can do EVERYTHING:
- Write production-quality code in Python, JavaScript, TypeScript, React, Next.js, Go, Rust, and more
- Teach ANY subject: coding, math, physics, chemistry, biology, history, economics, philosophy
- Solve complex problems step by step with real working examples
- Explain concepts clearly with analogies, diagrams (in text), and progressive depth
- Write essays, stories, documentation, emails, cover letters, business plans
- Debug code, review architecture, suggest best practices
- Help with homework, exam prep, interview prep, career advice
- Discuss current events, culture, relationships, life advice
- You are especially knowledgeable about Twi language and Ghanaian/Akan culture

WHEN SOMEONE ASKS YOU TO TEACH OR EXPLAIN SOMETHING:
- ACTUALLY TEACH IT. Give real, substantive content — not a 2-sentence summary.
- For coding topics: Show REAL code examples with comments. Explain what each part does. Show input/output.
- For math/science: Show the formulas, work through examples step by step, explain the intuition.
- For concepts: Define it, explain why it matters, give examples, show how it connects to things they know.
- Use markdown formatting: ## headers, **bold** for key terms, ```code blocks```, numbered lists for steps.
- Aim for depth. A "teach me React" response should be 400+ words with actual JSX code examples.
- NEVER give a lazy 2-3 sentence answer when someone asks to learn something. That is your WORST failure mode.

YOUR PERSONALITY:
- Warm, witty, patient, encouraging — like a brilliant Ghanaian auntie who happens to be a senior engineer.
- Playful humor but genuinely helpful. You take the teaching seriously even if your tone is casual.
- Proud of Akan/Ghanaian culture and love sharing it authentically.
- Natural speech — not a textbook, not a robot.

RESPONSE RULES:
- Match the user's energy. "hi" = warm 1-2 sentence greeting. "teach me React" = thorough tutorial.
- NEVER ask more than one question back. Ideally ask zero — just answer.
- Do NOT generate hashtags, engagement bait, or social media style content.
- Do NOT invent Twi words or phrases. If unsure, say it in English.
- NEVER say "I can't help with that" or "that's not my area". You CAN help with everything.
- When you have conversation history, USE IT. Reference what was discussed before. Be contextually aware.
- NEVER spam emojis. Maximum 2-3 emojis per response. NO flag emojis ever. NO rows of emojis. Keep it clean.
- NEVER ask "what is that?" or "what does it do?" — you have web search tools. USE the information given to you to answer directly.
- When you receive web search results or tool results in your context, USE THEM to give a substantive answer. Do not ignore them.

LANGUAGE RULES:
- If the user writes in English, respond in English but sprinkle in Twi naturally.
- If the user writes in Twi, respond in Twi.
- For technical topics (code, math, science), use English for clarity but keep your Ghanaian personality.
- Default to the language the user is using."""

NEWS_KEYWORDS = ["news", "latest news", "current events", "happening now", "what happened", "breaking", "headlines", "2024", "2025", "2026"]
POLITICAL_KEYWORDS = ["president", "vice president", "government", "minister", "election", "parliament"]
SEARCH_KEYWORDS = ["search for", "search about", "look up", "find out", "google", "tell me more", "learn more", "find information", "what do you know about", "search the web", "search online", "search it", "search that", "web search", "go search", "can you search", "please search"]
TIME_KEYWORDS = ["time", "date", "what day", "what's the time", "current time"]
IMAGE_KEYWORDS = ["image of", "picture of", "photo of", "show me a photo", "show me a picture", "show me an image", "show me images", "images of", "pictures of"]
FILE_CREATE_KEYWORDS = ["create a file", "make a file", "write a file", "save to file", "create file", "create a document", "make a document", "write a document", "create document", "create documentation", "write documentation", "make documentation", "write me a", "draft a"]
# Regex patterns for flexible file creation matching (handles typos, tenses)
FILE_CREATE_PATTERNS = [
    r"\b(?:create|created|make|write|draft|build|generate|put together|prepare)\s+(?:a\s+)?(?:document|doc|file|report|essay|paper|summary|guide|article|writeup|write-up)\b",
    r"\b(?:document|write up|write-up|summarize|summarise)\s+(?:about|on|for|regarding|bout)\b",
]
CREATOR_KEYWORDS = ["angelo asante", "travis moore", "who created", "who made you", "who built you", "your creator", "your developer", "who designed you", "angeloasante"]
# "teach me" alone is too broad — only match when paired with Twi/language context
TEACH_KEYWORDS_EXACT = ["learn twi", "twi phrases", "how do you say", "how to say", "say in twi", "impress her", "impress my girlfriend", "impress my wife", "impress his family", "impress her family", "speak twi", "practice twi", "twi lessons", "twi words", "some twi", "basic twi", "common twi", "useful twi", "romantic twi", "love in twi", "flirt in twi", "greetings in twi"]
# "teach me" only triggers if combined with Twi/language-related words
TEACH_ME_CONTEXT = ["twi", "akan", "ghana", "phrase", "word", "greeting", "say", "language", "romantic", "love", "food", "family"]
FOLLOWUP_PHRASES = ["tell me more", "more about it", "more about that", "go on", "continue", "elaborate", "explain more", "keep going", "what else", "more details", "more info", "tell me about it", "more on that", "expand on that"]

# Educational intent — these trigger thorough teaching mode
EDUCATION_KEYWORDS = [
    "teach me", "explain", "how to", "how do i", "tutorial", "what is a ",
    "what are ", "learn about", "help me understand", "show me how",
    "walk me through", "break down", "guide me", "step by step",
    "difference between", "how does", "why does", "when to use",
    "best practices", "introduction to", "intro to", "basics of",
    "fundamentals", "help me learn", "i want to learn",
]

def is_educational_query(message: str) -> bool:
    """Detect if user is asking to be taught something (non-Twi)."""
    lower = message.lower()
    # Don't intercept Twi teaching — that's handled by the phrase system
    if any(ctx in lower for ctx in TEACH_ME_CONTEXT):
        return False
    return any(kw in lower for kw in EDUCATION_KEYWORDS)

KNOWLEDGE_PATTERNS = [
    r"\b(?:places?|things?|spots?|attractions?|sites?)\s+to\s+(?:visit|see|go|do|explore|check out)\b",
    r"\b(?:best|top|popular|famous|must.?see|must.?visit|recommended)\s+(?:places?|things?|spots?|restaurants?|hotels?|beaches?)\b",
    r"\b(?:where|how)\s+(?:to|can|should|do)\s+(?:i|we|you)\s+(?:go|visit|eat|stay|travel|get|find)\b",
    r"\b(?:travel|trip|visit|vacation|holiday|tour)\s+(?:to|in|tips?|guide|plan|itinerary)\b",
    r"\b(?:history|capital|population|currency|language|economy)\s+of\b",
    r"\b(?:who is|who was|when did|when was|how many|how much|how old)\b",
    r"\b(?:recipe|ingredients|how to (?:make|cook|prepare|bake))\b",
    r"\b(?:weather|temperature|climate)\s+(?:in|at|for)\b",
    r"\b(?:cost|price|cheap|expensive|afford|budget)\s+(?:of|in|to|for)\b",
    r"\b(?:tell\s+me\s+about|talk\s+(?:to\s+me\s+)?about|what\s+(?:is|are)\s+(?:the|a|an)?\s*\w+|explain\s+(?:the|what|how)?\s*\w+)\b",
    r"\bdefine\s+\w+",
    r"\b(?:meaning|definition)\s+of\b",
    r"\b(?:latest|newest|new|recent|upcoming)\s+(?:\w+\s+)?(?:tech|technology|product|gadget|device|feature|release|update|announcement)s?\b",
]

CREATOR_INFO = """Angelo Asante (also known as Travis Moore) is a software engineer and AI developer from Ghana.
He is the creator of Ama (Twi AI). His website is www.angeloasante.com.
Angelo Asante is NOT a musician, NOT a footballer, NOT an athlete. He is a tech professional who builds AI tools for African languages.
He built Ama to help people learn Twi and explore Akan culture."""

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
        ("Medaase paa", "Thank you very much", "Extra gratitude"),
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
        ("Mo maakye", "Good morning (to a group/elder)", "Respectful group greeting"),
    ],
    "food": [
        ("Aduane no yɛ dɛ", "The food is delicious", "CRITICAL phrase — always compliment the cooking"),
        ("Mepɛ aduane", "I want food / I'm hungry", "Asking for food"),
        ("Me kɔn de me", "I am hungry", "Direct way to say you're hungry"),
        ("Nsuo", "Water", "Asking for water"),
        ("Mama, aduane no yɛ dɛ paa", "Mama, the food is really delicious", "Say this to her mother — instant approval"),
    ],
}

TIMEZONE_ALIASES = {
    "ghana": "Africa/Accra", "accra": "Africa/Accra", "nigeria": "Africa/Lagos",
    "lagos": "Africa/Lagos", "london": "Europe/London", "uk": "Europe/London",
    "new york": "America/New_York", "nyc": "America/New_York", "est": "America/New_York",
    "los angeles": "America/Los_Angeles", "la": "America/Los_Angeles", "pst": "America/Los_Angeles",
    "tokyo": "Asia/Tokyo", "japan": "Asia/Tokyo", "paris": "Europe/Paris", "france": "Europe/Paris",
    "dubai": "Asia/Dubai", "india": "Asia/Kolkata", "singapore": "Asia/Singapore",
    "sydney": "Australia/Sydney", "china": "Asia/Shanghai", "hong kong": "Asia/Hong_Kong",
    "south africa": "Africa/Johannesburg", "kenya": "Africa/Nairobi",
}

AKAN_DAYS = ["Ɛdwoada (Monday)", "Ɛbenada (Tuesday)", "Wukuada (Wednesday)", "Yawoada (Thursday)", "Efiada (Friday)", "Memeneda (Saturday)", "Kwasiada (Sunday)"]


# ─── Helper Functions ────────────────────────────────────────────────────────

def resolve_timezone(tz: str) -> str:
    if not tz:
        return "UTC"
    lower = tz.lower().strip()
    return TIMEZONE_ALIASES.get(lower, tz if "/" in tz else "UTC")


def get_current_time(timezone: str) -> str:
    from zoneinfo import ZoneInfo
    resolved = resolve_timezone(timezone)
    try:
        now = datetime.now(ZoneInfo(resolved))
        formatted = now.strftime("%A, %B %d, %Y %I:%M %p")
        day_index = now.weekday()  # 0=Monday
        akan_day = AKAN_DAYS[day_index]
        return f"**Current Date & Time ({resolved}):**\n- {formatted}\n- Twi Day: {akan_day}"
    except Exception:
        return f"**Current Time (UTC):** {datetime.utcnow().isoformat()}"


def detect_intent(message: str) -> dict:
    lower = message.lower()
    intent = {
        "needs_web_search": False,
        "needs_image_search": False,
        "needs_time": False,
        "needs_file_create": False,
        "needs_creator_info": False,
        "needs_teaching": False,
        "teach_category": "essentials",
        "search_query": "",
        "image_query": "",
    }

    if any(kw in lower for kw in NEWS_KEYWORDS) or any(kw in lower for kw in POLITICAL_KEYWORDS):
        intent["needs_web_search"] = True
        intent["search_query"] = message

    if any(kw in lower for kw in SEARCH_KEYWORDS):
        intent["needs_web_search"] = True
        if not intent["search_query"]:
            intent["search_query"] = message

    if any(kw in lower for kw in TIME_KEYWORDS):
        intent["needs_time"] = True

    for kw in IMAGE_KEYWORDS:
        if kw in lower:
            intent["needs_image_search"] = True
            parts = lower.split(kw)
            intent["image_query"] = parts[-1].strip() if parts[-1].strip() else message
            break

    file_match = any(kw in lower for kw in FILE_CREATE_KEYWORDS) or any(re.search(p, lower) for p in FILE_CREATE_PATTERNS)
    if file_match:
        intent["needs_file_create"] = True
        topic = lower
        for kw in sorted(FILE_CREATE_KEYWORDS, key=len, reverse=True):
            topic = topic.replace(kw, "")
        # Also strip regex-matched parts
        for p in FILE_CREATE_PATTERNS:
            topic = re.sub(p, "", topic)
        topic = topic.strip().strip("\"'")
        for prep in ["about ", "on ", "for ", "regarding ", "of ", "bout "]:
            if topic.startswith(prep):
                topic = topic[len(prep):]
        if len(topic) > 2:
            intent["needs_web_search"] = True
            intent["search_query"] = topic.strip()

    is_teach = any(kw in lower for kw in TEACH_KEYWORDS_EXACT)
    if not is_teach and "teach me" in lower:
        # Only trigger if "teach me" is paired with Twi/language context
        is_teach = any(ctx in lower for ctx in TEACH_ME_CONTEXT)
    if is_teach:
        intent["needs_teaching"] = True
        if any(w in lower for w in ["love", "romantic", "girlfriend", "boyfriend", "wife", "husband", "flirt", "marry"]):
            intent["teach_category"] = "romantic"
        elif any(w in lower for w in ["family", "parents", "mother", "father", "elder", "respect"]):
            intent["teach_category"] = "impress_family"
        elif any(w in lower for w in ["food", "eat", "cook", "hungry", "delicious"]):
            intent["teach_category"] = "food"
        elif any(w in lower for w in ["hello", "hi ", "greet", "morning", "evening", "goodbye", "bye"]):
            intent["teach_category"] = "greetings"

    if any(kw in lower for kw in CREATOR_KEYWORDS):
        intent["needs_creator_info"] = True

    if not intent["needs_web_search"]:
        if any(re.search(p, lower, re.IGNORECASE) for p in KNOWLEDGE_PATTERNS):
            intent["needs_web_search"] = True
            intent["search_query"] = message

    if any(p in lower for p in FOLLOWUP_PHRASES):
        intent["needs_web_search"] = True
        if not intent["search_query"]:
            intent["search_query"] = message

    return intent


def build_teaching_response(category: str) -> str:
    phrases = TWI_PHRASES.get(category, TWI_PHRASES["essentials"])
    offset = random.randint(0, max(0, len(phrases) - 4))
    selected = phrases[offset:offset + 4]
    if len(selected) < 4:
        selected = phrases[:4]

    intros = {
        "romantic": "Here are some sweet Twi phrases to impress her:",
        "greetings": "Let's start with some essential Twi greetings:",
        "essentials": "Here are some must-know Twi phrases:",
        "impress_family": "Meeting the family? These phrases will earn you major points:",
        "food": "Food is a big deal in Ghanaian culture! Here are some useful phrases:",
    }
    outros = {
        "romantic": "Try these out! Want me to teach you how to greet her family in Twi?",
        "greetings": "Practice these and you'll sound natural! Want to learn some romantic phrases next?",
        "essentials": "These will get you far! Want to learn greetings or romantic phrases?",
        "impress_family": "Her family will be impressed! Want to learn some food-related phrases too?",
        "food": "Complimenting the cooking is a shortcut to their hearts! Want to learn some essential phrases?",
    }

    lines = [intros.get(category, "Here are some Twi phrases for you:"), ""]
    for twi, eng, note in selected:
        lines.append(f'**{twi}** = "{eng}"')
        lines.append(f"  {note}")
        lines.append("")
    lines.append(outros.get(category, "Want me to teach you more?"))
    return "\n".join(lines)


# ─── Tool Functions (run inside Modal) ───────────────────────────────────────

async def web_search(query: str, max_results: int = 3) -> str:
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    if not tavily_key:
        return "Web search unavailable (no API key)"
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": tavily_key, "query": query, "max_results": max_results, "include_answer": True},
                timeout=15,
            )
        if res.status_code != 200:
            return f"Search failed: {res.status_code}"
        data = res.json()
        results = []
        if data.get("answer"):
            results.append(f"**Summary:** {data['answer']}\n")
        for i, r in enumerate(data.get("results", [])[:max_results]):
            results.append(f"{i+1}. **{r.get('title', 'No title')}**: {r.get('content', '')[:200]}\n")
        return "\n".join(results) if results else "No results found"
    except Exception as e:
        return f"Search error: {e}"


async def image_search(query: str, max_results: int = 5) -> str:
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    if not tavily_key:
        return "Image search unavailable"
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": tavily_key, "query": f"{query} images", "max_results": max_results, "include_images": True},
                timeout=15,
            )
        if res.status_code != 200:
            return "Image search failed"
        data = res.json()
        images = data.get("images", [])
        if not images:
            return f"No images found for '{query}'"
        lines = [f"**Image results for '{query}':**\n"]
        for i, url in enumerate(images[:max_results]):
            lines.append(f"{i+1}. {url}")
        return "\n".join(lines)
    except Exception as e:
        return f"Image search error: {e}"


async def claude_answer(question: str, search_context: str) -> str | None:
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        return None
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 200,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": f"Here is information from a web search:\n\n{search_context}\n\nUsing ONLY the information above, answer this question concisely: {question}\n\nRules:\n- Answer in 2-5 sentences\n- Only state facts from the search results\n- Stay warm and conversational (you're Ama)\n- Do NOT make up facts\n- Do NOT ask questions back"}],
                },
                timeout=20,
            )
        if res.status_code != 200:
            return None
        data = res.json()
        text = data.get("content", [{}])[0].get("text", "").strip()
        return text if text and len(text) > 10 else None
    except Exception:
        return None


# ─── Model Class ─────────────────────────────────────────────────────────────

@app.cls(
    gpu="L4",
    scaledown_window=300,
    secrets=[
        modal.Secret.from_name("huggingface"),
        modal.Secret.from_name("tavily"),
        modal.Secret.from_name("anthropic"),
        modal.Secret.from_dict({"AMA_API_KEY": "ama-twi-sk-7f3a9b2c1d4e5f6a8b9c0d1e2f3a4b5c"}),
    ],
)
class Model:
    model_id = MODEL_ID

    @modal.enter()
    def load_model(self):
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_id, trust_remote_code=True
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        self.model.eval()
        print(f"Model {self.model_id} loaded.")

    def _generate(self, message: str, system_prompt: str, max_new_tokens: int,
                  temperature: float, top_p: float, repetition_penalty: float,
                  history: list = None) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        # Add conversation history for context window
        if history:
            for msg in history[:-1]:  # all prior messages (last one is current user msg)
                role = msg.get("role", "user")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": message})
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False,
        )
        model_inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

        # Build stop token IDs to prevent thinking mode
        stop_ids = []
        for t in ["<think>", "</think>", "<|im_end|>", "<|endoftext|>"]:
            tok_id = self.tokenizer.encode(t, add_special_tokens=False)
            if tok_id:
                stop_ids.append(tok_id[0])

        with torch.no_grad():
            output_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature if temperature > 0 else None,
                top_p=top_p if temperature > 0 else None,
                repetition_penalty=repetition_penalty,
                do_sample=temperature > 0,
                eos_token_id=stop_ids if stop_ids else None,
            )

        new_tokens = output_ids[0][model_inputs["input_ids"].shape[1]:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

        for tok in ["<|im_end|>", "<|endoftext|>", "</s>", "<s>", "<|eot_id|>", "<think>", "</think>"]:
            if tok in response:
                response = response[:response.index(tok)].strip()

        # Strip any residual think blocks (e.g. "<think>\n...\n</think>\nactual response")
        response = re.sub(r"<think>[\s\S]*?</think>\s*", "", response).strip()

        # Remove filler endings only if they appear as standalone trailing lines
        response = re.sub(r"\n\s*(?:Would you like (?:more info|to know more|me to)[^.!?\n]*[.!?]?\s*$)", "", response, flags=re.IGNORECASE)
        response = re.sub(r"\n\s*(?:Feel free to (?:ask|explore)[^.!?\n]*[.!?]?\s*$)", "", response, flags=re.IGNORECASE)
        response = re.sub(r"\n\s*(?:Let me know[^.!?\n]*[.!?]?\s*$)", "", response, flags=re.IGNORECASE)

        # Strip trailing emoji/flag spam (3+ consecutive emojis at end)
        response = re.sub(r'([\U0001F1E0-\U0001F1FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U00002702-\U000027B0\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U0000FE00-\U0000FE0F\U0000200D]{2,}\s*){3,}$', '', response).strip()

        # Remove any line that is ONLY emojis/flags (no real text)
        lines = response.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = re.sub(r'[\U0001F1E0-\U0001F1FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U00002702-\U000027B0\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U0000FE00-\U0000FE0F\U0000200D\s]', '', line)
            if stripped or not line.strip():  # keep line if it has real text or is blank
                cleaned_lines.append(line)
        response = '\n'.join(cleaned_lines).strip()

        # Cap emojis: max 3 per response
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U00002702-\U000027B0\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF]')
        emoji_count = 0
        result_chars = []
        for ch in response:
            if emoji_pattern.match(ch):
                emoji_count += 1
                if emoji_count <= 3:
                    result_chars.append(ch)
            else:
                result_chars.append(ch)
        response = ''.join(result_chars).strip()

        # Strip all flag emojis entirely
        response = re.sub(r'[\U0001F1E0-\U0001F1FF]{2}', '', response).strip()

        return response

    @modal.fastapi_endpoint(method="POST")
    async def generate(self, data: dict):
        """Pure generation endpoint (backward compatible)."""
        inputs = data.get("inputs", "")
        params = data.get("parameters", {})
        system_prompt = params.get("system_prompt", SYSTEM_PROMPT)
        max_new_tokens = min(params.get("max_new_tokens", 1200), 4096)
        temperature = params.get("temperature", 0.7)
        top_p = params.get("top_p", 0.9)
        repetition_penalty = params.get("repetition_penalty", 1.2)

        response = self._generate(inputs, system_prompt, max_new_tokens, temperature, top_p, repetition_penalty)
        return {"generated_text": response}

    @modal.fastapi_endpoint(method="POST")
    async def chat(self, data: dict):
        """Full agentic chat endpoint with tools. Requires API key auth."""
        from fastapi.responses import JSONResponse

        # ── Auth check ──
        api_key = data.get("api_key", "")
        expected_key = os.environ.get("AMA_API_KEY", "")
        if not api_key or api_key != expected_key:
            return JSONResponse(status_code=401, content={"error": "Invalid API key"})

        raw_input = data.get("inputs", "")
        timezone = data.get("timezone", "UTC")
        history = data.get("history", [])  # conversation history

        # Parse memory context
        message = raw_input
        memory_context = ""
        if "Current message:" in raw_input:
            parts = raw_input.split("Current message:")
            memory_context = parts[0].strip()
            message = "Current message:".join(parts[1:]).strip()

        intent = detect_intent(message)

        tools_used = []
        tool_results = {}
        context_parts = []

        # ── Execute tools ──

        if intent["needs_creator_info"]:
            context_parts.append(f"**VERIFIED CREATOR INFORMATION (this overrides any training data):**\n{CREATOR_INFO}")

        if intent["needs_web_search"] and intent["search_query"]:
            skip_search = intent["needs_creator_info"] and not intent["needs_file_create"]
            if not skip_search:
                search_result = await web_search(intent["search_query"])
                tools_used.append("web_search")
                tool_results["web_search"] = {"query": intent["search_query"], "results": search_result}
                context_parts.append(f"**Web Search Results:**\n{search_result}")

        if intent["needs_time"]:
            time_result = get_current_time(timezone)
            context_parts.append(f"**Current Time Information:**\n{time_result}")
            tools_used.append("time")
            tool_results["time"] = time_result

        if intent["needs_image_search"] and intent["image_query"]:
            image_result = await image_search(intent["image_query"])
            context_parts.append(f"**Image Search Results:**\n{image_result}")
            tools_used.append("image_search")
            tool_results["image_search"] = {"query": intent["image_query"], "results": image_result}

        # ── Generate response ──

        if intent["needs_teaching"]:
            response = build_teaching_response(intent["teach_category"])
            tools_used.append("twi_phrases")
            tool_results["twi_phrases"] = {"category": intent["teach_category"]}
        else:
            all_context = []
            if memory_context:
                all_context.append(f"The following is background context about this user. Use it naturally:\n\n{memory_context}")
            all_context.extend(context_parts)
            context = "\n\n".join(all_context)

            has_search = "web_search" in tools_used
            is_document = intent["needs_file_create"]
            is_teaching = is_educational_query(message)

            # For teaching queries, use multi-pass generation for depth
            if is_teaching:
                system_content = SYSTEM_PROMPT
                if context:
                    system_content += f"\n\n---\n\n{context}"
                # First pass: get initial response
                first_response = self._generate(message, system_content, 1024, 0.7, 0.9, 1.1, history)

                # Second pass: ask model to expand with detail
                expand_msg = f"""The user asked: "{message}"

You gave this initial answer:
{first_response}

Now EXPAND this into a full tutorial. Add:
- Code examples in ```language blocks with comments
- Step-by-step explanations with numbered lists
- ## section headers
- Real working examples the user can copy and run
- At least 3 sections of content

Write the full expanded tutorial now:"""
                expanded = self._generate(expand_msg, system_content, 2048, 0.8, 0.9, 1.05)

                # Use the expanded version if it's actually longer
                response = expanded if len(expanded) > len(first_response) + 100 else first_response
                # Skip the rest of the generation logic
                tools_used.append("teaching_mode")
                max_tokens = 0  # signal to skip generation below
            else:
                system_content = f"{SYSTEM_PROMPT}\n\n---\n\n{context}" if context else SYSTEM_PROMPT
                max_tokens = 2048 if is_document else (1024 if has_search else 1500)
                temperature = 0.4 if has_search else (0.5 if is_document else 0.7)
                rep_penalty = 1.4 if has_search else 1.15

            if not is_teaching:
                # For factual queries with search results, try Claude for concise answers
                if has_search and not is_document:
                    search_context = "\n\n".join(context_parts)
                    claude_resp = await claude_answer(message, search_context)
                    if claude_resp:
                        response = claude_resp
                    else:
                        response = self._generate(message, system_content, max_tokens, temperature, 0.9, rep_penalty, history)
                else:
                    response = self._generate(message, system_content, max_tokens, temperature, 0.9, rep_penalty, history)

        # File creation
        if intent["needs_file_create"] and response:
            safe_name = message.lower()
            for kw in sorted(FILE_CREATE_KEYWORDS, key=len, reverse=True):
                safe_name = safe_name.replace(kw, "")
            safe_name = re.sub(r"[^a-zA-Z0-9\s]", "", safe_name).strip().replace(" ", "_")[:50] or "document"
            tools_used.append("create_file")
            tool_results["create_file"] = {
                "file_id": os.urandom(4).hex(),
                "filename": f"{safe_name}.md",
                "content": response,
                "size": len(response),
            }

        # Fallback if empty
        if not response or len(response.strip()) < 5:
            if "web_search" not in tools_used:
                search_result = await web_search(message)
                claude_resp = await claude_answer(message, search_result)
                if claude_resp:
                    response = claude_resp
                    tools_used.append("web_search")
                    tool_results["web_search"] = {"query": message, "results": search_result}
            if not response or len(response.strip()) < 5:
                response = "I'm having a bit of trouble with that one right now. Could you try rephrasing? I want to make sure I give you a good answer."

        return {
            "success": True,
            "response": response,
            "tools_used": tools_used,
            "tool_results": tool_results,
            "timezone": resolve_timezone(timezone),
        }

    @modal.fastapi_endpoint(method="GET")
    async def health(self):
        """Health check / keep-warm endpoint."""
        return {"status": "ok", "model": self.model_id}


# ─── Keep-warm: ping the model every 4 minutes to prevent cold starts ────────

@app.function(schedule=modal.Cron("*/4 * * * *"), image=image)
async def keep_warm():
    """Pings the health endpoint every 4 min to keep the GPU container alive."""
    import httpx as hx
    try:
        async with hx.AsyncClient() as client:
            res = await client.get(
                "https://angeloasante--twi-qwen-model-health.modal.run",
                timeout=120,
            )
            print(f"Keep-warm ping: {res.status_code}")
    except Exception as e:
        print(f"Keep-warm error: {e}")
