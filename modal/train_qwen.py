"""
Qwen3.5-9B Fine-Tuning on Modal (QLoRA)
========================================
Fine-tunes Qwen/Qwen3.5-9B on curated Twi conversation data.

Prerequisites:
    1. Run `python modal/prepare_qwen_data.py` to generate clean training data
    2. Modal secrets configured:
        modal secret create huggingface HF_TOKEN=hf_your_token
    3. Upload training data to the Modal volume:
        modal volume create twi-training-data
        modal volume put twi-training-data twi-dataset/qwen_train.jsonl qwen_train.jsonl
        modal volume put twi-training-data twi-dataset/qwen_val.jsonl qwen_val.jsonl

Deploy:
    modal run modal/train_qwen.py
"""

import modal
import os

# ─── Modal Setup ──────────────────────────────────────────────
app = modal.App("twi-qwen-train")

# Volume for training data + checkpoints
training_vol = modal.Volume.from_name("twi-training-data", create_if_missing=True)
VOL_PATH = "/data"

# Model config
MODEL_ID = "Qwen/Qwen3.5-9B"
OUTPUT_MODEL_NAME = "twi-qwen-v1"  # name on HuggingFace Hub

# Container image with all training dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.4.0",
        "transformers>=4.51.0",
        "accelerate>=0.34.0",
        "bitsandbytes>=0.45.0",
        "peft>=0.14.0",
        "trl>=0.16.0",
        "datasets>=3.0.0",
        "huggingface_hub>=0.27.0",
        "safetensors",
        "sentencepiece",
        "protobuf",
        "wandb",
    )
)


