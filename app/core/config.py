import os

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
    
    # VAD options (tuned for meeting audio with multiple speakers)
    VAD_ONSET = 0.500       # Speech start threshold (higher = less false positives)
    VAD_OFFSET = 0.363      # Speech end threshold
    MIN_DURATION_ON = 0.10  # Min speech duration (filter out clicks/noise)
    MIN_DURATION_OFF = 0.10 # Min silence to split segments (avoid over-splitting)
    
    # Speaker diarization settings
    MIN_SPEAKERS = None     # None = auto-detect (let pyannote decide)
    MAX_SPEAKERS = None     # None = auto-detect
    
    # HuggingFace token for diarization
    HF_TOKEN = os.environ.get("HF_TOKEN", "")
