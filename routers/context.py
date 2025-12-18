from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import uuid
from ..database import get_session
from ..models import Session as DbSession, ContextData
from ..services.scraper import scraper_service

router = APIRouter(prefix="/context", tags=["context"])

@router.post("/{session_id}/add-url")
async def add_url_context(
    session_id: uuid.UUID,
    url: str,
    session: Session = Depends(get_session)
):
    db_session = session.get(DbSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    content = scraper_service.scrape_url(url)
    if not content:
        raise HTTPException(status_code=400, detail="Failed to scrape URL")
        
    context_data = ContextData(session_id=session_id, source=url, content=content[:5000]) # Limit content size
    session.add(context_data)
    session.commit()
    session.refresh(context_data)
    
    return context_data

@router.post("/{session_id}/add-reddit")
async def add_reddit_context(
    session_id: uuid.UUID,
    query: str,
    session: Session = Depends(get_session)
):
    db_session = session.get(DbSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    content = scraper_service.scrape_reddit(query)
    
    context_data = ContextData(session_id=session_id, source=f"Reddit: {query}", content=content)
    session.add(context_data)
    session.commit()
    session.refresh(context_data)
    
    return context_data
