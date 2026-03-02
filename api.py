"""
FastAPI endpoint for Transcription-Summarization Pipeline.
Provides REST API for frontend integration.
"""
import os
import tempfile
import shutil
import uuid
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import pipeline components
from app.services.pipeline import TranscribeSummaryPipeline
from app.models.meeting import MEETING_TYPES, get_meeting_types_menu
from app.utils.export import export_transcript_to_docx, export_summary_to_docx

# Initialize FastAPI app
app = FastAPI(
    title="Transcribe-Summary API",
    description="API for transcribing audio files and generating AI summaries",
    version="2.0.0"
)

# Session storage for speaker clips (maps session_id -> clip_dir path)
# In production, use Redis or a proper session store
clip_sessions: Dict[str, str] = {}

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
    alignment: float
    diarization: float
    summarization: float
    total: float

class SpeakerClipInfo(BaseModel):
    clip_filename: str
    start: float
    end: float
    duration: float

class TranscribeSummarizeResponse(BaseModel):
    success: bool
    audio_file: str
    audio_length_seconds: float
    processing_time: ProcessingTime
    transcript: TranscriptResponse
    summary: str
    speaker_clips: dict  # { "คนพูด 1": { clip_filename, start, end, duration } }
    session_id: str  # For fetching audio clips


# Request models for export
class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    speaker: str = None

class ExportTranscriptRequest(BaseModel):
    segments: List[TranscriptSegment]
    audio_file: str = ""
    audio_length_seconds: float = 0

class ExportSummaryRequest(BaseModel):
    summary: str
    speaker_summary: dict = None  # Optional: speaking_time and word_count per speaker
    meeting_type_id: int = 0  # Meeting type for position formatting


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
    meeting_type_id: int = Form(0, description="Meeting type ID (0=auto-detect, 1-11=specific type)"),
):
    """
    Transcribe audio file and generate AI summary.
    
    - **audio**: Audio file (mp3, wav, m4a, etc.)
    - **meeting_type_id**: Meeting type for summary structure (0 = auto-detect)
    
    Returns transcript with speaker diarization, AI-generated summary, and speaker audio clips.
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
        
        # Run pipeline (no speaker names — user will fill in after)
        pipeline = TranscribeSummaryPipeline()
        result = pipeline.process(temp_file, meeting_type_id=meeting_type_id)
        
        # Generate session ID for clip access
        session_id = str(uuid.uuid4())
        clip_dir = result.get('clip_dir', '')
        if clip_dir and os.path.exists(clip_dir):
            clip_sessions[session_id] = clip_dir
        
        # Build speaker clips response (without file paths, just filenames)
        speaker_clips_response = {}
        for speaker, clip_info in result.get('speaker_clips', {}).items():
            speaker_clips_response[speaker] = {
                "clip_filename": clip_info['clip_filename'],
                "start": clip_info['start'],
                "end": clip_info['end'],
                "duration": clip_info['duration'],
            }
        
        # Build response
        return TranscribeSummarizeResponse(
            success=True,
            audio_file=audio.filename,
            audio_length_seconds=result['audio_length_seconds'],
            processing_time=ProcessingTime(
                model_load=result['processing_time']['model_load'],
                audio_load=result['processing_time']['audio_load'],
                transcription=result['processing_time']['transcription'],
                alignment=result['processing_time'].get('alignment', 0),
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
            summary=result['summary'],
            speaker_clips=speaker_clips_response,
            session_id=session_id,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    finally:
        # Cleanup temp files
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


# ===================== EXPORT ENDPOINTS =====================

@app.post("/api/export/transcript")
async def export_transcript(request: ExportTranscriptRequest):
    """
    Export transcript segments to DOCX file.
    """
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "transcript.docx")
    
    try:
        # Convert segments to dict format
        segments = [seg.model_dump() for seg in request.segments]
        
        # Generate DOCX
        export_transcript_to_docx(
            segments=segments,
            output_path=output_path,
            audio_file=request.audio_file,
            audio_length=request.audio_length_seconds
        )
        
        return FileResponse(
            path=output_path,
            filename="transcript.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True)
        )
    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


@app.post("/api/export/summary")
async def export_summary(request: ExportSummaryRequest):
    """
    Export summary text to DOCX file.0
    """
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "summary.docx")
    
    try:
        # Generate DOCX with optional speaker header section and meeting type
        export_summary_to_docx(
            summary_text=request.summary,
            output_path=output_path,
            speaker_summary=request.speaker_summary,
            meeting_type_id=request.meeting_type_id
        )
        
        return FileResponse(
            path=output_path,
            filename="summary.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True)
        )
    except Exception as e:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


# ===================== SPEAKER CLIP ENDPOINTS =====================

@app.get("/api/speaker-clip/{session_id}/{filename}")
async def get_speaker_clip(session_id: str, filename: str):
    """
    Serve a speaker audio clip file.
    
    - **session_id**: Session ID from transcribe-summarize response
    - **filename**: Clip filename (e.g., speaker_0.mp3)
    """
    # Validate session
    clip_dir = clip_sessions.get(session_id)
    if not clip_dir or not os.path.exists(clip_dir):
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    # Validate filename (prevent path traversal)
    if '/' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    clip_path = os.path.join(clip_dir, filename)
    if not os.path.exists(clip_path):
        raise HTTPException(status_code=404, detail="Clip not found")
    
    return FileResponse(
        path=clip_path,
        media_type="audio/mpeg",
        filename=filename
    )


@app.delete("/api/session/{session_id}")
async def cleanup_session(session_id: str):
    """
    Cleanup speaker clips for a session.
    Call this when the user is done with the results.
    """
    clip_dir = clip_sessions.pop(session_id, None)
    if clip_dir and os.path.exists(clip_dir):
        shutil.rmtree(clip_dir, ignore_errors=True)
    
    return {"success": True, "message": "Session cleaned up"}


# ===================== STARTUP =====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
