# WhisperX Thai Transcription

> ⚠️ **สถานะ: กำลังพัฒนา (Work in Progress)**

Thai speech-to-text using WhisperX with speaker diarization.

## ✨ Features
- 🎯 OpenAI Whisper large-v3 model
- 🗣️ Speaker diarization (แยกผู้พูด)
- 🇹🇭 Thai language support
- 🐳 Docker ready (CUDA/GPU)

## 🚀 Quick Start

### 1. Clone
```bash
git clone https://github.com/Theme-P/whisperx-prompt-customize.git
cd whisperx-prompt-customize
```

### 2. Build Docker
```bash
sudo docker compose build
```

### 3. Run
```bash
# Put audio files in ./audio folder, then:
sudo docker compose run --rm whisperx

# Input path: /app/audio/your_file.mp3
```

## ⚙️ Configuration
| Parameter | Value | Description |
|-----------|-------|-------------|
| Model | large-v3 | OpenAI Whisper |
| Compute Type | float16 | GPU optimized |
| Batch Size | 24 | For A100 GPU |
| Beam Size | 5 | Best quality |

## 📁 Structure
```
whisperx-prompt-customize/
├── Whisper_Test.py      # Main script
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── audio/               # Put audio files here
```

## 📝 TODO
- [ ] ปรับปรุงความแม่นยำภาษาไทย
- [ ] เพิ่ม alignment model สำหรับภาษาไทย
- [ ] เพิ่มการ export เป็น SRT/VTT
