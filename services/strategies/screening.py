from .base import InterviewStrategy

class ScreeningStrategy(InterviewStrategy):
    def get_prompt(self, context: str, history: list, user_message: str, role_level: str = "mid") -> str:
        specific_instruction = """
        **Current Step: Screening Call**
        - **Goal**: Verify background, motivation, and basic fit.
        - **Focus**: Resume walkthrough, "Why us?", "Tell me about yourself".
        - **Style**: Friendly, professional, and exploratory.
        """
        return f"{self._get_base_instruction(role_level)}\n{specific_instruction}\nContext: {context}\nCurrent conversation history:\n{history}\nUser: {user_message}"

    def evaluate(self, context: str, history: list) -> str:
        prompt = f"""
        {self._get_evaluation_instruction()}
        
        **Step Focus**: Screening Call (Resume, Background, Fit)
        
        **Evaluation Criteria**:
        - Did the candidate clearly explain their background?
        - Is their experience relevant to the role?
        - Did they show genuine interest in the company?
        - Communication clarity and professionalism.
        
        Context: {context}
        Conversation History: {history}
        """
        return prompt
