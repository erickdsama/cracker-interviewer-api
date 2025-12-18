from typing import List
from sqlmodel import Session, select
from uuid import UUID
from ..core.models import Session as DbSession
from .base import BaseRepository

class SessionRepository(BaseRepository[DbSession]):
    def __init__(self, session: Session):
        super().__init__(session, DbSession)

    def get_by_user_id(self, user_id: UUID) -> List[DbSession]:
        statement = select(DbSession).where(DbSession.user_id == user_id)
        return self.session.exec(statement).all()
