from fastapi import APIRouter, Depends
import uuid
from ..core.models import ContextData
from ..services.session import SessionService
from .sessions import get_session_service

router = APIRouter(prefix="/context", tags=["context"])

@router.post("/{session_id}/add-url")
async def add_url_context(
    session_id: uuid.UUID,
    url: str,
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.add_url_context(session_id, url)

@router.post("/{session_id}/add-reddit")
async def add_reddit_context(
    session_id: uuid.UUID,
    query: str,
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.add_reddit_context(session_id, query)
