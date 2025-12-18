import os
import json
from google import genai
from duckduckgo_search import DDGS
from .celery_worker import celery_app
from .database import get_session
from .models import Session, SessionStep, StepType, StepStatus
from sqlmodel import select, Session as DbSession
from typing import List, Dict

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

@celery_app.task
def perform_interview_research(session_id: str, company: str, role: str):
    """
    Background task to research interview process and update the session.
    """
    print(f"Starting research for {company} - {role} (Session {session_id})")
    
    # 1. Update status to processing
    from .database import engine
    with DbSession(engine) as db:
        session = db.get(Session, session_id)
        if not session:
            print(f"Session {session_id} not found")
            return
        session.research_status = "processing"
        db.add(session)
        db.commit()

    try:
        # 2. Perform Search
        query = f"{company} {role} interview process rounds questions"
        print(f"Searching for: {query}")
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            
        search_context = "\n\n".join([f"Title: {r['title']}\nSnippet: {r['body']}\nLink: {r['href']}" for r in results])
        
        # 3. Synthesize with LLM
        if not client:
             raise ValueError("GEMINI_API_KEY not configured")

        prompt = f"""
        You are an expert technical recruiter. Based on the following search results, identify the typical interview rounds for a {role} position at {company}.
        
        Search Results:
        {search_context}
        
        Return a JSON object with the following structure:
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
        
        Ensure the steps are in chronological order. Map the rounds to the closest standard type (screening, behavioral, technical, system_design).
        Return ONLY the JSON.
        """
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt
        )
        # Clean up response if it contains markdown code blocks
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        
        # 4. Update Session with results
        with DbSession(engine) as db:
            session = db.get(Session, session_id)
            if session:
                session.research_status = "completed"
                session.research_data = data
                
                # Optional: Auto-create steps if the user hasn't customized them yet?
                # For now, we just store the data. The frontend will let the user apply it.
                
                db.add(session)
                db.commit()
                
        print(f"Research completed for {session_id}")
        
    except Exception as e:
        print(f"Error in research task: {e}")
        with DbSession(engine) as db:
            session = db.get(Session, session_id)
            if session:
                session.research_status = "failed"
                db.add(session)
                db.commit()

@celery_app.task
def perform_context_research(session_id: str, company: str, role: str):
    """
    Background task to research company/role context using an Agent-to-Agent workflow.
    Workflow: Search Agent -> Evaluator Agent -> Cleaner Agent
    """
    print(f"Starting context research for {company} - {role} (Session {session_id})")
    from .database import engine
    from .models import ContextData

    try:
        # 1. Search Agent
        query = f"{company} company values culture tech stack news"
        print(f"Searching for: {query}")
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=10))
        
        raw_context = "\n\n".join([f"Title: {r['title']}\nSnippet: {r['body']}\nLink: {r['href']}" for r in results])
        
        # 2. Evaluator Agent (Check if data is sufficient)
        if not client:
             raise ValueError("GEMINI_API_KEY not configured")

        eval_prompt = f"""
        You are a Data Quality Evaluator. Analyze the following search results for {company}.
        Determine if there is sufficient information about:
        1. Company Values/Culture
        2. Technology Stack (if applicable)
        3. Recent News/Events

        Search Results:
        {raw_context}

        Return JSON:
        {{
            "sufficient": boolean,
            "missing_topics": ["list", "of", "missing", "topics"],
            "reasoning": "brief explanation"
        }}
        """
        eval_response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=eval_prompt
        )
        eval_text = eval_response.text.replace("```json", "").replace("```", "").strip()
        eval_data = json.loads(eval_text)
        
        if not eval_data["sufficient"]:
            print(f"Data insufficient: {eval_data['missing_topics']}. Proceeding with best effort.")
            # In a more complex system, we would trigger a secondary search here.

        # 3. Cleaner Agent (Synthesize and Format)
        clean_prompt = f"""
        You are a Research Assistant. Synthesize the following search results into a clean, structured summary for a candidate preparing for an interview at {company} for a {role} position.
        
        Focus on:
        - Core Values & Mission
        - Engineering Culture & Tech Stack (relevant to {role})
        - Recent News or Strategic Goals
        
        Search Results:
        {raw_context}
        
        Return a well-formatted Markdown string.
        """
        clean_response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=clean_prompt
        )
        clean_content = clean_response.text
        
        # 4. Store in ContextData
        with DbSession(engine) as db:
            # Clear old context from this source to avoid duplicates if re-run
            # Actually, let's just append or replace. For now, simple add.
            context = ContextData(
                session_id=session_id,
                source="agent_research",
                content=clean_content
            )
            db.add(context)
            db.commit()
            
        print(f"Context research completed for {session_id}")

    except Exception as e:
        print(f"Error in context research task: {e}")
