from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import torch
from transformers import VitsModel, AutoTokenizer
import base64
import io
import numpy as np

router = APIRouter()

# Load model and tokenizer
model = VitsModel.from_pretrained("facebook/mms-tts-vie")
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-vie")

class TTSRequest(BaseModel):
    text: str

@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    try:
        # Tokenize text
        inputs = tokenizer(request.text, return_tensors="pt")
        
        # Generate speech
        with torch.no_grad():
            output = model(**inputs).waveform
            
        # Convert to numpy array and then to bytes
        audio_data = output.numpy().tobytes()
        
        # Convert to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return {
            "audio": audio_base64,
            "sample_rate": model.config.sampling_rate
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 