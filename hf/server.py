"""
Minimal FastAPI server for HuggingFace Inference Endpoint (custom container).
Loads the model from /repository (HF-mounted model files) and delegates to handler.py.
"""

import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# Model path — HF mounts model files here
MODEL_DIR = os.environ.get("HF_MODEL_DIR", "/repository")

handler = None


@app.on_event("startup")
async def load_model():
    global handler
    from handler import EndpointHandler
    print(f"Loading model from {MODEL_DIR}...")
    handler = EndpointHandler(path=MODEL_DIR)
    print("Model loaded, ready to serve.")


@app.get("/health")
async def health():
    if handler is None:
        return JSONResponse(status_code=503, content={"status": "loading"})
    return {"status": "ok"}


@app.post("/")
async def predict(request: Request):
    body = await request.json()
    result = handler(body)
    return result


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    uvicorn.run(app, host="0.0.0.0", port=port)
