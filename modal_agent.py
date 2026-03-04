"""
Twi AI Agent with Tools - Web Search + RAG Knowledge Base
Deploy: modal deploy modal_agent.py
Test: curl -X POST https://YOUR_USERNAME--twi-ai-agent-twi-agent-chat.modal.run \
      -H "Content-Type: application/json" \
      -d '{"prompt": "What is the latest news about Ghana?"}'
"""

import modal
import json
import re
from typing import Optional

MODEL_ID = "travis-moore/twi-llama-v5"
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
MODEL_DIR = "/model"
KNOWLEDGE_DIR = "/knowledge"

# ============================================================================
# KNOWLEDGE BASE - Twi Cultural Facts (RAG-lite)
# ============================================================================

TWI_KNOWLEDGE_BASE = {
    "akan_day_names": """
AKAN DAY NAMING SYSTEM (Kradin):
| Day       | Male Name | Female Name | Meaning/Personality |
|-----------|-----------|-------------|---------------------|
| Monday    | Kwadwo    | Adwoa       | Peaceful, calm      |
| Tuesday   | Kwabena   | Abena       | Ocean, sea spirit   |
| Wednesday | Kweku     | Akua        | Spider (Ananse)     |
| Thursday  | Yaw       | Yaa         | Earth, strength     |
| Friday    | Kofi      | Afua        | Fertility, wanderer |
| Saturday  | Kwame     | Ama         | God, Saturday-born  |
| Sunday    | Kwasi     | Akosua      | Universe, cosmos    |

Famous examples:
- Kofi Annan (Friday-born) - Former UN Secretary General
- Kwame Nkrumah (Saturday-born) - First President of Ghana
- Yaa Asantewaa (Thursday-born) - Queen Mother who led Ashanti war
""",

    "ghana_regions": """
GHANA REGIONS AND CAPITALS:
| Region              | Capital         | Notable Info |
|---------------------|-----------------|--------------|
| Greater Accra       | Accra           | National capital |
| Ashanti             | Kumasi          | Largest region, Ashanti Kingdom |
| Western             | Sekondi-Takoradi| Oil production |
| Central             | Cape Coast      | Historic slave castles |
| Eastern             | Koforidua       | Cocoa farming |
| Volta               | Ho              | Ewe people |
| Northern            | Tamale          | Largest northern city |
| Upper East          | Bolgatanga      | Border with Burkina Faso |
| Upper West          | Wa              | Smallest population |
| Brong-Ahafo         | Sunyani         | Agricultural hub |
| Western North       | Sefwi Wiawso    | Created 2018 |
| Ahafo               | Goaso           | Created 2018 |
| Bono East           | Techiman        | Created 2018 |
| Oti                 | Dambai          | Created 2018 |
| North East          | Nalerigu        | Created 2018 |
| Savannah            | Damongo         | Created 2018 |
""",

    "twi_greetings": """
TWI GREETINGS AND RESPONSES:
| Twi               | English              | Response |
|-------------------|----------------------|----------|
| Ɛte sɛn?          | How are things?      | Ɛyɛ (It's good) |
| Wo ho te sɛn?     | How are you?         | Me ho yɛ (I'm fine) |
| Maakye            | Good morning         | Yaa, maakye |
| Maaha             | Good afternoon       | Yaa, maaha |
| Maadwo            | Good evening         | Yaa, maadwo |
| Akwaaba           | Welcome              | Medaase (Thank you) |
| Da yie            | Good night/Sleep well| Da yie |
| Me da wo ase      | Thank you            | Ɛyɛ/You're welcome |
| Nante yie         | Walk well/Goodbye    | Nante yie |
| Yɛbɛhyia bio      | We'll meet again     | Yɛbɛhyia bio |
""",

    "akan_proverbs": """
AKAN PROVERBS (Mmɛ):
1. "Obi nkyerɛ abɔfra Nyame" - No one teaches a child about God (God is innate)
2. "Sɛ wo werɛ fi na wosan hwɛ a, wonhu" - If you forget and look again, you won't see (Pay attention the first time)
3. "Nea onnim no sua a, ohu" - He who does not know can know from learning
4. "Abɔfra bo nnwa na ɔmmo akyekyedeɛ" - A child can kill a snail but not a tortoise (Know your limits)
5. "Tete ka asom" - Ancient things remain in the ears (Respect tradition)
6. "Obra nye mframa, obi nka nkyerɛ obi" - Life is not wind, no one tells another (Life is unpredictable)
7. "Woforo dua pa a, na yepia wo" - If you climb a good tree, you are pushed (Good efforts are supported)
8. "Onipa hia mmoa" - A person needs help (No one succeeds alone)
""",

    "ghana_history": """
GHANA HISTORY KEY DATES:
- 1471: Portuguese arrive at Gold Coast
- 1874: Gold Coast becomes British colony
- 1957: Independence (March 6) - First sub-Saharan African country
- 1960: Republic declared, Kwame Nkrumah first president
- 1966: Nkrumah overthrown by military coup
- 1981: Jerry Rawlings takes power
- 1992: Fourth Republic begins, multi-party democracy
- 2000: John Kufuor elected (first peaceful transfer of power)
- 2009: John Atta Mills becomes president
- 2012: John Mahama becomes president
- 2017: Nana Akufo-Addo becomes president
- 2021: Nana Akufo-Addo re-elected
- 2025: John Dramani Mahama returns as president (current)

National symbols:
- Flag: Red, Gold, Green with Black Star
- Motto: "Freedom and Justice"
- National bird: Eagle
- Currency: Ghanaian Cedi (GH₵)
""",

    "twi_numbers": """
TWI NUMBERS:
| Number | Twi      | Number | Twi          |
|--------|----------|--------|--------------|
| 1      | baako    | 11     | dubaako      |
| 2      | mmienu   | 12     | dummienu     |
| 3      | mmiɛnsa  | 20     | aduonu       |
| 4      | ɛnan     | 30     | aduasa       |
| 5      | enum     | 40     | aduanan      |
| 6      | nsia     | 50     | aduonum      |
| 7      | nson     | 60     | aduosia      |
| 8      | nwɔtwe   | 70     | aduoson      |
| 9      | nkron    | 80     | aduowɔtwe    |
| 10     | du       | 90     | aduokron     |
|        |          | 100    | ɔha          |
|        |          | 1000   | apem         |
""",

    "ghanaian_food": """
GHANAIAN FOOD:
| Food     | Description | Region |
|----------|-------------|--------|
| Fufu     | Pounded cassava/plantain with soup | Akan areas |
| Banku    | Fermented corn/cassava dough | Ga, Ewe |
| Kenkey   | Fermented corn dough wrapped in leaves | Coastal |
| Jollof Rice | Spiced tomato rice | Nationwide |
| Waakye   | Rice and beans with spices | Northern origin |
| Red Red  | Bean stew with fried plantain | Nationwide |
| Kelewele | Spiced fried plantain | Nationwide |
| Groundnut Soup | Peanut-based soup | Nationwide |
| Light Soup | Tomato-based soup | Akan |
| Palm Nut Soup | Palm fruit soup | Akan |
| Omo Tuo  | Rice balls with soup | Northern |
| TZ (Tuo Zaafi) | Corn flour dough | Northern |
"""
}


