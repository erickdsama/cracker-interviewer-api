from abc import ABC, abstractmethod

class InterviewStrategy(ABC):
    @abstractmethod
    def get_prompt(self, context: str, history: list, user_message: str) -> str:
        pass

    @abstractmethod
    def evaluate(self, context: str, history: list) -> str:
        pass

    def _get_base_instruction(self, role_level: str = "mid") -> str:
        level_instruction = ""
        if role_level == "junior":
            level_instruction = "Candidate is Junior. Focus on fundamentals, potential, and ability to learn. Be helpful."
        elif role_level == "mid":
            level_instruction = "Candidate is Mid-level. Expect solid execution, independence, and good communication."
        elif role_level == "senior":
            level_instruction = "Candidate is Senior. Expect system design depth, trade-off analysis, and leadership. Be rigorous."
        elif role_level in ["staff", "principal"]:
            level_instruction = "Candidate is Staff/Principal. Focus heavily on architecture, scalability, business impact, and organizational influence."
        elif role_level == "manager":
            level_instruction = "Candidate is Engineering Manager. Focus on people management, project delivery, and strategy."

        return f"""
        You are an expert technical recruiter and interviewer, following the principles of "Cracking the Coding Interview".
        
        **Role Level**: {role_level.upper()}
        {level_instruction}
        Respond as the interviewer.
        
        Guidelines:
        1. **Be conversational**: Respond naturally.
        2. **Be concise**: Keep responses short (max 2-3 sentences).
        3. **One thing at a time**: Ask only ONE question per response.
        4. **Step-by-step**: Don't dump a huge problem statement.
        5. **Formatting**: Use simple text.
        """

    def _get_evaluation_instruction(self) -> str:
        return """
        You are a critical "Bar Raiser" interviewer. Your job is to evaluate the candidate's performance in this step.
        
        **CRITICAL INSTRUCTIONS**:
        1. **Be Brutally Honest**: Do not sugarcoat. Identify every weakness.
        2. **Score**: Assign a score from 0 to 10 based on industry standards (FAANG level).
        3. **Verdict**: Must be one of: Strong No Hire, No Hire, Lean No Hire, Lean Hire, Hire, Strong Hire.
        4. **Format**:
            - **Score**: X/10
            - **Verdict**: [Verdict]
            - **Pros**: [Bullet points]
            - **Cons**: [Bullet points]
            - **Detailed Feedback**: [Paragraph]
        """
