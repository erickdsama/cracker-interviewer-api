from .base import InterviewStrategy
from ..leetcode import leetcode_service

class TechnicalStrategy(InterviewStrategy):
    def get_prompt(self, context: str, history: list, user_message: str, role_level: str = "mid") -> str:
        # Extract company name from context (simple heuristic)
        # Context usually starts with "Job Title: ...\nCompany: ..."
        company_name = "google" # Default
        try:
            for line in context.split('\n'):
                if line.startswith("Company:"):
                    company_name = line.split(":", 1)[1].strip()
                    break
        except:
            pass
            
        problem = leetcode_service.get_random_problem(company_name)
        problem_text = ""
        if problem:
            problem_text = f"\n\n**Proposed Problem**: {problem['title']} ({problem['difficulty']})\nURL: {problem['url']}\n\nIf you haven't already, propose this problem to the candidate."

        specific_instruction = f"""
        **Current Step: Technical Interview (Data Structures & Algorithms)**
        - **Goal**: Assess coding skills and problem-solving ability.
        - **Focus**: Propose a coding problem relevant to the job description. Guide the candidate through solving it.
        - **Style**: Collaborative but rigorous. Ask about time/space complexity.
        {problem_text}
        """
        return f"{self._get_base_instruction(role_level)}\n{specific_instruction}\nContext: {context}\nCurrent conversation history:\n{history}\nUser: {user_message}"

    def evaluate(self, context: str, history: list) -> str:
        prompt = f"""
        {self._get_evaluation_instruction()}
        
        **Step Focus**: Technical Interview (DS&A, Coding)
        
        **Evaluation Criteria**:
        - Did they solve the problem?
        - Was the code optimal (Time/Space complexity)?
        - Did they handle edge cases?
        - Did they communicate their thought process?
        - Code quality and cleanliness.
        
        Context: {context}
        Conversation History: {history}
        """
        return prompt
