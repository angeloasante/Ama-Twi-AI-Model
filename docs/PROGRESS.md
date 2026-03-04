# Twi AI Assistant - Dataset Build Progress

## Project Goal
Build a conversational AI assistant that:
- Lives in a chat interface
- Understands both Twi and English
- **Always responds in Twi**
- Talks like a real Ghanaian person
- Powered by Llama 3.1 8B Instruct fine-tuned with LoRA

---

## ✅ Completed Tasks

### 1. Data Sources Integrated

| Source | Type | Records | Status |
|--------|------|---------|--------|
| Local `english` file | Parallel sentences | 606,197 | ✅ Done |
| Local `twi` file | Parallel sentences | 606,197 | ✅ Done |
| HF: `english-twi-sentences-non-nouns-sample-100k` | Translation pairs | 100,000 | ✅ Done |
| HF: `english-twi-sentences-non-nouns` (full) | Translation pairs | 1,763,936 | ✅ Done |
| HF: `twi-llm-reasoning-dataset-1k` | Reasoning + responses | 999 | ✅ Done |

### 2. Dataset Processing
- ✅ Created conversation format (system + user + assistant)
- ✅ Built English → Twi pairs (user speaks English, AI responds in Twi)
- ✅ Built Twi → Twi pairs (natural Twi conversation flow)
- ✅ Filtered short/invalid entries
- ✅ Removed 139,118 duplicates
- ✅ Split into 90% train / 10% validation

### 3. Final Dataset Statistics

| File | Size | Conversations |
|------|------|---------------|
| `conversations.jsonl` | **993.1 MB** | 1,837,738 |
| `conversations_val.jsonl` | **110.4 MB** | 204,193 |
| **Total** | **1.1 GB** | **2,041,931** |

---

## Dataset Format

Each conversation follows the Llama chat format:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "Wo yɛ Twi kasa mu ɔboafo a wo te sɛ Ghanani papa. Wo te Twi ne Borɔfo kasa nyinaa ase, nanso wo de Twi nkutoo na ɛgye so. Ka wo nsɛm te sɛ Ghanani a ɔte Ghana - fa Twi nsɛnka ne ɛkasa kwan di dwuma. Yɛ ɔdɔfo, yɛ ayamye, na boa nkurɔfo wɔ wɔn nsɛm nyinaa mu."
    },
    {
      "role": "user", 
      "content": "How are you today?"
    },
    {
      "role": "assistant",
      "content": "Me ho yɛ! Wo nso, wo ho te sɛn?"
    }
  ]
}
```

### System Prompt (Twi)
> "You are a Twi language assistant who is like a true Ghanaian. You understand both Twi and English, but you respond only in Twi. Speak like a Ghanaian living in Ghana - use Twi idioms and expressions. Be friendly, be kind, and help people with all their matters."

---

## Files Created

```
/Users/travismoore/Desktop/twi ai/
├── english                          # Source: English translations
├── twi                              # Source: Twi translations  
├── build_dataset.py                 # Initial dataset builder
├── merge_all_datasets.py            # Full merger with HF data
├── train_twi_llama.ipynb            # Training notebook for Colab
├── download_twi_voice_data.py       # Voice dataset downloader
├── merge_voice_folders.py           # Voice data merger
├── TWI_TTS_ROADMAP.md               # TTS implementation guide
├── PROGRESS.md                      # This file
├── twi-dataset/                     # TEXT DATA
│   ├── conversations.jsonl          # Training (1.8M conversations)
│   └── conversations_val.jsonl      # Validation (204K conversations)
└── twi-voice-merged/                # VOICE DATA (merged)
    ├── metadata.json                # Transcriptions + metadata
    ├── stats.json                   # Statistics
    └── twi_*.wav/mp3                # 15,800 audio files
```

---

## 🎤 Voice Dataset (TTS Training)

### Data Sources

| Source | Files | Duration | Status |
|--------|-------|----------|--------|
| Ghana NLP Multi-Speaker | 15,560 | 571.3 min | ✅ Downloaded |
| Mozilla Common Voice | 240 | ~10 min | ✅ Downloaded |
| **TOTAL** | **15,800** | **~9.5 hours** | ✅ Merged |

### Merged Dataset: `twi-voice-merged/`
- **15,800 total audio files**
- **9.52 hours** of Twi speech
- **20 unique speakers**
- **16kHz WAV** (Ghana NLP) + **48kHz MP3** (Mozilla)
- **Full transcriptions** with speaker IDs

This is excellent data for training a Twi TTS model like ElevenLabs!

---

## 🚀 Training with VS Code + Colab Extension

### Setup
1. Install the **Google Colab** extension in VS Code:
   - Press `Cmd+Shift+X` → Search "Colab" → Install (by Google)
   
2. Open `train_twi_llama.ipynb` in VS Code

3. Click **"Connect to Colab"** in the notebook toolbar
   - Sign in with your Google account
   - Select a GPU runtime (T4 recommended, A100 for faster training)

4. Upload dataset to Google Drive:
   - Copy `twi-dataset/` folder to your Google Drive
   - The notebook will mount Drive automatically

5. Run all cells to train!

### What the Notebook Does
- Loads Llama 3.1 8B Instruct (4-bit quantized)
- Applies LoRA for efficient fine-tuning
- Trains on your Twi conversation data
- Tests the model with sample conversations
- Saves the trained model

---

## 🔜 Next Steps

### Phase 1: LLM Training (In Progress on Colab)
- ✅ Training notebook created
- ✅ Dataset uploaded to Google Drive
- ⏳ Training running on T4 GPU (ETA: 1-2 hours)

### Phase 2: TTS Model Training
1. Prepare voice data (convert to 22050Hz WAV)
2. Fine-tune XTTS v2 or VITS on Twi data
3. Test voice synthesis quality
4. See `TWI_TTS_ROADMAP.md` for full guide

### Phase 3: Integration
- Connect LLM output → TTS input
- Build chat interface with voice output
- Deploy as web app (Gradio/Streamlit)

### Recommended Training Config
```python
# LoRA Config
lora_r = 64
lora_alpha = 16
lora_dropout = 0.1
target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]

# Training
per_device_train_batch_size = 2
gradient_accumulation_steps = 8
learning_rate = 2e-4
num_train_epochs = 1  # Start with 1 epoch
```

### ⚠️ Note on Dataset Size
The full 2M conversation dataset is large (~1.1GB). For Colab Free/Pro:
- Consider using a subset (e.g., 500K conversations)
- Use streaming to avoid memory issues
- Enable gradient checkpointing

---

## Conversation Types in Dataset

| Type | Description | Count |
|------|-------------|-------|
| English → Twi | User speaks English, AI responds in Twi | ~1.5M |
| Twi → Twi | Natural Twi conversation flow | ~500K |
| Reasoning | Complex questions with Twi analysis | 999 |

---

## Date
**Last Updated:** March 1, 2026

## Author
Built by Travis Moore with GitHub Copilot assistance
