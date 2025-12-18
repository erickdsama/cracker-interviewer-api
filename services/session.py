import uuid
import datetime
import shutil
import os
from typing import List, Optional, Dict
from fastapi import UploadFile, HTTPException

from ..core.models import Session as DbSession, SessionStep, StepType, StepStatus, SessionStatus, Resume, ContextData, User
from ..repositories.session import SessionRepository
from ..services.ai import ai_service
from ..services.scraper import scraper_service
from ..services.parser import parser_service
from ..services.storage import storage_service
from ..tasks import perform_interview_research, perform_context_research

class SessionService:
    def __init__(self, session_repository: SessionRepository):
        self.session_repository = session_repository

    def create_session(self, user: User) -> DbSession:
        db_session = DbSession(
            user_id=user.id, 
            job_title="Software Engineer", # Default
            company_name="Pending", # Default
            jd_content="Standard JD", # Default
            role_level="mid", # Default
            duration_minutes=15 # Default
        )
        self.session_repository.create(db_session)
        
        # Initialize steps
        steps = [
            SessionStep(session_id=db_session.id, step_type=StepType.SCREENING, status=StepStatus.PENDING),
            SessionStep(session_id=db_session.id, step_type=StepType.BEHAVIORAL),
            SessionStep(session_id=db_session.id, step_type=StepType.TECHNICAL),
            SessionStep(session_id=db_session.id, step_type=StepType.SYSTEM_DESIGN),
        ]
        for step in steps:
            self.session_repository.session.add(step)
        self.session_repository.session.commit()
        
        return db_session

    def get_user_sessions(self, user_id: uuid.UUID) -> List[DbSession]:
        return self.session_repository.get_by_user_id(user_id)

    def get_session(self, session_id: uuid.UUID) -> DbSession:
        session = self.session_repository.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    def update_session(self, session_id: uuid.UUID, update_data: dict) -> DbSession:
        session = self.session_repository.update(session_id, update_data)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session

    def upload_resume(self, session_id: uuid.UUID, resume_file: UploadFile) -> Dict:
        db_session = self.get_session(session_id)
        
        # 1. Upload File (S3 or Local)
        destination_path = f"{db_session.id}_{resume_file.filename}"
        file_location = storage_service.upload_file(resume_file, destination_path)
        
        # 2. Parse Resume
        # Reset file pointer to read for parsing
        resume_file.file.seek(0)
        parsed_text = parser_service.parse_resume(resume_file.file, filename=resume_file.filename)
        
        db_resume = Resume(user_id=db_session.user_id, file_path=file_location, parsed_content=parsed_text)
        self.session_repository.session.add(db_resume)
        self.session_repository.session.commit()
        
        return {"status": "uploaded", "filename": resume_file.filename, "location": file_location}

    def start_session(self, session_id: uuid.UUID) -> Dict:
        db_session = self.get_session(session_id)
        
        # Scrape Company Info
        if not db_session.context_data and db_session.company_name and db_session.company_name != "Pending":
            company_info = scraper_service.search_company(db_session.company_name)
            if company_info:
                context = ContextData(session_id=db_session.id, source="duckduckgo", content=company_info)
                self.session_repository.session.add(context)
                self.session_repository.session.commit()

        # Find first step
        steps = db_session.steps
        first_step = next((s for s in steps if s.step_type == StepType.SCREENING), None)
        
        if first_step and first_step.status == StepStatus.PENDING:
            first_step.status = StepStatus.IN_PROGRESS
            first_step.started_at = datetime.datetime.utcnow()
            self.session_repository.session.add(first_step)
            
            # Initial greeting
            context_str = self._build_context_string(db_session)
            
            ai_response = ai_service.generate_response(context_str, [], "Hello", step_type=first_step.step_type, role_level=db_session.role_level)
            
            # Parse Roadmap
            ai_response = self._process_roadmap(ai_response, first_step)

            log = [{"role": "assistant", "content": ai_response, "id": str(uuid.uuid4())}]
            first_step.interaction_log = log
            self.session_repository.session.add(first_step)
            
        db_session.status = SessionStatus.IN_PROGRESS
        self.session_repository.session.add(db_session)
        self.session_repository.session.commit()
        
        return {"status": "started"}

    def interact_step(self, session_id: uuid.UUID, step_id: uuid.UUID, message: str) -> Dict:
        # Note: We need to fetch step directly or via session
        # For simplicity, we use the session repository's session to query step
        step = self.session_repository.session.get(SessionStep, step_id)
        if not step:
            raise HTTPException(status_code=404, detail="Step not found")
            
        # Update log
        current_log = step.interaction_log or []
        if isinstance(current_log, dict): log = list(current_log.values())
        elif isinstance(current_log, list): log = list(current_log)
        else: log = []
        
        log.append({"role": "user", "content": message, "id": str(uuid.uuid4())})
        
        db_session = self.get_session(session_id)
        
        # Check time limit
        start_time = step.started_at or db_session.created_at
        duration = datetime.timedelta(minutes=db_session.duration_minutes)
        
        if datetime.datetime.utcnow() > start_time + duration:
            ai_response = "The interview time for this step has ended. Please proceed to the next step."
            log.append({"role": "assistant", "content": ai_response, "id": str(uuid.uuid4())})
            step.interaction_log = log
            self.session_repository.session.add(step)
            self.session_repository.session.commit()
            return {"response": ai_response}

        # Calculate remaining time
        remaining_minutes = None
        if duration:
            elapsed = datetime.datetime.utcnow() - start_time
            remaining = duration - elapsed
            remaining_minutes = int(remaining.total_seconds() / 60)
            if remaining_minutes < 0: remaining_minutes = 0

        # Build Context
        context_str = self._build_context_string(db_session)
        
        # Build History
        history = [f"{entry['role']}: {entry['content']}" for entry in log if entry["role"] != "system"]
            
        ai_response = ai_service.generate_response(
            context_str, 
            history, 
            message, 
            step_type=step.step_type, 
            role_level=db_session.role_level,
            roadmap=step.roadmap,
            remaining_time=remaining_minutes
        )
        
        # Parse Roadmap
        ai_response = self._process_roadmap(ai_response, step)
        
        log.append({"role": "assistant", "content": ai_response, "id": str(uuid.uuid4())})
        
        step.interaction_log = log
        step.status = StepStatus.IN_PROGRESS
        self.session_repository.session.add(step)
        self.session_repository.session.commit()
        
        return {"response": ai_response}

    def complete_step(self, session_id: uuid.UUID, step_id: uuid.UUID) -> Dict:
        step = self.session_repository.session.get(SessionStep, step_id)
        if not step:
            raise HTTPException(status_code=404, detail="Step not found")
            
        db_session = step.session
        context_str = self._build_context_string(db_session)
        
        # Reconstruct history
        history = []
        current_log = step.interaction_log or []
        if isinstance(current_log, dict): log_list = list(current_log.values())
        elif isinstance(current_log, list): log_list = list(current_log)
        else: log_list = []
        
        for entry in log_list:
            if entry["role"] != "system":
                history.append(f"{entry['role']}: {entry['content']}")
                
        # Agent 1: Bar Raiser (Standard Evaluation)
        feedback = ai_service.evaluate_step(context_str, history, step.step_type)
        
        # Agent 2: Hiring Manager (Fresh Considerations, aligned with Bar Raiser)
        hm_feedback = ai_service.get_hiring_manager_feedback(context_str, history, bar_raiser_feedback=feedback)
        
        # Combine feedback
        combined_feedback = f"{feedback}\n\n---\n\n{hm_feedback}"
        
        step.status = StepStatus.COMPLETED
        step.feedback = combined_feedback
        self.session_repository.session.add(step)
        
        # Activate next step
        all_steps = db_session.steps
        next_step = next((s for s in all_steps if s.status == StepStatus.PENDING), None)
        if next_step:
            next_step.status = StepStatus.IN_PROGRESS
            next_step.started_at = datetime.datetime.utcnow()
            self.session_repository.session.add(next_step)
            
        self.session_repository.session.commit()
        return {"status": "success", "feedback": feedback}

    def research_session(self, session_id: uuid.UUID) -> Dict:
        db_session = self.get_session(session_id)
        
        if not db_session.company_name or db_session.company_name == "Pending":
             raise HTTPException(status_code=400, detail="Company name is required for research")
        if not db_session.job_title:
             raise HTTPException(status_code=400, detail="Job title is required for research")

        perform_interview_research.delay(str(session_id), db_session.company_name, db_session.job_title)
        perform_context_research.delay(str(session_id), db_session.company_name, db_session.job_title)
        
        db_session.research_status = "pending"
        self.session_repository.session.add(db_session)
        self.session_repository.session.commit()
        
        return {"status": "research_started"}

    def add_url_context(self, session_id: uuid.UUID, url: str) -> ContextData:
        db_session = self.get_session(session_id)
        
        content = scraper_service.scrape_url(url)
        if not content:
            raise HTTPException(status_code=400, detail="Failed to scrape URL")
            
        context_data = ContextData(session_id=session_id, source=url, content=content[:5000])
        self.session_repository.session.add(context_data)
        self.session_repository.session.commit()
        self.session_repository.session.refresh(context_data)
        
        return context_data

    def add_reddit_context(self, session_id: uuid.UUID, query: str) -> ContextData:
        db_session = self.get_session(session_id)
        
        content = scraper_service.scrape_reddit(query)
            
        context_data = ContextData(session_id=session_id, source=f"Reddit: {query}", content=content)
        self.session_repository.session.add(context_data)
        self.session_repository.session.commit()
        self.session_repository.session.refresh(context_data)
        
        return context_data


    def _build_context_string(self, db_session: DbSession) -> str:
        context_str = f"Job Title: {db_session.job_title}\nCompany: {db_session.company_name}\nJD: {db_session.jd_content}\n"
        for ctx in db_session.context_data:
            context_str += f"\nSource ({ctx.source}): {ctx.content[:500]}"
            
        # Add Resume (Need to query resumes via user)
        # For simplicity, we can query Resume directly here or add a method to Repo
        # Let's use the relationship if loaded, or query
        # Since Resume is on User, and Session has User...
        # But we might not have User loaded.
        # Let's do a direct query for now using the session from repo
        from sqlmodel import select
        latest_resume = self.session_repository.session.exec(
            select(Resume).where(Resume.user_id == db_session.user_id).order_by(Resume.id.desc())
        ).first()
        
        if latest_resume and latest_resume.parsed_content:
            context_str += f"\n\nCandidate Resume:\n{latest_resume.parsed_content[:2000]}"
            
        return context_str

    def _process_roadmap(self, ai_response: str, step: SessionStep) -> str:
        import re
        roadmap_match = re.search(r"<roadmap>(.*?)</roadmap>", ai_response, re.DOTALL)
        if roadmap_match:
            roadmap_str = roadmap_match.group(1)
            step.roadmap = [item.strip() for item in roadmap_str.split(",")]
            ai_response = ai_response.replace(f"<roadmap>{roadmap_str}</roadmap>", f"**Roadmap:** {roadmap_str}\n")
        return ai_response

    def close_session(self, session_id: uuid.UUID) -> Dict:
        db_session = self.get_session(session_id)
        db_session.status = SessionStatus.COMPLETED
        self.session_repository.session.add(db_session)
        self.session_repository.session.commit()
        return {"status": "closed"}
