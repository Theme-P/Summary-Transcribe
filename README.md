# Timsum

> Thai speech-to-text using WhisperX with speaker diarization + GPT-4.1 summarization.
> Full-stack application with React frontend and FastAPI backend.

## ✨ Features
- 🎯 OpenAI Whisper large-v3 model
- 🗣️ Speaker diarization (แยกผู้พูด) + Word-level alignment
- 🇹🇭 Thai language support
- 🤖 **AI Summary** - สรุปใจความสำคัญด้วย GPT-4.1
- 🐳 Docker ready (CUDA/GPU)
- 👥 **Speaker Identification** - ฟังเสียงตัวอย่าง ~10 วินาทีของแต่ละผู้พูด แล้วกรอกชื่อ+ตำแหน่ง
- 📋 **Auto Meeting Type Detection** - ระบุประเภทการประชุม 11 รูปแบบ
- 📄 **DOCX Export** - ส่งออกไฟล์ Transcript และ Summary พร้อมรายชื่อผู้เข้าร่วม
- 🌐 **Web UI** - React frontend โทนสีครีม สำหรับอัพโหลดเสียงและระบุตัวตนผู้พูด
- 🔌 **REST API** - FastAPI backend สำหรับ integration

## 🌐 Web UI

Frontend UI สำหรับใช้งานผ่าน browser:
- **อัพโหลดไฟล์เสียง** (drag & drop) + เลือกประเภทการประชุม
- **Speaker Identification** หลังประมวลผล — ฟัง audio clip ของแต่ละผู้พูด แล้วกรอกชื่อ
- **Client-side name replacement** — ชื่อจริงแทนที่ "คนพูด X" ทันทีทั้ง Transcript + Summary
- แสดง Transcript, Summary, และ Speaker Stats
- ดาวน์โหลด DOCX ได้ทันที

## 🎯 Supported Meeting Types

| ประเภท | English | โครงสร้างหลัก |
|--------|---------|--------------|
| ประชุมผู้ถือหุ้น | Shareholder Meeting | วาระ → มติ → เงินปันผล |
| ประชุมคณะกรรมการ | Board Meeting | นโยบาย → การอนุมัติ → มติ |
| ประชุมวางแผน | Planning Meeting | เป้าหมาย → แผนงาน → ไทม์ไลน์ |
| รายงานความคืบหน้า | Progress Update | สถานะ → ปัญหา → แนวทางแก้ |
| ประชุมเชิงกลยุทธ์ | Strategy Meeting | ทิศทาง → กลยุทธ์ → Action Plan |
| ประชุมแก้ไขปัญหา | Incident Review | ปัญหา → สาเหตุ → การป้องกัน |
| ประชุมลูกค้า | Client Meeting | ข้อเสนอ → Feedback → Next Steps |
| เชิงปฏิบัติการ | Workshop | หัวข้อ → บทเรียน → Action Items |
| ประชุมผู้บริหาร | Executive Meeting | การตัดสินใจ → มติ |
| ประชุมทีมงาน | Team Meeting | อัพเดต → มอบหมาย → ปัญหา |
| ประชุมทั่วไป | General Meeting | วาระ → หารือ → มติ |

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/Theme-P/Summary-Transcribe.git
cd Summary-Transcribe

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys
```

### 2. Run with Docker Compose
```bash
# Build and run both frontend + backend
docker compose up -d --build

# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
```

### 3. Run CLI (without frontend)
```bash
# Run full pipeline (Transcription + Summary + Export)
docker compose run backend python main.py
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/meeting-types` | List meeting types |
| `POST` | `/api/transcribe-summarize` | Transcribe + Summarize audio |
| `GET` | `/api/speaker-clip/{session_id}/{filename}` | Serve speaker audio clip |
| `DELETE` | `/api/session/{session_id}` | Cleanup session clips |
| `POST` | `/api/export/transcript` | Export transcript to DOCX |
| `POST` | `/api/export/summary` | Export summary to DOCX |

## ⚙️ Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| Model | large-v3 | OpenAI Whisper |
| Compute Type | float16 | GPU optimized |
| Batch Size | 24 | For A100 GPU |
| Beam Size | 5 | Best quality |
| Summary API | GPT-4.1 | Via NTC AI Gateway |
| VAD Onset | 0.500 | Speech start threshold |
| VAD Offset | 0.363 | Speech end threshold |

## 🔐 Environment Variables

Create `.env` file with:
```env
# Hugging Face Token (for speaker diarization)
HF_TOKEN=your_huggingface_token

# NTC AI Gateway (for GPT-4.1 summary)
NTC_API_KEY=your_ntc_api_key
NTC_API_URL=https://aigateway.ntictsolution.com/v1/chat/completions
```

## 📁 Project Structure

```
Summary-Transcribe/
├── app/
│   ├── core/
│   │   └── config.py              # PipelineConfig settings
│   ├── models/
│   │   └── meeting.py             # Meeting types definitions (11 types)
│   ├── services/
│   │   ├── pipeline.py            # TranscribeSummaryPipeline
│   │   └── summarizer.py          # GPT-4.1 summary with diarization
│   └── utils/
│       ├── audio_clip.py          # Speaker audio clip extraction (ffmpeg)
│       ├── export.py              # DOCX export (transcript + summary)
│       └── formatting.py          # Speaker & time formatting helpers
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Main application (single-column)
│   │   └── components/
│   │       ├── FileUploader.jsx
│   │       ├── MeetingTypeSelect.jsx
│   │       ├── ProcessingStatus.jsx
│   │       ├── ResultsTabs.jsx
│   │       └── SpeakerIdentification.jsx  # Post-process speaker naming
│   ├── Dockerfile
│   └── nginx.conf
├── tests/
│   ├── test_gpt41.py              # GPT-4.1 API test
│   └── whisper_playground.py      # WhisperX test script
├── api.py                         # FastAPI REST API
├── main.py                        # CLI entry point
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── audio/                         # Put audio files here
```

## 🔄 Pipeline Flow

```
Audio File
    ↓
[WhisperX Transcription] → [Clear VRAM]
    ↓
[Word-level Alignment] → Better speaker boundaries
    ↓
[Speaker Diarization] → Identify speakers → Extract ~10s audio clips
    ↓
[GPT-4.1 Summary API] ← Transcript + Speaker Data (generic labels)
    ↓
[Speaker Identification UI] → User listens to clips → Inputs names
    ↓
[Client-side Name Replacement] → "คนพูด 1" → "ชื่อจริง (ตำแหน่ง)"
    ↓
[Export DOCX] → transcript.docx + summary.docx
```

## 📝 TODO
- [x] Pipeline prompt customization สำหรับสร้างสรุปประชุม
- [x] Auto-detect meeting type (11 ประเภท)
- [x] Speaker role analysis จาก diarization data
- [x] Export to DOCX (Transcript + Summary)
- [x] Refactor to OOP architecture
- [x] REST API (FastAPI)
- [x] Web UI (React + Vite)
- [x] Docker Compose (Frontend + Backend)
- [x] Participant header in Summary DOCX
- [x] Speaker identification (ฟังเสียง → กรอกชื่อหลังประมวลผล)
- [x] Word-level alignment สำหรับ diarization ที่แม่นยำขึ้น
- [x] Audio clip extraction (~10s ต่อผู้พูด)
- [x] Client-side speaker name replacement
- [x] Cream theme UI
- [ ] เพิ่มการ export เป็น SRT/VTT
- [ ] Action Items / มติที่ประชุม extraction
- [ ] Search & Filter transcript
- [ ] Speaker analytics chart
- [ ] ประวัติการประชุม (session history)

## 📄 License

MIT License
