from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlmodel import Session, select
from typing import List, Optional
import uuid
import shutil
import os
import datetime
from pydantic import BaseModel
from ..database import get_session
from ..models import User, Session as DbSession, SessionStep, StepType, StepStatus, SessionStatus, Resume, ContextData
from ..services.ai import ai_service
from ..services.scraper import scraper_service
from ..services.parser import parser_service
from .auth import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("/")
@router.post("/")
async def create_session(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Use authenticated user
    user = current_user
        
    db_session = DbSession(
        user_id=user.id, 
        job_title="Software Engineer", # Default, will be updated later
        company_name="Pending", # Default, will be updated later
        jd_content="Standard JD", # Default
        role_level="mid", # Default
        duration_minutes=15 # Default
    )
    session.add(db_session)
    session.commit()
    session.refresh(db_session)
    
    # Initialize steps - ALL PENDING initially
    steps = [
        SessionStep(session_id=db_session.id, step_type=StepType.SCREENING, status=StepStatus.PENDING),
        SessionStep(session_id=db_session.id, step_type=StepType.BEHAVIORAL),
        SessionStep(session_id=db_session.id, step_type=StepType.TECHNICAL),
        SessionStep(session_id=db_session.id, step_type=StepType.SYSTEM_DESIGN),
    ]
    for step in steps:
        session.add(step)
    session.commit()
    
    print(f"Created session: {db_session}")
    return {"id": str(db_session.id)}

@router.get("/", response_model=List[DbSession])
async def get_sessions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    sessions = session.exec(select(DbSession).where(DbSession.user_id == current_user.id)).all()
    return sessions

@router.get("/{session_id}", response_model=DbSession)
async def get_session_by_id(session_id: uuid.UUID, session: Session = Depends(get_session)):
    db_session = session.get(DbSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return db_session

class SessionUpdate(BaseModel):
    role_level: Optional[str] = None
    duration_minutes: Optional[int] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None

@router.patch("/{session_id}")
async def update_session(
    session_id: uuid.UUID,
    update_data: SessionUpdate,
    session: Session = Depends(get_session)
):
    db_session = session.get(DbSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if update_data.role_level:
        db_session.role_level = update_data.role_level
    if update_data.duration_minutes:
        db_session.duration_minutes = update_data.duration_minutes
    if update_data.company_name:
        db_session.company_name = update_data.company_name
    if update_data.job_title:
        db_session.job_title = update_data.job_title
        
    session.add(db_session)
    session.commit()
    session.refresh(db_session)
    return db_session

@router.post("/{session_id}/resume")
async def upload_resume(
    session_id: uuid.UUID,
    resume: UploadFile = File(...),
    session: Session = Depends(get_session)
):
    db_session = session.get(DbSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")

    upload_dir = "backend/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_location = f"{upload_dir}/{db_session.id}_{resume.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(resume.file, file_object)
        
    # Create Resume record
    parsed_text = parser_service.parse_resume(file_location)
    
    db_resume = Resume(user_id=db_session.user_id, file_path=file_location, parsed_content=parsed_text)
    session.add(db_resume)
    session.commit()
    
    return {"status": "uploaded", "filename": resume.filename}

@router.post("/{session_id}/start")
async def start_session(
    session_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    db_session = session.get(DbSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Scrape Company Info if not already done (and if company name is valid)
    # We check if context data already exists to avoid re-scraping if user restarts?
    # Or just scrape if it's "Pending" or changed. 
    # Let's assume we scrape if context is empty or we just want to ensure we have it.
    # Simple check: if no context data, scrape.
    if not db_session.context_data and db_session.company_name and db_session.company_name != "Pending":
        company_info = scraper_service.search_company(db_session.company_name)
        if company_info:
            context = ContextData(session_id=db_session.id, source="duckduckgo", content=company_info)
            session.add(context)
            session.commit()

    # Find first step (Screening)
    steps = session.exec(select(SessionStep).where(SessionStep.session_id == session_id)).all()
    first_step = next((s for s in steps if s.step_type == StepType.SCREENING), None)
    
    if first_step and first_step.status == StepStatus.PENDING:
        first_step.status = StepStatus.IN_PROGRESS
        first_step.started_at = datetime.datetime.utcnow()
        session.add(first_step)
        
        # Initial greeting
        # Construct context
        context_str = f"Job Title: {db_session.job_title}\nCompany: {db_session.company_name}\nJD: {db_session.jd_content}\n"
        # Add external context
        for ctx in db_session.context_data:
            context_str += f"\nSource ({ctx.source}): {ctx.content[:500]}"
        # Add Resume
        latest_resume = session.exec(select(Resume).where(Resume.user_id == db_session.user_id).order_by(Resume.id.desc())).first()
        if latest_resume and latest_resume.parsed_content:
            context_str += f"\n\nCandidate Resume:\n{latest_resume.parsed_content[:2000]}"
            
        ai_response = ai_service.generate_response(context_str, [], "Hello", step_type=first_step.step_type, role_level=db_session.role_level)
        
        # Parse Roadmap if present (Duplicate logic from interact_step - refactor later?)
        import re
        roadmap_match = re.search(r"<roadmap>(.*?)</roadmap>", ai_response, re.DOTALL)
        if roadmap_match:
            roadmap_str = roadmap_match.group(1)
            first_step.roadmap = [item.strip() for item in roadmap_str.split(",")]
            ai_response = ai_response.replace(f"<roadmap>{roadmap_str}</roadmap>", f"**Roadmap:** {roadmap_str}\n")

        log = [{"role": "assistant", "content": ai_response, "id": str(uuid.uuid4())}]
        first_step.interaction_log = log
        session.add(first_step)
        
    db_session.status = SessionStatus.IN_PROGRESS # Or READY
    session.add(db_session)
    session.commit()
    
    return {"status": "started"}

@router.get("/{session_id}/details", response_model=DbSession)
async def get_session_details(session_id: uuid.UUID, session: Session = Depends(get_session)):
    db_session = session.get(DbSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return db_session

@router.get("/{session_id}/steps", response_model=List[SessionStep])
async def get_session_steps(session_id: uuid.UUID, session: Session = Depends(get_session)):
    steps = session.exec(select(SessionStep).where(SessionStep.session_id == session_id)).all()
    return steps

class InteractionRequest(BaseModel):
    message: str

@router.post("/{session_id}/steps/{step_id}/interact")
async def interact_step(
    session_id: uuid.UUID,
    step_id: uuid.UUID,
    request: InteractionRequest,
    session: Session = Depends(get_session)
):
    message = request.message
    step = session.get(SessionStep, step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    
    # Update interaction log
    current_log = step.interaction_log or []
    if isinstance(current_log, dict):
        log = list(current_log.values())
    elif isinstance(current_log, list):
        log = list(current_log) # Copy to avoid mutation issues if it's an ORM object
    else:
        log = []
    
    # User message
    log.append({"role": "user", "content": message, "id": str(uuid.uuid4())})
    
    # Check for time limit
    db_session = session.get(DbSession, session_id)
    
    # Use step.started_at if available, fallback to session.created_at (legacy/fallback)
    start_time = step.started_at or db_session.created_at
    duration = datetime.timedelta(minutes=db_session.duration_minutes)
    
    if datetime.datetime.utcnow() > start_time + duration:
        ai_response = "The interview time for this step has ended. Please proceed to the next step."
        log.append({"role": "assistant", "content": ai_response, "id": str(uuid.uuid4())})
        step.interaction_log = log
        # Do not auto-complete, let user decide to move on or review
        session.add(step)
        session.commit()
        session.refresh(step)
        return {"response": ai_response}

    # Calculate remaining time
    remaining_minutes = None
    if duration:
        elapsed = datetime.datetime.utcnow() - start_time
        remaining = duration - elapsed
        remaining_minutes = int(remaining.total_seconds() / 60)
        if remaining_minutes < 0: remaining_minutes = 0

    # Call AI Service
    # Construct context from session data (JD, Company, etc.)
    context_str = f"Job Title: {db_session.job_title}\nCompany: {db_session.company_name}\nJD: {db_session.jd_content}\n"
    
    # Add external context (Company Info)
    for ctx in db_session.context_data:
        context_str += f"\nSource ({ctx.source}): {ctx.content[:500]}"
        
    # Add Resume Context
    latest_resume = session.exec(select(Resume).where(Resume.user_id == db_session.user_id).order_by(Resume.id.desc())).first()
    if latest_resume and latest_resume.parsed_content:
        context_str += f"\n\nCandidate Resume:\n{latest_resume.parsed_content[:2000]}"
        
    # Construct history
    history = []
    for entry in log:
        if entry["role"] != "system": 
            history.append(f"{entry['role']}: {entry['content']}")
            
    ai_response = ai_service.generate_response(
        context_str, 
        history, 
        message, 
        step_type=step.step_type, 
        role_level=db_session.role_level,
        roadmap=step.roadmap,
        remaining_time=remaining_minutes
    )
    
    # Parse Roadmap if present
    import re
    roadmap_match = re.search(r"<roadmap>(.*?)</roadmap>", ai_response, re.DOTALL)
    if roadmap_match:
        roadmap_str = roadmap_match.group(1)
        step.roadmap = [item.strip() for item in roadmap_str.split(",")]
        # Optional: Remove the tag from the response shown to user? 
        # User might want to see it. Let's keep it but maybe format it nicely in frontend later.
        # For now, we strip the tags for cleaner text if we wanted, but let's leave it.
        # Actually, let's strip the tags so it doesn't look like raw XML.
        ai_response = ai_response.replace(f"<roadmap>{roadmap_str}</roadmap>", f"**Roadmap:** {roadmap_str}\n")
    
    # AI message
    log.append({"role": "assistant", "content": ai_response, "id": str(uuid.uuid4())})
    
    step.interaction_log = log
    step.status = StepStatus.IN_PROGRESS
    session.add(step)
    session.commit()
    session.refresh(step)
    
    return {"response": ai_response}

@router.post("/{session_id}/steps/{step_id}/complete")
async def complete_step(
    session_id: uuid.UUID,
    step_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    step = session.get(SessionStep, step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
        
    # Generate evaluation
    # Construct context from session data
    db_session = step.session
    context_str = f"Job Title: {db_session.job_title}\nCompany: {db_session.company_name}\nJD: {db_session.jd_content}\n"
    
    # Add external context (Company Info)
    if db_session.context_data:
        for ctx in db_session.context_data:
            context_str += f"\nSource ({ctx.source}): {ctx.content[:500]}"
    
    # Reconstruct history for evaluation
    history = []
    current_log = step.interaction_log or []
    if isinstance(current_log, dict):
        log_list = list(current_log.values())
    elif isinstance(current_log, list):
        log_list = list(current_log)
    else:
        log_list = []
        
    for entry in log_list:
        if entry["role"] != "system":
            history.append(f"{entry['role']}: {entry['content']}")
            
    feedback = ai_service.evaluate_step(context_str, history, step.step_type)
    
    step.status = StepStatus.COMPLETED
    step.feedback = feedback
    session.add(step)
    
    # Find next step and activate it
    all_steps = session.exec(select(SessionStep).where(SessionStep.session_id == session_id)).all()
    
    # Simple logic: Find first PENDING step
    next_step = next((s for s in all_steps if s.status == StepStatus.PENDING), None)
    if next_step:
        next_step.status = StepStatus.IN_PROGRESS
        next_step.started_at = datetime.datetime.utcnow()
        session.add(next_step)
        
    session.commit()
    return {"status": "success", "feedback": feedback}

    db_session.status = "completed"
    session.add(db_session)
    session.commit()
    return {"status": "success"}

@router.post("/{session_id}/research")
async def research_session(
    session_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    db_session = session.get(DbSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if not db_session.company_name or db_session.company_name == "Pending":
         raise HTTPException(status_code=400, detail="Company name is required for research")
         
    if not db_session.job_title:
         raise HTTPException(status_code=400, detail="Job title is required for research")

    # Trigger Celery Task
    from ..tasks import perform_interview_research, perform_context_research
    perform_interview_research.delay(str(session_id), db_session.company_name, db_session.job_title)
    perform_context_research.delay(str(session_id), db_session.company_name, db_session.job_title)
    
    db_session.research_status = "pending"
    session.add(db_session)
    session.commit()
    
    return {"status": "research_started"}

@router.get("/{session_id}/research/status")
async def get_research_status(
    session_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    db_session = session.get(DbSession, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {
        "status": db_session.research_status,
        "data": db_session.research_data
    }

