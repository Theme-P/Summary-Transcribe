# WhisperX Thai Transcription + AI Summary Pipeline

> ⚠️ **สถานะ: กำลังพัฒนา (Work in Progress)**

Thai speech-to-text using WhisperX with speaker diarization + GPT-4o summarization.

## ✨ Features
- 🎯 OpenAI Whisper large-v3 model
- 🗣️ Speaker diarization (แยกผู้พูด)
- 🇹🇭 Thai language support
- 🤖 **AI Summary** - สรุปใจความสำคัญด้วย GPT-4o
- 🐳 Docker ready (CUDA/GPU)
- ⚡ **Parallel Processing** - รัน Summary ขนานกับ Diarization

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/Theme-P/whisperx-prompt-customize.git
cd whisperx-prompt-customize

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

### 2. Build Docker
```bash
sudo docker compose build
```

### 3. Run

```bash
# Start container
sudo docker compose run --rm whisperx

# Option 1: Transcription + Summary (Pipeline ใหม่)
python TranscribeSummaryPipeline.py

# Option 2: Transcription only (เดิม)
python Whisper_Test.py
```

## 📊 Output Examples

### TranscribeSummaryPipeline.py
```
📊 PROCESSING SUMMARY   → Processing time breakdown
📝 FULL TRANSCRIPT      → Timestamped transcript with speakers
📈 SPEAKER SUMMARY      → Speaking time per person
📋 COMBINED TEXT        → Full text without timestamps
🤖 AI SUMMARY           → GPT-4o generated summary
```

## ⚙️ Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| Model | large-v3 | OpenAI Whisper |
| Compute Type | float16 | GPU optimized |
| Batch Size | 24 | For A100 GPU |
| Beam Size | 5 | Best quality |
| Summary API | GPT-4o | Via NTC AI Gateway |

## 🔐 Environment Variables

Create `.env` file with:
```env
# Hugging Face Token (for speaker diarization)
HF_TOKEN=your_huggingface_token

# NTC AI Gateway (for GPT-4o summary)
NTC_API_KEY=your_ntc_api_key
NTC_API_URL=https://aigateway.ntictsolution.com/v1/chat/completions
```

## 📁 Project Structure
```
whisperx-prompt-customize/
├── TranscribeSummaryPipeline.py  # Combined transcription + summary
├── Whisper_Test.py               # Transcription only
├── SummaryModel.py               # GPT-4o summary module
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example                  # Environment template
└── audio/                        # Put audio files here
```

## 🔄 Pipeline Flow

```
Audio File
    ↓
[WhisperX Transcription] → [Clear VRAM] → [Diarization]
                                              ↓
                          [Summary API] ←──parallel──┘
                                              ↓
                          [Combined Output: Transcript + Summary]
```

## 📝 TODO
- [x] **Pipeline prompt customization สำหรับสร้างสรุปประชุมหลังถอดเสียง**
- [ ] ปรับปรุงความแม่นยำภาษาไทย
- [ ] เพิ่ม alignment model สำหรับภาษาไทย
- [ ] เพิ่มการ export เป็น SRT/VTT
- [ ] เพิ่ม REST API interface

## 📄 License

MIT License
