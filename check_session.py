from sqlmodel import Session, select, create_engine
from backend.core.models import Session as SessionModel
from backend.core.database import DATABASE_URL
import os

# Override DATABASE_URL if needed (it should be set in env)
# But we are running inside container, so it should be fine.

engine = create_engine(os.getenv("DATABASE_URL"))

def check_session(session_id):
    with Session(engine) as db:
        session = db.get(SessionModel, session_id)
        if session:
            print(f"Session ID: {session.id}")
            print(f"Research Status: {session.research_status}")
            print(f"Research Data: {session.research_data}")
        else:
            print(f"Session {session_id} not found")

if __name__ == "__main__":
    check_session("1da73d55-f03b-40c6-a123-756458fe0724")
