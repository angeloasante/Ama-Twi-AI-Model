"""
Twi AI Agent - Ama with Tools
Features: Web Search, Knowledge Base (RAG), Tool Calling

Deploy:
    modal deploy modal_agent_deploy.py

Test:
    curl -X POST https://YOUR_USERNAME--twi-ai-agent-twiagent-chat.modal.run \
      -H "Content-Type: application/json" \
      -d '{"prompt": "What is the latest news about Ghana?"}'
"""

import modal
import os
import json
import re
from typing import Optional

MODEL_ID = "travis-moore/twi-llama-v5"
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
MODEL_DIR = "/model"

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

    "ghana_presidents": """
⚠️ NOTE: This information may be OUTDATED. Always verify with web search for current president.

GHANA PRESIDENTS (Historical):
- Kwame Nkrumah (1960-1966): First President, led independence
- John Agyekum Kufuor (2001-2009): NPP
- John Atta Mills (2009-2012): NDC, passed away in office
- John Dramani Mahama (2012-2017, 2025-present): NDC
- Nana Akufo-Addo (2017-2025): NPP

⚠️ FOR CURRENT PRESIDENT: Use web search to get accurate, up-to-date information.
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
| Yes | Aane | aa-neh |
| No | Daabi | daa-bee |
| Welcome | Akwaaba | ah-kwaa-bah |
| Goodbye | Nante yie | nan-teh yee-eh |
| I love you | Me dɔ wo | meh dawh woh |
| What is your name? | Wo din de sɛn? | woh din deh sehn |
| My name is... | Me din de... | meh din deh |
""",

    "akan_proverbs": """
POPULAR AKAN PROVERBS (Mmɛ):
1. "Obi nkyerɛ abɔfra Nyame" - No one teaches a child about God (God is innate)
2. "Sɛ wo werɛ fi na wosan hwɛ a, wonhu wo ti akyi" - If you forgot and look again, you won't see your back (learn from past)
3. "Nkrabea mu nni kwatibea" - There's no changing destiny
4. "Aboa a ɔnni dua, Onyame na ɔpra ne ho" - God looks after the tailless animal
5. "Woforo dua pa a, na yepia wo" - When you climb a good tree, you get pushed (support)
6. "Tete ka asom" - Old things remain in the ear (wisdom passes down)
7. "Ananse ntontan nyinaa, ɛhyia ne yam" - All spider webs join at the center
8. "Ɔdɔ yɛ owuo" - Love is death (love conquers all)
""",

    "ghana_facts": """
GHANA FACTS:
- Independence: March 6, 1957 (first sub-Saharan African country)
- Population: ~34 million (2024)
- Capital: Accra
- Currency: Ghana Cedi (GHS)
- Languages: English (official), Akan, Ewe, Ga, Dagbani, Dagaare, Hausa
- Major ethnic groups: Akan (47%), Mole-Dagbon (17%), Ewe (14%), Ga-Dangme (7%)
- Main exports: Gold, cocoa, oil, timber
- Famous people: Kofi Annan (UN), Michael Essien, Asamoah Gyan, Kwame Nkrumah
- National dish: Jollof rice, Fufu with light soup, Banku with tilapia
- National symbol: Black Star (on flag)
""",

    "twi_numbers": """
TWI NUMBERS:
| Number | Twi | Pronunciation |
|--------|-----|---------------|
| 1 | Baako | baa-koh |
| 2 | Mmienu | mmee-eh-noo |
| 3 | Mmiɛnsa | mmee-ehn-sah |
| 4 | Ɛnan | eh-nahn |
| 5 | Enum | eh-noom |
| 6 | Nsia | n-see-ah |
| 7 | Nson | n-sohn |
| 8 | Nwɔtwe | n-waw-tweh |
| 9 | Nkron | n-krohn |
| 10 | Edu | eh-doo |
| 20 | Aduonu | ah-doo-oh-noo |
| 50 | Aduonum | ah-doo-oh-noom |
| 100 | Ɔha | aw-hah |
| 1000 | Apem | ah-pem |
""",
}

