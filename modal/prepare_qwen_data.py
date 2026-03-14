"""
Prepare training data for Qwen3.5-9B fine-tuning
=================================================
Merges v2 + v3 + v4 + targeted + seed datasets.
Unifies system prompt. Outputs a single clean JSONL file.

Usage:
    python modal/prepare_qwen_data.py
"""

import json
import random
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(BASE_DIR, "twi-dataset")
OUTPUT_TRAIN = os.path.join(DATASET_DIR, "qwen_train.jsonl")
OUTPUT_VAL = os.path.join(DATASET_DIR, "qwen_val.jsonl")

VAL_RATIO = 0.05  # 5% validation split
SEED = 42

# Production system prompt — matches handler_agent.py personality
SYSTEM_PROMPT = """You are Ama (Twi AI), a bilingual AI assistant fluent in both Twi and English.
Your name is Ama. You were created by Angelo Asante (also known as Travis Moore), a software engineer and AI developer.

YOUR PERSONALITY:
- You are warm, witty, patient, and encouraging — like a cool Ghanaian auntie or older sister.
- You have a playful sense of humor but you're genuinely helpful.
- You care about getting things RIGHT. If you're not sure about a Twi phrase, say so honestly rather than making something up.
- You're proud of Akan/Ghanaian culture and love sharing it authentically.
- You speak naturally — not like a textbook, not like a robot.

RESPONSE STYLE:
- Match the user's energy. Short question = short answer. Detailed question = detailed answer.
- If someone says "hello" or "hi", reply with a warm 1-2 sentence greeting. Do NOT ramble.
- NEVER pad responses with filler like "What would you like to talk about?", "Feel free to ask!", "Let me know!"
- NEVER use hashtags. This is not social media.
- Use emojis sparingly — at most 1-2 per response, and only when natural.
- Do NOT repeat yourself. Say it once, clearly.

TWI LANGUAGE RULES:
- When teaching Twi, ALWAYS use this format: Twi phrase first, then "=" or "means", then English meaning.
- ONLY teach Twi phrases you are CONFIDENT are correct. If unsure, say "I'm not 100% sure of this one".
- NEVER string random Twi words together and pretend they form a sentence.
- If the user writes in Twi, respond primarily in Twi with English translations in parentheses.
- If the user writes in English, respond in English but include relevant Twi phrases naturally.

AKAN DAY NAMES:
- Sunday = Kwasiada, Monday = Ɛdwoada, Tuesday = Ɛbenada, Wednesday = Wukuada
- Thursday = Yawoada, Friday = Efiada, Saturday = Memeneda

You are Ama. Be warm, knowledgeable, and genuine."""


def load_jsonl(filepath):
    """Load a JSONL file and return list of parsed objects."""
    data = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return data


def clean_example(example):
    """
    Validate and clean a single training example.
    Returns None if the example should be skipped.
    """
    msgs = example.get("messages", [])

    # Find user and assistant messages
    user_msgs = [m for m in msgs if m.get("role") == "user"]
    asst_msgs = [m for m in msgs if m.get("role") == "assistant"]

    if not user_msgs or not asst_msgs:
        return None

    user_content = user_msgs[0]["content"].strip()
    asst_content = asst_msgs[0]["content"].strip()

    # Skip empty messages
    if not user_content or not asst_content:
        return None

    # Skip template placeholder translations (<1>, <2>, etc.)
    if "<1>" in user_content or "<2>" in user_content:
        return None

    # Skip very short responses (likely garbage)
    if len(asst_content) < 5:
        return None

    # Skip very long responses (likely garbled)
    if len(asst_content) > 2000:
        return None

    # Skip if assistant response is just a Bible reference
    if asst_content.startswith("—") or asst_content.startswith("- "):
        if len(asst_content) < 50:
            return None

    # Build clean example with unified system prompt
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": asst_content},
        ]
    }


def main():
    # Files to include (good quality only)
    files = [
        ("conversations_v4.jsonl", "v4 — concise bilingual"),
        ("conversations_v2.jsonl", "v2 — educational Twi Q&A"),
        ("conversations_v3.jsonl", "v3 — bilingual conversational"),
        ("conversations_targeted.jsonl", "targeted — identity/creator"),
        ("conversations_seed.jsonl", "seed — hand-crafted examples"),
    ]

    all_examples = []
    stats = {}

    for filename, description in files:
        filepath = os.path.join(DATASET_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP {filename} — file not found")
            continue

        raw = load_jsonl(filepath)
        cleaned = []
        for ex in raw:
            result = clean_example(ex)
            if result is not None:
                cleaned.append(result)

        stats[filename] = {"raw": len(raw), "cleaned": len(cleaned)}
        all_examples.extend(cleaned)
        print(f"  {filename}: {len(raw)} raw → {len(cleaned)} clean ({description})")

    # Deduplicate by user message content
    seen = set()
    unique = []
    for ex in all_examples:
        user_msg = ex["messages"][1]["content"]
        key = user_msg.strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(ex)

    dupes_removed = len(all_examples) - len(unique)
    print(f"\n  Duplicates removed: {dupes_removed}")
    print(f"  Total unique examples: {len(unique)}")

    # Shuffle and split
    random.seed(SEED)
    random.shuffle(unique)

    val_size = int(len(unique) * VAL_RATIO)
    val_data = unique[:val_size]
    train_data = unique[val_size:]

    print(f"  Train: {len(train_data)}")
    print(f"  Val:   {len(val_data)}")

    # Write output files
    with open(OUTPUT_TRAIN, "w", encoding="utf-8") as f:
        for ex in train_data:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    with open(OUTPUT_VAL, "w", encoding="utf-8") as f:
        for ex in val_data:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\n  Wrote {OUTPUT_TRAIN}")
    print(f"  Wrote {OUTPUT_VAL}")

    # Show a few examples
    print("\n--- Sample training examples ---")
    for i, ex in enumerate(train_data[:3]):
        print(f"\nExample {i+1}:")
        print(f"  User: {ex['messages'][1]['content'][:100]}")
        print(f"  Ama:  {ex['messages'][2]['content'][:100]}")


if __name__ == "__main__":
    print("Preparing Qwen3.5-9B training data...\n")
    main()
    print("\nDone!")
