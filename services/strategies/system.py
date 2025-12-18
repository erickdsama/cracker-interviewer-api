from .base import InterviewStrategy

class SystemDesignStrategy(InterviewStrategy):
    def get_prompt(self, context: str, history: list, user_message: str, role_level: str = "mid") -> str:
        specific_instruction = """
        **Current Step: System Design**
        - **Goal**: Assess architectural thinking and scalability.
        - **Focus**: Design a system (e.g., "Design Twitter"). Clarify requirements, high-level design, deep dive.
        - **Style**: High-level, architectural, and trade-off focused.
        """
        return f"{self._get_base_instruction(role_level)}\n{specific_instruction}\nContext: {context}\nCurrent conversation history:\n{history}\nUser: {user_message}"

    def evaluate(self, context: str, history: list) -> str:
        prompt = f"""
        {self._get_evaluation_instruction()}
        
        **Step Focus**: System Design (Scalability, Architecture)
        
        **Evaluation Criteria**:
        - Did they clarify requirements?
        - Is the high-level design sound?
        - Did they choose appropriate technologies (DB, API, etc.)?
        - Did they address bottlenecks and scalability?
        - Trade-off analysis.
        
        Context: {context}
        Conversation History: {history}
        """
        return prompt
