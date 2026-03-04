from huggingface_hub import hf_hub_download, HfApi
import json
import os

# Get token from environment
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("Set HF_TOKEN environment variable")

# Download tokenizer_config.json
config_path = hf_hub_download(
    repo_id="travis-moore/twi-llama-v5",
    filename="tokenizer_config.json",
    token=HF_TOKEN
)

# Read and fix it
with open(config_path, 'r') as f:
    config = json.load(f)

print("Current tokenizer_class:", config.get("tokenizer_class"))

# Remove the problematic tokenizer_class field
if "tokenizer_class" in config:
    del config["tokenizer_class"]
    print("Removed tokenizer_class field")

# Save locally
with open("tokenizer_config_fixed.json", 'w') as f:
    json.dump(config, f, indent=2)

# Upload fixed version
api = HfApi()
api.upload_file(
    path_or_fileobj="tokenizer_config_fixed.json",
    path_in_repo="tokenizer_config.json",
    repo_id="travis-moore/twi-llama-v5",
    token=HF_TOKEN
)
print("✅ Fixed tokenizer_config.json uploaded!")
