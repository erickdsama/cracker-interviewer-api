from google import genai
import os
from dotenv import load_dotenv
import pathlib

# Force load backend/.env
env_path = pathlib.Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

from .strategies import ScreeningStrategy, BehavioralStrategy, TechnicalStrategy, SystemDesignStrategy
from ..core.logger import get_logger

logger = get_logger(__name__)

import time
from google.api_core import exceptions

class AIService:
    def __init__(self):
        self.model_name = 'gemini-2.0-flash'
        self.strategies = {
            "screening": ScreeningStrategy(),
            "behavioral": BehavioralStrategy(),
            "technical": TechnicalStrategy(),
            "system_design": SystemDesignStrategy()
        }

    def generate_response(self, context: str, history: list, user_message: str, step_type: str = "screening", role_level: str = "mid", roadmap: list = None, remaining_time: int = None) -> str:
        if not client:
            return "Gemini API Key not configured. Mock response."
            
        strategy = self.strategies.get(step_type, self.strategies["screening"])
        
        # Construct prompt
        # Optimization: Truncate history to last 10 messages to save tokens
        truncated_history = history[-10:] if len(history) > 10 else history
        
        # Inject Roadmap and Time
        time_instruction = ""
        if remaining_time is not None:
            time_instruction = f"\nREMAINING TIME: {remaining_time} minutes.\n"
            if remaining_time < 5:
                time_instruction += "WARNING: Time is running out. Skip less important topics. Wrap up the current topic and move to the conclusion. DO NOT ask new deep questions.\n"
            else:
                time_instruction += "Manage your time to cover all roadmap items.\n"
                
        roadmap_instruction = ""
        if roadmap:
            roadmap_instruction = f"\nCURRENT ROADMAP: {', '.join(roadmap)}\nEnsure you are following this roadmap. Move to the next item if the current one is sufficiently covered.\n"
        elif len(history) == 0: # First turn
            roadmap_instruction = "\nTASK: Create a concise 3-5 item roadmap for this interview step based on the duration. List the roadmap items at the start of your response in a block like <roadmap>Item 1, Item 2, Item 3</roadmap>.\n"

        prompt = strategy.get_prompt(context, truncated_history, user_message, role_level)
        prompt += time_instruction + roadmap_instruction
        
        retries = 3
        for attempt in range(retries):
            try:
                logger.info(f"Generating AI response for step: {step_type} (Attempt {attempt + 1})...")
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                # Basic retry logic, catching general exception as genai exceptions might differ
                wait_time = (2 ** attempt) + 1 # 2, 3, 5 seconds
                logger.warning(f"Error or quota exceeded. Retrying in {wait_time} seconds... Error: {e}")
                time.sleep(wait_time)
        
        return "Sorry, the AI service is currently busy. Please try again later."

    def evaluate_step(self, context: str, history: list, step_type: str) -> str:
        if not client:
            return "Gemini API Key not configured. Mock evaluation."
            
        strategy = self.strategies.get(step_type, self.strategies["screening"])
        prompt = strategy.evaluate(context, history)
        
        retries = 3
        for attempt in range(retries):
            try:
                logger.info(f"Generating evaluation for step: {step_type} (Attempt {attempt + 1})...")
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                logger.error(f"Error generating evaluation: {e}")
                time.sleep(2 ** attempt)
        
        return "Evaluation unavailable due to high traffic."

    def get_hiring_manager_feedback(self, context: str, history: list, bar_raiser_feedback: str = None) -> str:
        if not client:
            return "Gemini API Key not configured. Mock HM feedback."
            
        br_section = ""
        if bar_raiser_feedback:
            br_section = f"\n**Technical Evaluation (Bar Raiser)**:\n{bar_raiser_feedback}\n"

        prompt = f"""
        You are a seasoned Hiring Manager at a top-tier tech company. You are reviewing an interview transcript AND a technical evaluation from a "Bar Raiser" to decide if this candidate is someone you want on your team.
        
        Your perspective is DIFFERENT from the Bar Raiser. While they focus on technical correctness, YOU focus on "Hireability", "Team Impact", and "Actionable Growth".
        
        **Context**:
        {context}
        
        **Interview Transcript**:
        {history}
        {br_section}
        
        **Instructions**:
        1. **Aligned but Independent**: Use the Bar Raiser's feedback to understand the candidate's technical standing, but provide YOUR OWN managerial perspective.
        2. **Fresh Considerations**: Provide insights that a technical evaluator might miss (e.g., communication style, attitude, clarity of thought, potential for growth).
        3. **Actionable Advice**: Give 3-5 VERY specific tips on what they need to change or emphasize to get the "Hire" verdict from a manager, taking into account their technical performance.
        4. **Key Missing Element**: What is the ONE thing that, if fixed, would make them an irresistible hire?
        
        **Format**:
        ### 💼 Hiring Manager's Perspective
        *Fresh considerations for your hireability:*

        - **Actionable Tip**: ...
        - **Actionable Tip**: ...
        ...
        
        **🎯 The "Hire" Closer**: [The one thing you need to nail to get the offer]
        """
        
        retries = 3
        for attempt in range(retries):
            try:
                logger.info(f"Generating HM feedback (Attempt {attempt + 1})...")
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                return response.text
            except Exception as e:
                logger.error(f"Error generating HM feedback: {e}")
                time.sleep(2 ** attempt)
        
        return "Hiring Manager feedback unavailable."

ai_service = AIService()
