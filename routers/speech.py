from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from ..services.tts import get_tts_service

router = APIRouter(
    prefix="/speech",
    tags=["speech"],
    responses={404: {"description": "Not found"}},
)

@router.get("/generate")
async def generate_speech(text: str = Query(...), tier: Optional[str] = Query("free")):
    try:
        tts_service = get_tts_service(tier)
        audio_generator = tts_service.generate_speech(text)
        return StreamingResponse(audio_generator, media_type="audio/mpeg")
    except Exception as e:
        error_msg = str(e)
        if "OPENAI_API_KEY" in error_msg or "DefaultCredentialsError" in error_msg:
             raise HTTPException(status_code=400, detail=f"Configuration Error: {error_msg}")
        raise HTTPException(status_code=500, detail=str(e))
