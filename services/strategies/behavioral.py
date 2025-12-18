from .base import InterviewStrategy

class BehavioralStrategy(InterviewStrategy):
    def get_prompt(self, context: str, history: list, user_message: str, role_level: str = "mid") -> str:
        specific_instruction = """
        **Current Step: Behavioral Interview**
        - **Goal**: Assess soft skills, leadership, and culture fit.
        - **Focus**: STAR method questions (Situation, Task, Action, Result).
        - **Style**: Inquisitive and focused on specific examples.
        """
        return f"{self._get_base_instruction(role_level)}\n{specific_instruction}\nContext: {context}\nCurrent conversation history:\n{history}\nUser: {user_message}"

    def evaluate(self, context: str, history: list) -> str:
        prompt = f"""
        {self._get_evaluation_instruction()}
        
        **Step Focus**: Behavioral Interview (STAR Method, Culture Fit)
        
        **Evaluation Criteria**:
        - Did they use the STAR method?
        - Did they demonstrate leadership/ownership?
        - How did they handle conflict/challenges?
        - Are they a culture add?
        
        Context: {context}
        Conversation History: {history}
        """
        return prompt
