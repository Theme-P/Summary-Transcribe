import torch
import gc
import os
import time
import tempfile
from typing import Dict, Any, Optional
import whisperx

from ..core.config import PipelineConfig
from ..models.meeting import MEETING_TYPES
from ..services.summarizer import summarize_with_diarization
from ..utils.formatting import format_speaker, format_time
from ..utils.audio_clip import extract_speaker_clips

# Fix for PyTorch 2.6+ compatibility with pyannote
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load

def clear_gpu_memory():
    """Clear GPU memory"""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

class TranscribeSummaryPipeline:
    """
    Combined pipeline that runs WhisperX transcription and GPT-4.1 summarization.
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
    
    def process(self, audio_file: str, meeting_type_id: int = 0) -> Dict[str, Any]:
        """
        Process audio file: transcribe and summarize.
        
        Args:
            audio_file: Path to audio file
            meeting_type_id: Meeting type ID (0=auto-detect, 1-11=specific type)
        
        Returns structured output with:
        - Full transcript with segments
        - Summary
        - Speaker audio clips (~10s per speaker)
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
        
        # Step 4: Align transcript (word-level timestamps for better speaker assignment)
        print("📐 Aligning transcript (word-level timestamps)...")
        align_start = time.time()
        try:
            align_model, align_metadata = whisperx.load_align_model(
                language_code=self.config.LANGUAGE,
                device=self.config.DEVICE
            )
            result = whisperx.align(
                result["segments"],
                align_model,
                align_metadata,
                audio,
                self.config.DEVICE,
                return_char_alignments=False,
            )
            align_time = time.time() - align_start
            print(f"   ⏱️ Alignment: {align_time:.2f}s")
            
            # Clear alignment model
            del align_model
            clear_gpu_memory()
        except Exception as e:
            align_time = 0
            print(f"   ⚠️ Alignment skipped (will use segment-level timestamps): {e}")
        
        # Step 5: Run speaker diarization
        print("👥 Running speaker diarization...")
        diarize_start = time.time()
        try:
            diarize_model = whisperx.diarize.DiarizationPipeline(
                use_auth_token=self.config.HF_TOKEN,
                device=self.config.DEVICE
            )
        except TypeError:
            # Newer pyannote versions use 'token' instead of 'use_auth_token'
            diarize_model = whisperx.diarize.DiarizationPipeline(
                token=self.config.HF_TOKEN,
                device=self.config.DEVICE
            )
        diarize_segments = diarize_model(
            audio,
            min_speakers=self.config.MIN_SPEAKERS,
            max_speakers=self.config.MAX_SPEAKERS,
        )
        diarize_time = time.time() - diarize_start
        print(f"   ⏱️ Diarization: {diarize_time:.2f}s")
        
        # Assign speakers to segments (with word-level alignment = much better accuracy)
        result = whisperx.assign_word_speakers(diarize_segments, result)
        
        # Clear diarization model
        del diarize_model
        clear_gpu_memory()
        
        # Build speaker summary and transcript with generic speaker labels
        segments = sorted(result.get('segments', []), key=lambda x: x['start'])
        speakers_time = {}
        speakers_words = {}
        transcript_lines = []
        
        for segment in segments:
            speaker = format_speaker(segment.get('speaker'))
            # Keep generic labels (คนพูด 1, คนพูด 2, ...)
            segment['speaker'] = speaker
            
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
        
        # Step 4: Extract audio clips per speaker (~10s each)
        print("🔊 Extracting speaker audio clips...")
        clip_start = time.time()
        clip_dir = tempfile.mkdtemp(prefix="speaker_clips_")
        speaker_clips = extract_speaker_clips(
            audio_file=audio_file,
            segments=segments,
            clip_dir=clip_dir,
            target_duration=10.0
        )
        clip_time = time.time() - clip_start
        print(f"   ⏱️ Clip extraction: {clip_time:.2f}s")
        
        # Step 3: Run summary with diarization data
        meeting_info = MEETING_TYPES.get(meeting_type_id, MEETING_TYPES[0])
        print(f"🤖 Running AI Summary ({meeting_info['thai']})...")
        summary_start = time.time()
        summary_text = summarize_with_diarization(
            transcript_with_speakers, 
            speaker_summary,
            meeting_type_id=meeting_type_id
        )
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
                'alignment': align_time,
                'diarization': diarize_time,
                'summarization': summary_time,
                'clip_extraction': clip_time,
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
            'speaker_clips': speaker_clips,
            'clip_dir': clip_dir,
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
        print(f"   - Alignment: {pt.get('alignment', 0):.2f}s")
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
        print("🤖 AI SUMMARY (GPT-4.1)")
        print("=" * 60)
        print(output['summary'])
        
        print("\n" + "=" * 60)
        print("✅ Pipeline completed successfully!")
        print("=" * 60)
