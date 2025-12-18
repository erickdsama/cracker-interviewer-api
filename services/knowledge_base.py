from sqlmodel import select, Session
from ..core.models import KnowledgeBase
from ..core.database import engine
from ..core.logger import get_logger

logger = get_logger(__name__)

def seed_knowledge_base():
    """
    Seeds the Knowledge Base with initial data if empty.
    """
    with Session(engine) as session:
        # Check if empty
        existing = session.exec(select(KnowledgeBase)).first()
        if existing:
            return

        logger.info("Seeding Knowledge Base...")
        
        initial_data = [
            {
                "category": "General",
                "title": "STAR Method",
                "content": "The STAR method is a structured manner of responding to a behavioral-based interview question by discussing the specific Situation, Task, Action, and Result of the situation you are describing."
            },
            {
                "category": "General",
                "title": "Questions to Ask",
                "content": "Always have questions prepared for your interviewer. Examples: 'What does a typical day look like?', 'What are the biggest challenges the team is facing?', 'How is success measured in this role?'"
            },
            {
                "category": "Technical",
                "title": "System Design Basics",
                "content": "Key concepts: Scalability, Availability, Reliability, Consistency, Partition Tolerance (CAP Theorem), Load Balancing, Caching, Database Sharding."
            },
            {
                "category": "Behavioral",
                "title": "Handling Conflict",
                "content": "Focus on resolution and professional growth. Describe the situation objectively, explain your perspective and the other person's, describe the steps taken to resolve it, and the positive outcome."
            }
        ]
        
        for item in initial_data:
            kb_item = KnowledgeBase(
                category=item["category"],
                title=item["title"],
                content=item["content"]
            )
            session.add(kb_item)
        
        session.commit()
        session.commit()
        logger.info("Knowledge Base seeded.")
