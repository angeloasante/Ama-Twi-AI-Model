FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3-pip git && \
    rm -rf /var/lib/apt/lists/* && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3

# Install PyTorch (CUDA 12.4) + transformers from source (Qwen3.5 support)
RUN pip install --no-cache-dir \
    torch>=2.3.0 --index-url https://download.pytorch.org/whl/cu124

RUN pip install --no-cache-dir \
    git+https://github.com/huggingface/transformers.git \
    accelerate>=0.34.0 \
    safetensors \
    sentencepiece \
    uvicorn \
    fastapi

COPY handler.py /app/handler.py
COPY server.py /app/server.py

WORKDIR /app
EXPOSE 80

CMD ["python3", "server.py"]
