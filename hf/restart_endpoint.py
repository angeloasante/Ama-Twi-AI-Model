"""Restart the HF Inference Endpoint to reload updated handler."""
from huggingface_hub import HfApi

api = HfApi()
NAMESPACE = "travis-moore"
NAME = "twi-llama-v5"

print("Pausing endpoint...")
ep = api.pause_inference_endpoint(NAME, namespace=NAMESPACE)
print(f"  State: {ep.status}")

print("Resuming endpoint...")
ep = api.resume_inference_endpoint(NAME, namespace=NAMESPACE)
print(f"  State: {ep.status}")

print("\nEndpoint is restarting. It will take a few minutes to initialize.")
print("The updated handler_agent.py will be loaded on startup.")
