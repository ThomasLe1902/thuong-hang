from fastapi import APIRouter, File, UploadFile, Form, Response
from typing import Optional
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from src.config.direct_chain import image_gen_prompt
from src.config.llm import get_llm
import os

load_dotenv()

router = APIRouter(prefix="/image-generation", tags=["Image Generation"])


@router.post("/generate-image")
async def gen_image(
    prompt: str = Form(...),
    api_key: str = Form(default=os.getenv("GOOGLE_API_KEY")),
    image: Optional[UploadFile] = File(None),
):
    try:
        client = genai.Client(api_key=api_key)
        contents = prompt
        if image:
            img_bytes = await image.read()
            img_pil = Image.open(BytesIO(img_bytes))
            contents = [prompt, img_pil]
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=contents,
            config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
        )

        for part in response.candidates[0].content.parts:
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                img_bytes = part.inline_data.data
                return Response(content=img_bytes, media_type="image/png")
            elif getattr(part, "text", None) is not None:
                # Return plain text directly
                return Response(content=part.text, media_type="text/plain")

        # No response found
        return Response(content="No content generated.", media_type="text/plain")
    except Exception as e:
        return Response(content=str(e), media_type="text/plain", status_code=500)


@router.post("/generate-image-prompt")
async def generate_image_prompt(
    prompt: str = Form(...),
    model: str = Form(default="gemini-2.5-flash-preview-05-20"),
    api_key: str = Form(...),
):
    try:
        chain = image_gen_prompt | get_llm(model, api_key)
        response = chain.invoke({"input": prompt})
        return Response(content=response.content, media_type="text/plain")
    except Exception as e:
        return Response(content=str(e), media_type="text/plain", status_code=500)
