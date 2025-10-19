# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel
# from transformers import VitsModel, AutoTokenizer
# import torch
# import os
# import uuid
# from fastapi.responses import FileResponse
# import soundfile as sf
# import numpy as np
# from src.utils.logger import logger
# from google import genai
# from google.genai import types
# import wave
# from typing import Literal

# router = APIRouter()


# class TTSRequest(BaseModel):
#     text: str


# class GeminiTTSRequest(BaseModel):
#     text: str
#     voice_name: str = "Kore"


# # Initialize model and tokenizer globally
# try:
#     logger.info("Loading TTS model and tokenizer...")
#     model = VitsModel.from_pretrained("facebook/mms-tts-vie")
#     tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-vie")
#     logger.info("TTS model and tokenizer loaded successfully")
# except Exception as e:
#     logger.error(f"Failed to load TTS model: {str(e)}")
#     raise

# # Initialize Google Gemini client
# try:
#     logger.info("Initializing Google Gemini client...")
#     gemini_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
#     logger.info("Google Gemini client initialized successfully")
# except Exception as e:
#     logger.error(f"Failed to initialize Google Gemini client: {str(e)}")
#     raise


# def save_wave_file(
#     filename: str,
#     pcm: bytes,
#     channels: int = 1,
#     rate: int = 24000,
#     sample_width: int = 2,
# ):
#     """Save PCM data to a WAV file."""
#     with wave.open(filename, "wb") as wf:
#         wf.setnchannels(channels)
#         wf.setsampwidth(sample_width)
#         wf.setframerate(rate)
#         wf.writeframes(pcm)


# @router.post("/tts/huggingface")
# async def huggingface_tts(request: TTSRequest):
#     try:
#         logger.info(
#             f"Processing HuggingFace TTS request for text: {request.text[:50]}..."
#         )

#         # Tokenize input
#         inputs = tokenizer(request.text, return_tensors="pt")
#         logger.info("Text tokenized successfully")

#         # Generate audio
#         with torch.no_grad():
#             output = model(**inputs).waveform
#         logger.info("Audio generated successfully")

#         # Convert tensor to numpy array
#         audio_numpy = output.squeeze().cpu().numpy()

#         # Create audio directory if it doesn't exist
#         audio_dir = os.path.join(os.getcwd(), "audio_files")
#         os.makedirs(audio_dir, exist_ok=True)

#         # Generate unique filename
#         audio_filename = f"huggingface_{uuid.uuid4()}.wav"
#         audio_path = os.path.join(audio_dir, audio_filename)

#         # Save audio file using soundfile
#         sf.write(audio_path, audio_numpy, model.config.sampling_rate)
#         logger.info(f"Audio saved to {audio_path}")

#         # Return audio file
#         return FileResponse(audio_path, media_type="audio/wav", filename=audio_filename)

#     except Exception as e:
#         logger.error(f"Error in huggingface_tts: {str(e)}")
#         raise HTTPException(
#             status_code=500, detail=f"Failed to generate speech: {str(e)}"
#         )


# @router.post("/tts/gemini")
# def gemini_tts(request: GeminiTTSRequest):
#     try:
#         logger.info(f"Processing Gemini TTS request for text: {request.text[:50]}...")

#         response = gemini_client.models.generate_content(
#             model="gemini-2.5-flash-preview-tts",
#             contents=request.text,
#             config=types.GenerateContentConfig(
#                 response_modalities=["AUDIO"],
#                 speech_config=types.SpeechConfig(
#                     voice_config=types.VoiceConfig(
#                         prebuilt_voice_config=types.PrebuiltVoiceConfig(
#                             voice_name=request.voice_name,
#                         )
#                     )
#                 ),
#             ),
#         )

#         data = response.candidates[0].content.parts[0].inline_data.data

#         # Create audio directory if it doesn't exist
#         audio_dir = os.path.join(os.getcwd(), "audio_files")
#         os.makedirs(audio_dir, exist_ok=True)

#         # Generate unique filename
#         audio_filename = f"gemini_{uuid.uuid4()}.wav"
#         audio_path = os.path.join(audio_dir, audio_filename)

#         # Save audio file
#         save_wave_file(audio_path, data)
#         logger.info(f"Audio saved to {audio_path}")

#         # Return audio file
#         return FileResponse(audio_path, media_type="audio/wav", filename=audio_filename)

#     except Exception as e:
#         logger.error(f"Error in gemini_tts: {str(e)}")
#         raise HTTPException(
#             status_code=500, detail=f"Failed to generate speech: {str(e)}"
#         )