def search_knowledge_base(query: str) -> str:
    """Search the local knowledge base for relevant information."""
    query_lower = query.lower()
    results = []
    
    # Keywords to topics mapping
    keyword_map = {
        "akan_day_names": ["day name", "kradin", "kwadwo", "kwabena", "kweku", "yaw", "kofi", "kwame", "kwasi", 
                          "adwoa", "abena", "akua", "yaa", "afua", "ama", "akosua", "born on", "saturday", 
                          "monday", "tuesday", "wednesday", "thursday", "friday", "sunday"],
        "ghana_regions": ["region", "capital", "accra", "kumasi", "tamale", "cape coast", "sekondi", "ho", 
                         "bolgatanga", "sunyani", "techiman"],
        "twi_greetings": ["greeting", "hello", "how are you", "wo ho te", "maakye", "maaha", "maadwo", 
                         "akwaaba", "thank you", "goodbye", "welcome"],
        "akan_proverbs": ["proverb", "mmɛ", "saying", "wisdom", "ancient"],
        "ghana_history": ["history", "independence", "nkrumah", "president", "colony", "1957", "republic"],
        "twi_numbers": ["number", "count", "baako", "mmienu", "how many", "du", "ɔha"],
        "ghanaian_food": ["food", "eat", "fufu", "banku", "kenkey", "jollof", "waakye", "kelewele", "soup"]
    }
    
    for topic, keywords in keyword_map.items():
        if any(kw in query_lower for kw in keywords):
            results.append(TWI_KNOWLEDGE_BASE[topic])
    
    if results:
        return "\n\n---\n\n".join(results)
    return ""


# ============================================================================
# WEB SEARCH TOOL (Tavily API)
# ============================================================================

def web_search(query: str, api_key: str) -> str:
    """Search the web using Tavily API."""
    import requests
    
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": 5,
                "include_answer": True
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Format results
            results = []
            if data.get("answer"):
                results.append(f"Summary: {data['answer']}")
            
            for r in data.get("results", [])[:3]:
                results.append(f"- {r.get('title', 'No title')}: {r.get('content', '')[:200]}...")
            
            return "\n".join(results) if results else "No results found."
        else:
            return f"Search failed: {response.status_code}"
    except Exception as e:
        return f"Search error: {str(e)}"


# ============================================================================
# AGENT LOGIC
# ============================================================================

