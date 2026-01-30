# WhisperX Thai Transcription + AI Summary Pipeline

> ⚠️ **สถานะ: กำลังพัฒนา (Work in Progress)**

Thai speech-to-text using WhisperX with speaker diarization + GPT-4o summarization.

## ✨ Features
- 🎯 OpenAI Whisper large-v3 model
- 🗣️ Speaker diarization (แยกผู้พูด)
- 🇹🇭 Thai language support
- 🤖 **AI Summary** - สรุปใจความสำคัญด้วย GPT-4o
- 🐳 Docker ready (CUDA/GPU)
- 👥 **Speaker Analysis** - วิเคราะห์บทบาทผู้พูด
- 📋 **Auto Meeting Type Detection** - ระบุประเภทการประชุม 11 รูปแบบ
- 📄 **DOCX Export** - ส่งออกไฟล์ Transcript และ Summary

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
# Run full pipeline (Transcription + Summary + Export)
sudo docker compose run whisperx python TM.py

# Or transcription only (without summary)
sudo docker compose run whisperx python Whisper_Test.py
```

## 📊 Output

เมื่อรัน `TM.py` จะได้:

### Console Output
```
📊 PROCESSING SUMMARY   → Processing time breakdown
📝 FULL TRANSCRIPT      → Timestamped transcript with speakers
📈 SPEAKER SUMMARY      → Speaking time per person
📋 COMBINED TEXT        → Full text without timestamps
🤖 AI SUMMARY           → GPT-4o summary with speaker analysis
```

### DOCX Files
```
📄 Files exported:
   - audio/filename_transcript.docx  → Raw transcript (ตาราง + Combined Text)
   - audio/filename_summary.docx     → AI Summary
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
├── TM.py                   # Main pipeline (Transcription + Summary + Export)
├── Whisper_Test.py         # Transcription only
├── SummaryModel.py         # GPT-4o summary module
│   ├── summarize_transcription()      # Basic summary
│   └── summarize_with_diarization()   # Summary with speaker analysis
├── ExportUtils.py          # DOCX export utilities
│   ├── export_transcript_to_docx()    # Raw transcript export
│   ├── export_summary_to_docx()       # Summary export
│   └── export_both()                  # Export both files
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example            # Environment template
└── audio/                  # Put audio files here
```

## 🔄 Pipeline Flow

```
Audio File
    ↓
[WhisperX Transcription] → [Clear VRAM]
    ↓
[Speaker Diarization] → Build speaker summary
    ↓
[GPT-4o Summary API] ← Transcript + Speaker Data
    ↓
[Export DOCX] → transcript.docx + summary.docx
    ↓
[Output Complete]
```

## 📝 TODO
- [x] Pipeline prompt customization สำหรับสร้างสรุปประชุม
- [x] Auto-detect meeting type (11 ประเภท)
- [x] Speaker role analysis จาก diarization data
- [x] **Export to DOCX (Transcript + Summary)**
- [ ] ปรับปรุงความแม่นยำภาษาไทย
- [ ] เพิ่ม alignment model สำหรับภาษาไทย
- [ ] เพิ่มการ export เป็น SRT/VTT
- [ ] เพิ่ม REST API interface

## 📄 License

MIT License
