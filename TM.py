"""
TM.py - Transcription & Meeting Summary Pipeline
Combined WhisperX Transcription + GPT-4o Summary Pipeline

Output:
1. Full transcript with timestamps and speaker diarization
2. Summary generated from the transcript using GPT-4o
"""

import torch
import gc
import os
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fix for PyTorch 2.6+ compatibility with pyannote
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load

import whisperx
from SummaryModel import summarize_with_diarization, export_to_docx


# ===================== CONFIGURATION =====================
class PipelineConfig:
    """Configuration for the transcription-summary pipeline"""
    
    # Device settings
    DEVICE = "cuda"
    COMPUTE_TYPE = "float16"
    
    # WhisperX settings
    MODEL_NAME = "large-v3"
    BATCH_SIZE = 24
    LANGUAGE = "th"
    
    # Beam search settings
    BEAM_SIZE = 5
    BEST_OF = 5
    PATIENCE = 1.5
    
    # VAD options (optimized for overlapping speech detection)
    VAD_ONSET = 0.400       # Lower = more sensitive to speech start
    VAD_OFFSET = 0.300      # Lower = faster silence detection
    MIN_DURATION_ON = 0.05  # Catch short speech segments
    MIN_DURATION_OFF = 0.05 # Catch short pauses/interruptions
    
    # Speaker diarization settings (for overlapping speech)
    MIN_SPEAKERS = 2        # Minimum expected speakers (None = auto)
    MAX_SPEAKERS = None     # Maximum expected speakers (None = auto)
    
    # HuggingFace token for diarization
    HF_TOKEN = os.environ.get("HF_TOKEN", "")


# ===================== UTILITY FUNCTIONS =====================
def format_speaker(speaker: Optional[str]) -> str:
    """Format speaker label to Thai"""
    if speaker and speaker.startswith('SPEAKER_'):
        num = int(speaker.split('_')[1]) + 1
        return f"คนพูด {num}"
    return speaker or "Unknown"


