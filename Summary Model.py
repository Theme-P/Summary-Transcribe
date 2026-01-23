import requests
import json 
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI API configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


def summarize_transcription(transcription_text: str, language: str = "Thai") -> str:
    """
    Summarize transcription text from WhisperX using GPT-4o.
    
    Args:
        transcription_text: The transcription text to summarize
        language: The language for the summary output (default: Thai)
    
    Returns:
        Summarized text
    """
    if not OPENAI_API_KEY:
        return "Error: OPENAI_API_KEY not found in environment variables"
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "system",
                "content": f"""คุณคือผู้ช่วยสรุปใจความสำคัญ 
กรุณาสรุปเนื้อหาที่ได้รับมาอย่างกระชับและครอบคลุมประเด็นสำคัญ
ตอบเป็นภาษา{language}
รูปแบบการสรุป:
1. หัวข้อหลัก/ประเด็นสำคัญ
2. รายละเอียดที่สำคัญ
3. สรุปใจความโดยรวม"""
            },
            {
                "role": "user",
                "content": f"กรุณาสรุปใจความสำคัญจากข้อความต่อไปนี้:\n\n{transcription_text}"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
        
    except requests.exceptions.RequestException as e:
        return f"Error calling OpenAI API: {str(e)}"
    except (KeyError, IndexError) as e:
        return f"Error parsing response: {str(e)}"


def summarize_from_whisperx_result(result: dict) -> str:
    """
    Summarize from WhisperX result dictionary.
    
    Args:
        result: WhisperX result dictionary containing 'segments'
    
    Returns:
        Summarized text
    """
    # Extract text from all segments
    if "segments" in result:
        full_text = " ".join([seg.get("text", "") for seg in result["segments"]])
    else:
        full_text = str(result)
    
    return summarize_transcription(full_text)


# Example usage
if __name__ == "__main__":
    # Test with sample text
    sample_text = """
    นี่คือตัวอย่างข้อความที่ได้จาก WhisperX
    สามารถนำมาสรุปใจความสำคัญได้
    """
    
    print("Testing GPT-4o Summarization...")
    summary = summarize_transcription(sample_text)
    print(f"\nSummary:\n{summary}")