# Keywords to match knowledge base topics
KNOWLEDGE_KEYWORDS = {
    "akan_day_names": ["day name", "kradin", "born on", "kwadwo", "kwabena", "kweku", "yaw", "kofi", "kwame", "kwasi", 
                       "adwoa", "abena", "akua", "yaa", "afua", "ama", "akosua", "monday", "tuesday", "wednesday",
                       "thursday", "friday", "saturday", "sunday", "naming", "soul name"],
    "ghana_regions": ["region", "capital", "accra", "kumasi", "tamale", "cape coast", "takoradi", "ho", "bolgatanga"],
    "ghana_presidents": ["president", "mahama", "akufo-addo", "nkrumah", "kufuor", "atta mills", "government", "ndc", "npp"],
    "twi_greetings": ["hello", "greeting", "how are you", "good morning", "goodbye", "thank you", "please", "welcome",
                      "maakye", "akwaaba", "medaase", "wo ho te"],
    "akan_proverbs": ["proverb", "mmɛ", "saying", "wisdom", "ananse"],
    "ghana_facts": ["ghana", "independence", "population", "currency", "cedi", "flag", "black star", "jollof", "fufu"],
    "twi_numbers": ["number", "count", "baako", "mmienu", "edu", "how many", "numer"],
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


app = modal.App("twi-ai-agent")

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
        "tavily-python",  # Web search
        "httpx",          # HTTP client
    )
    .run_function(
        download_model,
        secrets=[modal.Secret.from_name("huggingface")],
    )
)

# ============================================================================
# TOOLS
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
        return "Web search unavailable (no API key)"
    
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
        
        # Search with context about Ghana/Twi
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=3,
        )
        
        results = []
        for r in response.get("results", []):
            results.append(f"**{r.get('title', 'No title')}**\n{r.get('content', '')[:500]}")
        
        if results:
            return "\n\n".join(results)
        return "No results found"
        
    except Exception as e:
        return f"Web search error: {str(e)}"