# ─── Training Function ───────────────────────────────────────
@app.function(
    image=image,
    gpu="A100-80GB",
    secrets=[modal.Secret.from_name("huggingface")],
    volumes={VOL_PATH: training_vol},
    timeout=7200,  # 2 hours max
)
def train():
    import torch
    from datasets import load_dataset
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from trl import SFTTrainer, SFTConfig

    hf_token = os.environ["HF_TOKEN"]
    train_path = os.path.join(VOL_PATH, "qwen_train.jsonl")
    val_path = os.path.join(VOL_PATH, "qwen_val.jsonl")

    # Verify data exists
    if not os.path.exists(train_path):
        raise FileNotFoundError(
            f"{train_path} not found. Upload data first:\n"
            "  modal volume put twi-training-data twi-dataset/qwen_train.jsonl qwen_train.jsonl"
        )

    print(f"Loading training data from {train_path}")
    dataset = load_dataset(
        "json",
        data_files={"train": train_path, "validation": val_path},
    )
    print(f"Train: {len(dataset['train'])} examples")
    print(f"Val:   {len(dataset['validation'])} examples")

    # ─── Tokenizer ────────────────────────────────────────────
    print(f"\nLoading tokenizer: {MODEL_ID}")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        token=hf_token,
        trust_remote_code=True,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # ─── 4-bit Quantization (QLoRA) ──────────────────────────
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    # ─── Load Model ──────────────────────────────────────────
    print(f"Loading model: {MODEL_ID} (4-bit)")

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        token=hf_token,
        trust_remote_code=True,
        attn_implementation="sdpa",
    )
    model = prepare_model_for_kbit_training(model)

    # ─── LoRA Config ─────────────────────────────────────────
    lora_config = LoraConfig(
        r=64,
        lora_alpha=128,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )

    model = get_peft_model(model, lora_config)
    trainable, total = model.get_nb_trainable_parameters()
    print(f"\nTrainable params: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")

    # ─── Format dataset for chat template ────────────────────
    def format_chat(example):
        """Apply Qwen chat template to messages."""
        text = tokenizer.apply_chat_template(
            example["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )
        return {"text": text}

    print("Formatting dataset with Qwen chat template...")
    dataset = dataset.map(format_chat, num_proc=4)

    # Show a sample
    print("\n--- Sample formatted input ---")
    print(dataset["train"][0]["text"][:500])
    print("---\n")

    # ─── Training Config ─────────────────────────────────────
    output_dir = os.path.join(VOL_PATH, "checkpoints")

    sft_config = SFTConfig(
        output_dir=output_dir,

        # Training hyperparams
        num_train_epochs=3,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=4,  # effective batch = 16
        learning_rate=2e-4,
        weight_decay=0.01,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",

        # SFT-specific
        max_length=1024,
        dataset_text_field="text",
        packing=True,

        # Precision
        bf16=True,
        tf32=True,

        # Eval + Logging
        eval_strategy="steps",
        eval_steps=200,
        logging_steps=25,
        save_strategy="steps",
        save_steps=500,
        save_total_limit=3,

        # Misc
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        report_to="none",  # set to "wandb" if you want logging
        seed=42,
    )

    # ─── Train ───────────────────────────────────────────────
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        processing_class=tokenizer,
        args=sft_config,
    )

    print("Starting training...\n")
    train_result = trainer.train()
    print(f"\nTraining complete!")
    print(f"  Total steps: {train_result.global_step}")
    print(f"  Train loss:  {train_result.training_loss:.4f}")

    # ─── Save LoRA Adapter ───────────────────────────────────
    adapter_path = os.path.join(VOL_PATH, "adapter")
    print(f"\nSaving LoRA adapter to {adapter_path}")
    trainer.save_model(adapter_path)
    tokenizer.save_pretrained(adapter_path)

    # Persist to volume
    training_vol.commit()
    print("Saved to Modal volume.")

    # ─── Push to HuggingFace Hub ─────────────────────────────
    print(f"\nPushing adapter to HuggingFace: travis-moore/{OUTPUT_MODEL_NAME}")
    model.push_to_hub(
        f"travis-moore/{OUTPUT_MODEL_NAME}",
        token=hf_token,
        private=True,
    )
    tokenizer.push_to_hub(
        f"travis-moore/{OUTPUT_MODEL_NAME}",
        token=hf_token,
        private=True,
    )
    print("Pushed to HuggingFace Hub!")

    return {
        "steps": train_result.global_step,
        "train_loss": train_result.training_loss,
        "adapter_path": adapter_path,
        "hub_repo": f"travis-moore/{OUTPUT_MODEL_NAME}",
    }


# ─── Merge LoRA → Full Model (optional, run separately) ──────
@app.function(
    image=image,
    gpu="A100-80GB",
    secrets=[modal.Secret.from_name("huggingface")],
    volumes={VOL_PATH: training_vol},
    timeout=3600,
)
def merge_and_push():
    """
    Merge LoRA adapter into base model and push the full merged model.
    Run after training: modal run modal/train_qwen.py::merge_and_push
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    hf_token = os.environ["HF_TOKEN"]
    adapter_path = os.path.join(VOL_PATH, "adapter")
    merged_name = f"{OUTPUT_MODEL_NAME}-merged"

    print(f"Loading base model: {MODEL_ID}")
    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        token=hf_token,
        trust_remote_code=True,
    )

    print(f"Loading LoRA adapter from {adapter_path}")
    model = PeftModel.from_pretrained(base_model, adapter_path)

    print("Merging LoRA weights into base model...")
    model = model.merge_and_unload()

    tokenizer = AutoTokenizer.from_pretrained(adapter_path)

    print(f"Pushing merged model to travis-moore/{merged_name}")
    model.push_to_hub(
        f"travis-moore/{merged_name}",
        token=hf_token,
        private=True,
    )
    tokenizer.push_to_hub(
        f"travis-moore/{merged_name}",
        token=hf_token,
        private=True,
    )

    print(f"Done! Merged model at: travis-moore/{merged_name}")
    return {"hub_repo": f"travis-moore/{merged_name}"}


# ─── Entry Point ─────────────────────────────────────────────
@app.local_entrypoint()
def main():
    print("=" * 60)
    print("  Twi AI — Qwen3.5-9B Fine-Tuning")
    print("=" * 60)
    # Use spawn() so the function runs detached on Modal —
    # the local client can disconnect without killing training.
    fc = train.spawn()
    print(f"\n  Training spawned on Modal!")
    print(f"  Function call ID: {fc.object_id}")
    print(f"\n  Monitor progress at: https://modal.com/apps")
    print(f"  The function will run to completion on Modal's servers.")
    print(f"  Checkpoints saved every 500 steps to Modal volume.")
    print(f"  Final model pushed to: travis-moore/{OUTPUT_MODEL_NAME}")
    print(f"\n  After training completes, merge the model:")
    print(f"    modal run modal/train_qwen.py::merge_and_push")
    print(f"{'=' * 60}")
