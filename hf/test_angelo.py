"""Wait for HF endpoint to restart then test Angelo Asante query."""
import time
import requests
import json

ENDPOINT = "https://vs68t0qrfr3hsfp3.us-east-1.aws.endpoints.huggingface.cloud"
import os
TOKEN = os.environ.get("HF_TOKEN", "")
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

print("Waiting for endpoint to come back online...")
for i in range(30):
    try:
        r = requests.post(
            ENDPOINT,
            headers=headers,
            json={"inputs": "ping", "parameters": {"max_new_tokens": 5}},
            timeout=15,
        )
        if r.status_code == 200:
            print(f"  [{i*10}s] Online!")
            break
        else:
            print(f"  [{i*10}s] Status {r.status_code}, waiting...")
    except Exception as e:
        print(f"  [{i*10}s] Not ready ({type(e).__name__})")
    time.sleep(10)
else:
    print("Still starting. Try again in a few minutes.")
    exit()

# Test
tests = [
    "hello",
    "Who is Angelo Asante?",
    "explain what galamsey is in great detail",
    "create a document about galamsey",
]
for q in tests:
    payload = {
        "inputs": q,
        "parameters": {"max_new_tokens": 512, "temperature": 0.7},
    }
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    for attempt in range(3):
        try:
            r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=180)
            print(f"Status: {r.status_code}")
            data = r.json()
            print(f"Tools: {data.get('tools_used', [])}")
            resp = data.get('response', '')
            print(f"Response ({len(resp)} chars): {resp[:500]}")
            print(f"Tool results keys: {list(data.get('tool_results', {}).keys())}")
            if 'create_file' in data.get('tool_results', {}):
                cf = data['tool_results']['create_file']
                print(f"  >> Document: {cf.get('filename')} ({cf.get('size')} bytes)")
            break
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {type(e).__name__}. Retrying...")
            time.sleep(10)