AGENT_SYSTEM_PROMPT = """You are Ama, a bilingual Twi-English AI assistant with access to tools.

TOOLS AVAILABLE:
1. KNOWLEDGE_BASE - Contains verified facts about Ghana, Twi language, Akan culture
2. WEB_SEARCH - Search the internet for current information

WHEN TO USE TOOLS:
- Use KNOWLEDGE_BASE for: Akan day names, Twi translations, Ghana regions, proverbs, cultural facts
- Use WEB_SEARCH for: Current news, recent events, things after 2024, real-time information

IMPORTANT - OUTDATED KNOWLEDGE WARNING:
- Your training data is from 2024, so political info may be WRONG
- ALWAYS use web search for: presidents, ministers, government officials, elections, political parties
- If you're not 100% sure about something, search the web first
- Never guess about current political leaders - ALWAYS search

HOW TO USE TOOLS:
When you need to use a tool, respond with:
[TOOL: tool_name]
[QUERY: your search query]

I will execute the tool and provide results. Then answer based on what you learn.

IMPORTANT - Akan Day Names (ALWAYS USE THIS):
| Day       | Male    | Female  |
|-----------|---------|---------|
| Monday    | Kwadwo  | Adwoa   |
| Tuesday   | Kwabena | Abena   |
| Wednesday | Kweku   | Akua    |
| Thursday  | Yaw     | Yaa     |
| Friday    | Kofi    | Afua    |
| Saturday  | Kwame   | Ama     |
| Sunday    | Kwasi   | Akosua  |

Your traits:
- Created by Angelo Asante
- Expert in Twi language and Ghanaian culture
- Warm, helpful, knowledgeable
- Match the user's language (Twi or English)"""


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
        print(f"Model loaded! Tavily available: {bool(self.tavily_key)}")

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

    def execute_tool(self, tool_name: str, query: str) -> str:
        """Execute a tool and return results"""
        tool_name = tool_name.lower().strip()
        
        if "knowledge" in tool_name or "kb" in tool_name:
            result = search_knowledge_base(query)
            if result:
                return f"[KNOWLEDGE BASE RESULTS]\n{result}"
            return "[KNOWLEDGE BASE] No relevant information found."
            
        elif "web" in tool_name or "search" in tool_name:
            result = web_search(query, self.tavily_key)
            return f"[WEB SEARCH RESULTS]\n{result}"
            
        return f"[ERROR] Unknown tool: {tool_name}"

    def parse_tool_call(self, response: str) -> tuple:
        """Parse tool call from model response"""
        tool_match = re.search(r'\[TOOL:\s*([^\]]+)\]', response, re.IGNORECASE)
        query_match = re.search(r'\[QUERY:\s*([^\]]+)\]', response, re.IGNORECASE)
        
        if tool_match and query_match:
            return tool_match.group(1).strip(), query_match.group(1).strip()
        return None, None

    @modal.fastapi_endpoint(method="POST")
    def chat(self, data: dict) -> dict:
        """HTTP endpoint for agent chat"""
        try:
            prompt = data.get("prompt", "")
            system_prompt = data.get("system_prompt", AGENT_SYSTEM_PROMPT)
            max_tokens = data.get("max_tokens", 512)
            temperature = data.get("temperature", 0.7)
            use_tools = data.get("use_tools", True)  # Enable/disable tools
            
            if not prompt:
                return {"error": "No prompt provided"}
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            # Keywords that trigger automatic web search
            NEWS_KEYWORDS = ["news", "latest", "today", "recent", "current", "happening", 
                           "2025", "2026", "update", "breaking", "now"]
            
            # ALWAYS search for these topics - model knowledge is outdated
            ALWAYS_SEARCH_KEYWORDS = ["president", "vice president", "government", "minister",
                                      "election", "parliament", "ndc", "npp", "political",
                                      "who is the", "who won", "current leader"]
            
            prompt_lower = prompt.lower()
            needs_web_search = any(kw in prompt_lower for kw in NEWS_KEYWORDS)
            needs_president_search = any(kw in prompt_lower for kw in ALWAYS_SEARCH_KEYWORDS)
            
            # First check knowledge base automatically for relevant queries
            kb_context = ""
            web_context = ""
            tools_used = []
            
            if use_tools:
                kb_context = search_knowledge_base(prompt)
                
                # Auto web search for news/current events OR political topics (outdated knowledge)
                if (needs_web_search or needs_president_search) and self.tavily_key:
                    search_query = prompt
                    # Add Ghana context for political queries
                    if needs_president_search and "ghana" not in prompt_lower:
                        search_query = f"Ghana {prompt}"
                    web_context = web_search(search_query, self.tavily_key)
                    tools_used.append({"tool": "web_search", "query": search_query, "reason": "president/political queries always use live data"})
            
            # Build context
            context_parts = []
            if kb_context and not needs_president_search:
                # Don't include KB for political queries (it might be outdated)
                context_parts.append(f"[KNOWLEDGE BASE]\n{kb_context}")
            if web_context and "error" not in web_context.lower():
                context_parts.append(f"[LIVE WEB SEARCH - CURRENT DATA FROM TODAY]\n{web_context}")
            
            if context_parts:
                if needs_president_search or needs_web_search:
                    # Be very explicit that web results are authoritative
                    messages.append({
                        "role": "assistant", 
                        "content": f"I searched the web for current information:\n\n" + "\n\n---\n\n".join(context_parts)
                    })
                    messages.append({
                        "role": "user",
                        "content": f"IMPORTANT: Use ONLY the web search results above to answer. Your training data is outdated. The web results are from TODAY and are accurate. Question: {prompt}"
                    })
                else:
                    messages.append({
                        "role": "assistant", 
                        "content": f"Let me check my sources...\n\n" + "\n\n---\n\n".join(context_parts)
                    })
                    messages.append({
                        "role": "user",
                        "content": f"Based on this information, please answer: {prompt}"
                    })
            
            # Generate initial response
            response = self.generate(messages, max_tokens, temperature)
            
            # Check if model wants to use a tool (in addition to auto tools)
            tool_name, tool_query = self.parse_tool_call(response)
            
            if tool_name and tool_query and use_tools:
                # Execute the tool
                tool_result = self.execute_tool(tool_name, tool_query)
                tools_used.append({"tool": tool_name, "query": tool_query})
                
                # Add tool result to conversation and regenerate
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"Tool result:\n{tool_result}\n\nNow provide your final answer."})
                
                response = self.generate(messages, max_tokens, temperature)
            
            return {
                "response": response,
                "model": MODEL_ID,
                "tools_used": tools_used,
                "kb_context_found": bool(kb_context),
                "web_search_used": bool(web_context),
            }
            
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}


# Simple endpoint without agent (backwards compatible)
@app.cls(
    image=image,
    gpu="A100",
    timeout=600,
    scaledown_window=120,
    memory=32768,
    secrets=[modal.Secret.from_name("huggingface")],
)
class TwiAI:
    """Simple chat without agent tools (original functionality)"""
    
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_DIR,
            torch_dtype=torch.float16,
            device_map="auto",
        )

    @modal.fastapi_endpoint(method="POST")
    def chat(self, data: dict) -> dict:
        prompt = data.get("prompt", "")
        system_prompt = data.get("system_prompt", AGENT_SYSTEM_PROMPT)
        max_tokens = data.get("max_tokens", 512)
        temperature = data.get("temperature", 0.7)
        
        if not prompt:
            return {"error": "No prompt provided"}
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
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
        
        response = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True
        )
        
        return {"response": response, "model": MODEL_ID}


@app.local_entrypoint()
def main(prompt: str = "What day name is Kofi?"):
    """Test locally"""
    agent = TwiAgent()
    result = agent.chat.remote({"prompt": prompt, "max_tokens": 512})
    print(f"Response: {result}")
