import os
import json
from google import genai
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch
from .celery_worker import celery_app
from .core.database import get_session
from .core.models import Session, SessionStep, StepType, StepStatus
from sqlmodel import select, Session as DbSession
from typing import List, Dict
from .core.logger import get_logger

logger = get_logger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

@celery_app.task
def perform_interview_research(session_id: str, company: str, role: str):
    """
    Background task to research interview process using Gemini with Google Search Grounding.
    """
    logger.info(f"Starting research for {company} - {role} (Session {session_id})")
    
    # 1. Update status to processing
    from .core.database import engine
    with DbSession(engine) as db:
        session = db.get(Session, session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return
        session.research_status = "processing"
        db.add(session)
        db.commit()

    try:
        if not client:
             raise ValueError("GEMINI_API_KEY not configured")

        # Prompt for Gemini to perform research
        prompt = f"""
        You are an expert technical recruiter. Research the typical interview process for a {role} position at {company}.
        
        Use Google Search to find the most recent and relevant information. Synthesize a best-effort summary of the process based on the available search results.
        
        If the search results are completely irrelevant or empty, return exactly this JSON:
        {{
            "error": "insufficient_data",
            "reason": "Could not find specific interview process information."
        }}

        Otherwise, return a JSON object with the following structure:
        {{
            "description": "A brief summary of the process.",
            "steps": [
                {{
                    "type": "screening" | "behavioral" | "technical" | "system_design",
                    "title": "Specific name of the round (e.g. 'Online Assessment', 'Hiring Manager Interview')",
                    "description": "What to expect in this round"
                }}
            ]
        }}
        
        Ensure the steps are in chronological order. Map the rounds to the closest standard type.
        Return ONLY the JSON.
        """
        
        try:
            # Use Google Search Grounding
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt,
                config=GenerateContentConfig(
                    tools=[Tool(googleSearch=GoogleSearch())]
                )
            )
            
            # Parse response
            # Since we can't enforce JSON mode with tools, we must strip markdown
            text = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            
            # Check for explicit error
            if "error" in data and data["error"] == "insufficient_data":
                logger.warning(f"Gemini could not find info: {data.get('reason')}")
                raise ValueError(f"Insufficient data found for {company} {role}")
            
            # Check for "soft failure"
            if not data.get("steps") and ("cannot determine" in data.get("description", "").lower() or "irrelevant" in data.get("description", "").lower()):
                 logger.warning(f"Gemini returned soft failure: {data.get('description')}")
                 raise ValueError("Soft failure in research data")

            final_data = data

        except Exception as e:
            logger.warning(f"Specific research failed: {e}. Falling back to generic.")
            
            # Fallback: Generic Research
            fallback_prompt = f"""
            You are an expert technical recruiter. I could not find specific interview process information for {company}.
            
            Please generate a **standard, best-practice** interview process for a {role} position.
            
            Return a JSON object with the following structure:
            {{
                "description": "A generic interview process for a {role}, as specific data for {company} was not found.",
                "steps": [
                    {{
                        "type": "screening" | "behavioral" | "technical" | "system_design",
                        "title": "Standard round name",
                        "description": "Typical expectations for this round"
                    }}
                ]
            }}
            
            Return ONLY the JSON.
            """
            
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=fallback_prompt,
                config=GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            final_data = json.loads(response.text)

        # 4. Update Session with results
        with DbSession(engine) as db:
            session = db.get(Session, session_id)
            if session:
                session.research_status = "completed"
                session.research_data = final_data
                db.add(session)
                db.commit()
                
        logger.info(f"Research completed for {session_id}")
        
    except Exception as e:
        logger.error(f"Error in research task: {e}")
        with DbSession(engine) as db:
            session = db.get(Session, session_id)
            if session:
                session.research_status = "failed"
                db.add(session)
                db.commit()

@celery_app.task
def perform_context_research(session_id: str, company: str, role: str):
    """
    Background task to research company/role context using Gemini with Google Search Grounding.
    """
    logger.info(f"Starting context research for {company} - {role} (Session {session_id})")
    from .core.database import engine
    from .core.models import ContextData

    try:
        if not client:
             raise ValueError("GEMINI_API_KEY not configured")

        # Single Agent with Grounding
        prompt = f"""
        You are a Research Assistant. Research {company} to prepare a candidate for a {role} interview.
        
        Use Google Search to find information about:
        1. Core Values & Mission
        2. Engineering Culture & Tech Stack (relevant to {role})
        3. Recent News or Strategic Goals
        
        Synthesize the information into a clean, structured summary in Markdown format.
        """
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
            config=GenerateContentConfig(
                tools=[Tool(googleSearch=GoogleSearch())]
            )
        )
        
        clean_content = response.text
        
        if not clean_content:
             raise ValueError("Empty response from Gemini")

        # Store in ContextData
        with DbSession(engine) as db:
            context = ContextData(
                session_id=session_id,
                source="agent_research",
                content=clean_content
            )
            db.add(context)
            db.commit()
            
        logger.info(f"Context research completed for {session_id}")

    except Exception as e:
        logger.error(f"Error in context research task: {e}")
