"""
FastAPI endpoint for Transcription-Summarization Pipeline.
Provides REST API for frontend integration.
"""
import os
import tempfile
import shutil
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import pipeline components
from app.services.pipeline import TranscribeSummaryPipeline
from app.models.meeting import MEETING_TYPES, get_meeting_types_menu

# Initialize FastAPI app
app = FastAPI(
    title="Transcribe-Summary API",
    description="API for transcribing audio files and generating AI summaries",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===================== RESPONSE MODELS =====================

class HealthResponse(BaseModel):
    status: str
    message: str

class MeetingTypeInfo(BaseModel):
    id: int
    name: str
    thai: str
    structure: str
    key_focus: str

class MeetingTypesResponse(BaseModel):
    success: bool
    meeting_types: list[MeetingTypeInfo]

class SpeakerSummary(BaseModel):
    speaking_time: dict
    word_count: dict

class TranscriptResponse(BaseModel):
    segments: list
    combined_text: str
    speaker_summary: SpeakerSummary

class ProcessingTime(BaseModel):
    model_load: float
    audio_load: float
    transcription: float
    diarization: float
    summarization: float
    total: float

class TranscribeSummarizeResponse(BaseModel):
    success: bool
    audio_file: str
    audio_length_seconds: float
    processing_time: ProcessingTime
    transcript: TranscriptResponse
    summary: str


# ===================== ENDPOINTS =====================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        message="Transcribe-Summary API is running"
    )


@app.get("/api/meeting-types", response_model=MeetingTypesResponse)
async def get_meeting_types():
    """Get list of available meeting types"""
    types_list = []
    for type_id, info in MEETING_TYPES.items():
        types_list.append(MeetingTypeInfo(
            id=type_id,
            name=info['name'],
            thai=info['thai'],
            structure=info['structure'],
            key_focus=info.get('key_focus', '')
        ))
    
    return MeetingTypesResponse(
        success=True,
        meeting_types=types_list
    )


@app.post("/api/transcribe-summarize", response_model=TranscribeSummarizeResponse)
async def transcribe_summarize(
    audio: UploadFile = File(..., description="Audio file to transcribe"),
    meeting_type_id: int = Form(0, description="Meeting type ID (0=auto-detect, 1-11=specific type)")
):
    """
    Transcribe audio file and generate AI summary.
    
    - **audio**: Audio file (mp3, wav, m4a, etc.)
    - **meeting_type_id**: Meeting type for summary structure (0 = auto-detect)
    
    Returns transcript with speaker diarization and AI-generated summary.
    """
    # Validate meeting type
    if meeting_type_id < 0 or meeting_type_id > 11:
        raise HTTPException(status_code=400, detail="meeting_type_id must be between 0 and 11")
    
    # Validate file type
    allowed_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg', '.webm', '.mp4']
    file_ext = os.path.splitext(audio.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file to temp location
    temp_dir = tempfile.mkdtemp()
    temp_file = os.path.join(temp_dir, audio.filename)
    
    try:
        # Write uploaded file
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        
        # Run pipeline
        pipeline = TranscribeSummaryPipeline()
        result = pipeline.process(temp_file, meeting_type_id=meeting_type_id)
        
        # Build response
        return TranscribeSummarizeResponse(
            success=True,
            audio_file=audio.filename,
            audio_length_seconds=result['audio_length_seconds'],
            processing_time=ProcessingTime(
                model_load=result['processing_time']['model_load'],
                audio_load=result['processing_time']['audio_load'],
                transcription=result['processing_time']['transcription'],
                diarization=result['processing_time']['diarization'],
                summarization=result['processing_time']['summarization'],
                total=result['processing_time']['total']
            ),
            transcript=TranscriptResponse(
                segments=result['full_transcript']['segments'],
                combined_text=result['full_transcript']['combined_text'],
                speaker_summary=SpeakerSummary(
                    speaking_time=result['full_transcript']['speaker_summary']['speaking_time'],
                    word_count=result['full_transcript']['speaker_summary']['word_count']
                )
            ),
            summary=result['summary']
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    finally:
        # Cleanup temp files
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


# ===================== STARTUP =====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
