"""Test detail and document generation quality."""
import time
import requests

ENDPOINT = "https://vs68t0qrfr3hsfp3.us-east-1.aws.endpoints.huggingface.cloud"
import os
TOKEN = os.environ.get("HF_TOKEN", "")
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# Wait for online
print("Waiting for endpoint...")
for i in range(30):
    try:
        r = requests.post(ENDPOINT, headers=headers,
                          json={"inputs": "ping", "parameters": {"max_new_tokens": 5}},
                          timeout=15)
        if r.status_code == 200:
            print(f"  Online after {i*10}s")
            break
    except:
        pass
    time.sleep(10)

tests = [
    "explain what galamsey is in great detail",
    "create a document about galamsey",
]

for q in tests:
    print(f"\n{'='*60}")
    print(f"Q: {q}")
    for attempt in range(3):
        try:
            r = requests.post(ENDPOINT, headers=headers,
                              json={"inputs": q, "parameters": {"max_new_tokens": 2048}},
                              timeout=300)
            data = r.json()
            resp = data.get("response", "")
            print(f"Tools: {data.get('tools_used', [])}")
            print(f"Response ({len(resp)} chars):")
            print(resp[:2000])
            if "create_file" in data.get("tool_results", {}):
                cf = data["tool_results"]["create_file"]
                print(f"\n  >> Doc: {cf['filename']} ({cf['size']} bytes)")
            break
        except Exception as e:
            print(f"  Attempt {attempt+1}: {type(e).__name__}")
            time.sleep(15)