AGENT_SYSTEM_PROMPT = """You are Ama, a bilingual Twi-English AI assistant with access to tools.

AVAILABLE TOOLS:
1. KNOWLEDGE_BASE - Search Twi/Ghana cultural knowledge (day names, regions, greetings, proverbs, history, numbers, food)
2. WEB_SEARCH - Search the internet for current events and information

WHEN TO USE TOOLS:
- Use KNOWLEDGE_BASE for: Akan day names, Ghana regions, Twi greetings, proverbs, history, numbers, food
- Use WEB_SEARCH for: Current news, recent events, things that change over time, facts you're unsure about

HOW TO USE TOOLS:
When you need to use a tool, respond ONLY with this format:
<tool>TOOL_NAME</tool>
<query>your search query</query>

Example:
<tool>KNOWLEDGE_BASE</tool>
<query>akan day names</query>

IMPORTANT:
- If you can answer from your training, answer directly
- If you need current/recent information, use WEB_SEARCH
- If asked about Ghanaian culture/language, check KNOWLEDGE_BASE first
- After receiving tool results, synthesize them into a natural response

AKAN DAY NAMES (always use this):
Monday=Kwadwo/Adwoa, Tuesday=Kwabena/Abena, Wednesday=Kweku/Akua,
Thursday=Yaw/Yaa, Friday=Kofi/Afua, Saturday=Kwame/Ama, Sunday=Kwasi/Akosua"""


def parse_tool_call(response: str) -> tuple[Optional[str], Optional[str]]:
    """Parse tool call from model response."""
    tool_match = re.search(r'<tool>(\w+)</tool>', response, re.IGNORECASE)
    query_match = re.search(r'<query>(.*?)</query>', response, re.IGNORECASE | re.DOTALL)
    
    if tool_match and query_match:
        return tool_match.group(1).upper(), query_match.group(1).strip()
    return None, None


# ============================================================================
# MODAL SETUP
# ============================================================================

def download_model():
    import os
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
        "requests",
    )
    .run_function(
        download_model,
        secrets=[modal.Secret.from_name("huggingface")],
    )
)


@app.cls(
    image=image,
    gpu="A100",
    timeout=600,
    scaledown_window=120,
    memory=32768,
    secrets=[
        modal.Secret.from_name("huggingface"),
    ],
)
class TwiAgent:
    @modal.enter()
    def load_model(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import os
        
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            MODEL_DIR,
            torch_dtype=torch.float16,
            device_map="auto",
        )
        
        self.tavily_key = os.environ.get("TAVILY_API_KEY", "")
        print("Agent loaded with tools: KNOWLEDGE_BASE, WEB_SEARCH")

    def generate(self, messages: list, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate response from messages."""
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

    def run_agent(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> dict:
        """Run the agent with tool-calling capability."""
        messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        # Step 1: Initial response
        response = self.generate(messages, max_tokens=256, temperature=0.3)
        
        # Step 2: Check for tool call
        tool_name, tool_query = parse_tool_call(response)
        
        tool_results = None
        if tool_name:
            if tool_name == "KNOWLEDGE_BASE":
                tool_results = search_knowledge_base(tool_query)
                if not tool_results:
                    tool_results = "No specific knowledge found. Answering from general knowledge."
            elif tool_name == "WEB_SEARCH":
                if self.tavily_key:
                    tool_results = web_search(tool_query, self.tavily_key)
                else:
                    tool_results = "Web search unavailable (no API key). Answering from general knowledge."
            
            # Step 3: Generate final response with tool results
            if tool_results:
                messages.append({"role": "assistant", "content": f"[Used {tool_name}]"})
                messages.append({"role": "user", "content": f"Tool results:\n{tool_results}\n\nNow answer the original question naturally, incorporating this information."})
                response = self.generate(messages, max_tokens=max_tokens, temperature=temperature)
        
        return {
            "response": response,
            "tool_used": tool_name,
            "tool_query": tool_query if tool_name else None,
        }

    @modal.fastapi_endpoint(method="POST")
    def chat(self, data: dict) -> dict:
        """HTTP endpoint for agent chat."""
        try:
            prompt = data.get("prompt", "")
            max_tokens = data.get("max_tokens", 512)
            temperature = data.get("temperature", 0.7)
            use_agent = data.get("use_agent", True)  # Enable agent by default
            
            if not prompt:
                return {"error": "No prompt provided"}
            
            if use_agent:
                result = self.run_agent(prompt, max_tokens, temperature)
                return {
                    "response": result["response"],
                    "tool_used": result["tool_used"],
                    "model": MODEL_ID,
                    "agent": True
                }
            else:
                # Direct mode (no tools)
                messages = [
                    {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
                response = self.generate(messages, max_tokens, temperature)
                return {
                    "response": response,
                    "model": MODEL_ID,
                    "agent": False
                }
                
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}


@app.local_entrypoint()
def main(prompt: str = "What day was Kofi Annan born on?"):
    agent = TwiAgent()
    result = agent.run_agent.remote(prompt=prompt)
    print(f"Response: {result['response']}")
    if result.get('tool_used'):
        print(f"Tool used: {result['tool_used']}")
