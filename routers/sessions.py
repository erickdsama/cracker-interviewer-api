from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel import Session
from typing import List, Optional
import uuid
from pydantic import BaseModel

from ..core.database import get_session
from ..core.models import User, Session as DbSession, SessionStep
from .auth import get_current_user
from ..repositories.session import SessionRepository
from ..services.session import SessionService

router = APIRouter(prefix="/sessions", tags=["sessions"])

def get_session_repository(session: Session = Depends(get_session)) -> SessionRepository:
    return SessionRepository(session)

def get_session_service(session_repo: SessionRepository = Depends(get_session_repository)) -> SessionService:
    return SessionService(session_repo)

class SessionUpdate(BaseModel):
    role_level: Optional[str] = None
    duration_minutes: Optional[int] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None

class InteractionRequest(BaseModel):
    message: str

@router.post("")
async def create_session(
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service)
):
    db_session = session_service.create_session(current_user)
    return {"id": str(db_session.id)}

@router.get("", response_model=List[DbSession])
async def get_sessions(
    current_user: User = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.get_user_sessions(current_user.id)

@router.get("/{session_id}", response_model=DbSession)
async def get_session_by_id(
    session_id: uuid.UUID, 
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.get_session(session_id)

@router.patch("/{session_id}")
async def update_session(
    session_id: uuid.UUID,
    update_data: SessionUpdate,
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.update_session(session_id, update_data.dict(exclude_unset=True))

@router.post("/{session_id}/resume")
async def upload_resume(
    session_id: uuid.UUID,
    resume: UploadFile = File(...),
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.upload_resume(session_id, resume)

@router.post("/{session_id}/start")
async def start_session(
    session_id: uuid.UUID,
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.start_session(session_id)

@router.get("/{session_id}/details", response_model=DbSession)
async def get_session_details(
    session_id: uuid.UUID, 
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.get_session(session_id)

@router.get("/{session_id}/steps", response_model=List[SessionStep])
async def get_session_steps(
    session_id: uuid.UUID, 
    session_service: SessionService = Depends(get_session_service)
):
    session = session_service.get_session(session_id)
    return session.steps

@router.post("/{session_id}/steps/{step_id}/interact")
async def interact_step(
    session_id: uuid.UUID,
    step_id: uuid.UUID,
    request: InteractionRequest,
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.interact_step(session_id, step_id, request.message)

@router.post("/{session_id}/steps/{step_id}/complete")
async def complete_step(
    session_id: uuid.UUID,
    step_id: uuid.UUID,
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.complete_step(session_id, step_id)

@router.post("/{session_id}/research")
async def research_session(
    session_id: uuid.UUID,
    session_service: SessionService = Depends(get_session_service)
):
    return session_service.research_session(session_id)

@router.get("/{session_id}/research/status")
async def get_research_status(
    session_id: uuid.UUID,
    session_service: SessionService = Depends(get_session_service)
):
    session = session_service.get_session(session_id)
    return {
        "status": session.research_status,
        "data": session.research_data
    }
