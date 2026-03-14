"""Upload handler_agent.py as handler.py to HF and restart endpoint."""
import time
from huggingface_hub import HfApi

import os
TOKEN = os.environ.get("HF_TOKEN", "")
api = HfApi(token=TOKEN)
repo_id = "travis-moore/twi-llama-v5"

print("Uploading hf/handler_agent.py -> handler.py ...")
api.upload_file(
    path_or_fileobj="hf/handler_agent.py",
    path_in_repo="handler.py",
    repo_id=repo_id,
    repo_type="model",
    commit_message="Update handler",
)
print("Done!")

print("Restarting endpoint...")
for attempt in range(5):
    try:
        api.pause_inference_endpoint("twi-llama-v5", namespace="travis-moore")
        time.sleep(5)
        api.resume_inference_endpoint("twi-llama-v5", namespace="travis-moore")
        print("Endpoint restarting.")
        break
    except Exception as e:
        print(f"  Attempt {attempt+1} failed: {e}")
        time.sleep(10)