def format_time(seconds: float) -> str:
    """Format seconds to MM:SS.ms"""
    m = int(seconds // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 100)
    return f"{m:02d}:{s:02d}.{ms:02d}"


def clear_gpu_memory():
    """Clear GPU memory"""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# ===================== TRANSCRIBE SUMMARY PIPELINE =====================
class TranscribeSummaryPipeline:
    """
    Combined pipeline that runs WhisperX transcription and GPT-4o summarization.
    Handles model loading, transcription, speaker diarization, and AI summary.
    """
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.model = None
        self.timing = {}
    
    def _load_model(self):
        """Load WhisperX model with optimized settings"""
        print("🔄 Loading WhisperX model...")
        start = time.time()
        
        self.model = whisperx.load_model(
            self.config.MODEL_NAME,
            self.config.DEVICE,
            compute_type=self.config.COMPUTE_TYPE,
            language=self.config.LANGUAGE,
            asr_options={
                "beam_size": self.config.BEAM_SIZE,
                "best_of": self.config.BEST_OF,
                "patience": self.config.PATIENCE,
                "condition_on_previous_text": True,
                "temperatures": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                "compression_ratio_threshold": 2.2,
                "log_prob_threshold": -0.8,
                "no_speech_threshold": 0.5,
                "initial_prompt": "สวัสดีครับ นี่คือการถอดเสียงภาษาไทย",
                "repetition_penalty": 1.1,
                "length_penalty": 1.0,
            },
            vad_options={
                "vad_onset": self.config.VAD_ONSET,
                "vad_offset": self.config.VAD_OFFSET,
                "min_duration_on": self.config.MIN_DURATION_ON,
                "min_duration_off": self.config.MIN_DURATION_OFF,
            },
        )
        
        self.timing['model_load'] = time.time() - start
        print(f"   ⏱️ Model loaded: {self.timing['model_load']:.2f}s")
    
    def process(self, audio_file: str) -> Dict[str, Any]:
        """
        Process audio file: transcribe and summarize.
        
        Returns structured output with:
        - Full transcript with segments
        - Summary
        - Processing times
        """
        total_start = time.time()
        
        print("=" * 60)
        print("🚀 TranscribeSummaryPipeline - Starting")
        print("=" * 60)
        print(f"📁 Audio file: {audio_file}")
        print()
        
        # Step 1: Load model
        self._load_model()
        
        # Step 2: Load audio
        print("🔄 Loading audio...")
        audio_start = time.time()
        audio = whisperx.load_audio(audio_file)
        audio_time = time.time() - audio_start
        print(f"   ⏱️ Audio loaded: {audio_time:.2f}s")
        
        # Step 3: Transcribe
        print("🎯 Transcribing...")
        trans_start = time.time()
        result = self.model.transcribe(
            audio,
            batch_size=self.config.BATCH_SIZE,
            language=self.config.LANGUAGE,
            task="transcribe",
        )
        trans_time = time.time() - trans_start
        print(f"   ⏱️ Transcription: {trans_time:.2f}s")
        
        # Extract text for summary
        combined_text = ' '.join(
            seg.get('text', '').strip() 
            for seg in result.get('segments', [])
        )
        
        # Clear transcription model to free VRAM
        del self.model
        self.model = None
        clear_gpu_memory()
        
        # Step 2: Run diarization FIRST (needs speaker info for summary)
        print("👥 Running speaker diarization...")
        diarize_start = time.time()
        diarize_model = whisperx.diarize.DiarizationPipeline(
            use_auth_token=self.config.HF_TOKEN,
            device=self.config.DEVICE
        )
        diarize_segments = diarize_model(
            audio,
            min_speakers=self.config.MIN_SPEAKERS,
            max_speakers=self.config.MAX_SPEAKERS,
        )
        diarize_time = time.time() - diarize_start
        print(f"   ⏱️ Diarization: {diarize_time:.2f}s")
        
        # Assign speakers to segments
        result = whisperx.assign_word_speakers(diarize_segments, result)
        
        # Clear diarization model
        del diarize_model
        clear_gpu_memory()
        
        # Build speaker summary and transcript with speaker labels
        segments = sorted(result.get('segments', []), key=lambda x: x['start'])
        speakers_time = {}
        speakers_words = {}
        transcript_lines = []
        
        for segment in segments:
            speaker = format_speaker(segment.get('speaker'))
            duration = segment['end'] - segment['start']
            text = segment.get('text', '').strip()
            word_count = len(text.split())
            speakers_time[speaker] = speakers_time.get(speaker, 0) + duration
            speakers_words[speaker] = speakers_words.get(speaker, 0) + word_count
            # Build transcript with speaker labels
            transcript_lines.append(f"[{speaker}]: {text}")
        
        transcript_with_speakers = "\n".join(transcript_lines)
        speaker_summary = {
            'speaking_time': speakers_time,
            'word_count': speakers_words,
        }
        
        # Step 3: Run summary with diarization data
        print("🤖 Running AI Summary with speaker analysis...")
        summary_start = time.time()
        summary_text = summarize_with_diarization(transcript_with_speakers, speaker_summary)
        summary_time = time.time() - summary_start
        print(f"   ⏱️ Summary API: {summary_time:.2f}s")
        
        total_time = time.time() - total_start
        
        # Calculate audio length and speed
        audio_length = len(audio) / 16000
        speed_factor = audio_length / total_time if total_time > 0 else 0
        
        # Build output
        output = {
            'audio_file': audio_file,
            'processing_time': {
                'model_load': self.timing.get('model_load', 0),
                'audio_load': audio_time,
                'transcription': trans_time,
                'diarization': diarize_time,
                'summarization': summary_time,
                'total': total_time,
            },
            'audio_length_seconds': audio_length,
            'speed_factor': speed_factor,
            'full_transcript': {
                'segments': segments,
                'combined_text': combined_text,
                'transcript_with_speakers': transcript_with_speakers,
                'speaker_summary': speaker_summary,
            },
            'summary': summary_text,
        }
        
        return output
    
    def print_results(self, output: Dict[str, Any]):
        """Pretty print the results"""
        print("\n" + "=" * 60)
        print("📊 PROCESSING SUMMARY")
        print("=" * 60)
        
        pt = output['processing_time']
        print(f"⏱️ Total processing time: {pt['total']:.2f}s")
        print(f"   - Model load: {pt['model_load']:.2f}s")
        print(f"   - Audio load: {pt['audio_load']:.2f}s")
        print(f"   - Transcription: {pt['transcription']:.2f}s")
        print(f"   - Diarization: {pt['diarization']:.2f}s")
        print(f"   - Summarization: {pt['summarization']:.2f}s")
        print(f"   - Audio length: {output['audio_length_seconds']:.1f}s")
        print(f"   - Speed: {output['speed_factor']:.1f}x realtime")
        
        # Transcription results
        print("\n" + "=" * 60)
        print("📝 FULL TRANSCRIPT")
        print("=" * 60)
        print(f"{'เวลาเริ่ม':<10} {'เวลาจบ':<10} {'คนพูด':<12} {'ข้อความ'}")
        print("-" * 60)
        
        for segment in output['full_transcript']['segments']:
            speaker = format_speaker(segment.get('speaker'))
            text = segment.get('text', '').strip()
            start = format_time(segment['start'])
            end = format_time(segment['end'])
            print(f"{start:<10} {end:<10} {speaker:<12} {text}")
        
        # Speaker summary
        print("\n" + "=" * 60)
        print("📈 SPEAKER SUMMARY")
        print("=" * 60)
        
        speakers_time = output['full_transcript']['speaker_summary']['speaking_time']
        speakers_words = output['full_transcript']['speaker_summary']['word_count']
        total_time = sum(speakers_time.values())
        
        for speaker, speaking_time in sorted(speakers_time.items()):
            pct = (speaking_time / total_time * 100) if total_time > 0 else 0
            words = speakers_words.get(speaker, 0)
            print(f"  {speaker}: {format_time(speaking_time)} ({pct:.1f}%) - {words} words")
        
        # Combined text
        print("\n" + "=" * 60)
        print("📋 COMBINED TEXT")
        print("=" * 60)
        print(output['full_transcript']['combined_text'])
        
        # Summary
        print("\n" + "=" * 60)
        print("🤖 AI SUMMARY (GPT-4o)")
        print("=" * 60)
        print(output['summary'])
        
        print("\n" + "=" * 60)
        print("✅ Pipeline completed successfully!")
        print("=" * 60)


# ===================== MAIN =====================
if __name__ == "__main__":
    # Get audio file from user
    audio_file = input("📁 กรุณาใส่ path ไฟล์เสียง: ").strip().strip('"').strip("'")
    
    if not os.path.exists(audio_file):
        print(f"❌ Error: File not found: {audio_file}")
        exit(1)
    
    # Run pipeline
    pipeline = TranscribeSummaryPipeline()
    output = pipeline.process(audio_file)
    pipeline.print_results(output)
    
    # Export to DOCX
    docx_path = os.path.splitext(audio_file)[0] + "_summary.docx"
    try:
        result_path = export_to_docx(
            summary_text=output['summary'],
            output_path=docx_path,
            audio_file=audio_file,
            processing_time={
                **output['processing_time'],
                'audio_length': output['audio_length_seconds']
            },
            speaker_summary=output['full_transcript']['speaker_summary']
        )
        print(f"\n📄 Summary exported to: {result_path}")
    except Exception as e:
        print(f"\n⚠️ Could not export DOCX: {e}")
