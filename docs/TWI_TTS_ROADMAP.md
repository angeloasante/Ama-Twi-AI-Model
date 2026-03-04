# 🇬🇭 Twi Text-to-Speech (TTS) Model Roadmap

Build a voice synthesis system like ElevenLabs that speaks Twi naturally.

---

## 📊 Current Dataset (Actual Numbers)

### Merged Dataset Location: `twi-voice-merged/`

| Metric | Value |
|--------|-------|
| **Total Audio Files** | 15,800 |
| **Total Duration** | 9.52 hours (571.3 minutes) |
| **Unique Speakers** | 20 |
| **WAV Files (16kHz)** | 15,560 |
| **MP3 Files (48kHz)** | 240 |

### Data Sources

#### 1. Ghana NLP Multi-Speaker Dataset ✅ Downloaded
**HuggingFace:** `ghananlpcommunity/twi-speech-text-multispeaker-16k`
- **15,560 audio samples**
- **571.3 minutes** of Twi speech
- **16kHz WAV** format
- **Multi-speaker** recordings

#### 2. Mozilla Common Voice Twi ✅ Downloaded
**Source:** [Mozilla Common Voice](https://commonvoice.mozilla.org/tw)
- **240 validated recordings**
- **MP3 format** (48kHz)
- **Community-contributed** voice recordings

#### 3. Twi Asante Male TTS (Pre-trained VITS) - Reference
**Source:** [OpenBible TTS Model](https://aimodels.org/ai-models/text-to-speech-synthesis/twi_asante-male-tts-model-vits-encoding-trained-on-openbible-dataset-at-22050hz/)
- **Pre-trained VITS model** for Twi Asante
- **22,050Hz** sample rate
- **Male voice** trained on OpenBible dataset
- **Can use as:** Base model for fine-tuning or direct inference

---

## 🏗️ Architecture Options

### Option A: Fine-tune XTTS (Recommended)
**Best for:** Low-resource languages, voice cloning
```
XTTS v2 → Fine-tune on Twi data → Twi Voice Clone
```
- Requires only ~30 mins of audio
- Supports voice cloning from short samples
- Multi-lingual by default

### Option B: Fine-tune Coqui TTS / VITS
**Best for:** High-quality single voice
```
VITS Base → Fine-tune on Twi → Custom Twi Voice
```
- Requires 2-5 hours of single-speaker audio
- High quality synthesis
- Can use OpenBible model as starting point

### Option C: Bark + Voice Cloning
**Best for:** Expressive speech with emotions
```
Bark Model → Clone Twi voice samples → Expressive TTS
```
- More expressive (laughs, sighs, etc.)
- Works with minimal data via voice cloning
- Slower inference

---

## 📥 Data Download Scripts

### Download All Datasets

```python
# download_twi_voice_data.py

from datasets import load_dataset
import os
import requests
import soundfile as sf

OUTPUT_DIR = "twi-voice-full"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Download Ghana NLP Multi-Speaker Dataset
print("📥 Downloading Ghana NLP Multi-Speaker Dataset...")
ds = load_dataset("ghananlpcommunity/twi-speech-text-multispeaker-16k")

print(f"Total samples: {len(ds['train']):,}")

# Save to disk
multi_speaker_dir = os.path.join(OUTPUT_DIR, "multi-speaker")
os.makedirs(multi_speaker_dir, exist_ok=True)

metadata = []
for i, sample in enumerate(ds['train']):
    # Save audio
    audio_path = os.path.join(multi_speaker_dir, f"audio_{i:05d}.wav")
    sf.write(audio_path, sample['audio']['array'], sample['audio']['sampling_rate'])
    
    # Collect metadata
    metadata.append({
        'audio': f"audio_{i:05d}.wav",
        'text': sample['text'],
        'speaker_id': sample.get('speaker_id', 'unknown')
    })
    
    if (i + 1) % 100 == 0:
        print(f"  Processed {i+1} samples...")

# Save metadata
import json
with open(os.path.join(multi_speaker_dir, 'metadata.json'), 'w') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f"✅ Saved {len(metadata)} samples to {multi_speaker_dir}")


# 2. Merge with Mozilla Common Voice
print("\n📥 Merging Mozilla Common Voice data...")
import shutil
import pandas as pd

mozilla_dir = "twi-voice"
if os.path.exists(mozilla_dir):
    # Copy clips
    mozilla_clips_dir = os.path.join(OUTPUT_DIR, "mozilla-cv")
    shutil.copytree(os.path.join(mozilla_dir, "clips"), mozilla_clips_dir, dirs_exist_ok=True)
    
    # Convert TSV metadata
    validated = pd.read_csv(os.path.join(mozilla_dir, "validated.tsv"), sep='\t')
    mozilla_meta = []
    for _, row in validated.iterrows():
        mozilla_meta.append({
            'audio': row['path'],
            'text': row['sentence'],
            'speaker_id': row.get('client_id', 'mozilla')[:8]
        })
    
    with open(os.path.join(mozilla_clips_dir, 'metadata.json'), 'w') as f:
        json.dump(mozilla_meta, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Copied {len(mozilla_meta)} Mozilla CV samples")

print("\n🎉 All data downloaded!")
```

### Download Pre-trained VITS Model

```bash
# Download Twi Asante VITS model
mkdir -p twi-voice-full/pretrained-vits
cd twi-voice-full/pretrained-vits

# Model files from OpenBible TTS (check exact URLs)
# These typically include:
# - config.json (model configuration)
# - G_*.pth (generator weights)
# - model.onnx (for inference)
```

---

## 🚀 Training Pipeline

### Step 1: Prepare Data
```python
# prepare_tts_data.py

import os
import json
from pathlib import Path

def prepare_ljspeech_format(input_dir, output_dir):
    """Convert to LJSpeech format for TTS training"""
    os.makedirs(output_dir, exist_ok=True)
    wavs_dir = os.path.join(output_dir, "wavs")
    os.makedirs(wavs_dir, exist_ok=True)
    
    metadata_lines = []
    
    # Load all metadata
    for subdir in ['multi-speaker', 'mozilla-cv']:
        meta_path = os.path.join(input_dir, subdir, 'metadata.json')
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                data = json.load(f)
            
            for item in data:
                # Copy/convert audio to wav
                src = os.path.join(input_dir, subdir, item['audio'])
                if os.path.exists(src):
                    dst = os.path.join(wavs_dir, item['audio'].replace('.mp3', '.wav'))
                    # Convert if needed (use ffmpeg or pydub)
                    
                    # Add to metadata (LJSpeech format: filename|text|text)
                    basename = Path(item['audio']).stem
                    metadata_lines.append(f"{basename}|{item['text']}|{item['text']}")
    
    # Write metadata.csv
    with open(os.path.join(output_dir, "metadata.csv"), 'w') as f:
        f.write('\n'.join(metadata_lines))
    
    print(f"Prepared {len(metadata_lines)} samples in LJSpeech format")

prepare_ljspeech_format("twi-voice-full", "twi-tts-dataset")
```

### Step 2: Train with Coqui TTS

```bash
# Install Coqui TTS
pip install TTS

# Train VITS model
tts --train \
    --config_path config.json \
    --model_name vits \
    --dataset_path twi-tts-dataset \
    --output_path twi-vits-model
```

### Step 3: Fine-tune XTTS (Alternative)

```python
# finetune_xtts.py

from TTS.api import TTS
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts

# Load pre-trained XTTS
config = XttsConfig()
config.load_json("path/to/xtts_config.json")

model = Xtts.init_from_config(config)
model.load_checkpoint(config, checkpoint_dir="path/to/xtts_checkpoint")

# Fine-tune on Twi data
# (See Coqui TTS documentation for full training script)
```

---

## 🎤 Inference Pipeline

### Generate Twi Speech

```python
# twi_tts_inference.py

from TTS.api import TTS

# Load fine-tuned model
tts = TTS(model_path="twi-vits-model/best_model.pth",
          config_path="twi-vits-model/config.json")

# Generate speech
text = "Akwaaba! Wo ho te sɛn?"  # Welcome! How are you?
tts.tts_to_file(text=text, file_path="output.wav")

print("Generated: output.wav")
```

### Voice Cloning with XTTS

```python
# Clone a specific Twi voice
from TTS.api import TTS

tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

# Use a reference Twi voice clip
tts.tts_to_file(
    text="Medaase! Meda wo ase paa.",
    file_path="cloned_output.wav",
    speaker_wav="twi-voice/clips/sample_speaker.wav",  # Reference audio
    language="tw"  # Twi language code
)
```

---

## 📋 Implementation Checklist

### Phase 1: Data Collection ✅ COMPLETE
- [x] Mozilla Common Voice Twi (240 validated clips)
- [x] Ghana NLP multi-speaker dataset (15,560 samples)
- [x] Merge all datasets into `twi-voice-merged/` (15,800 total)
- [ ] Download/evaluate OpenBible VITS model (optional)

### Phase 2: Data Preparation
- [ ] Convert all audio to 22050Hz WAV
- [ ] Normalize text (handle Twi characters: ɛ, ɔ, etc.)
- [ ] Create train/val/test splits (80/10/10)
- [ ] Generate LJSpeech-format metadata

### Phase 3: Model Training
- [ ] Fine-tune XTTS v2 on Twi data
- [ ] OR train VITS from scratch
- [ ] Evaluate on held-out test set
- [ ] Optimize for inference speed

### Phase 4: Integration
- [ ] Connect to Twi LLM text output
- [ ] Build voice cloning pipeline
- [ ] Create API endpoint
- [ ] Deploy (Gradio/FastAPI)

---

## 📁 Project Structure

```
twi ai/
├── twi-dataset/              # Text conversation data (2M+ samples)
│   ├── conversations.jsonl   # Training data
│   └── conversations_val.jsonl  # Validation data
├── twi-voice/                # Original Mozilla Common Voice
├── twi-voice-full/           # Downloaded datasets (raw)
│   ├── multi-speaker/        # Ghana NLP (15,560 WAV)
│   └── mozilla-cv/           # Mozilla clips (240 MP3)
├── twi-voice-merged/         # 🎯 MERGED DATASET (15,800 files)
│   ├── metadata.json         # All transcriptions + metadata
│   ├── stats.json            # Dataset statistics
│   └── twi_*.wav/mp3         # All audio files
├── train_twi_llama.ipynb     # LLM training notebook
├── download_twi_voice_data.py
├── merge_voice_folders.py
└── TWI_TTS_ROADMAP.md
```

---

## 🎯 Training Estimates (with 9.5 hours of audio)

| Approach | Quality | Training Time | GPU Required |
|----------|---------|---------------|--------------|
| XTTS Fine-tune | Very Good | 4-8 hours | T4/V100 |
| VITS Fine-tune | Excellent | 12-24 hours | T4/V100 |
| Coqui TTS | Good | 8-16 hours | T4/V100 |

With **9.5 hours of diverse multi-speaker audio**, you have enough data for high-quality TTS training!

---

## 🔗 Resources

- **Coqui TTS:** https://github.com/coqui-ai/TTS
- **XTTS v2:** https://huggingface.co/coqui/XTTS-v2
- **Ghana NLP:** https://huggingface.co/ghananlpcommunity
- **OpenBible TTS:** https://aimodels.org/ai-models/text-to-speech-synthesis/
- **Mozilla Common Voice:** https://commonvoice.mozilla.org/tw

---

## 🏁 Next Steps

1. **Complete LLM training** (currently running on Colab)
2. **Download voice datasets** (run `download_twi_voice_data.py`)
3. **Prepare training data** (run `prepare_tts_data.py`)
4. **Train TTS model** (XTTS recommended for speed)
5. **Integrate** text model + voice model

**Goal:** A full Twi AI that you talk to and it responds in spoken Twi! 🎤🇬🇭
