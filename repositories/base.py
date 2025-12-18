from typing import Generic, TypeVar, Type, Optional, List, Any
from uuid import UUID
from sqlmodel import Session, select, SQLModel

T = TypeVar("T", bound=SQLModel)

class BaseRepository(Generic[T]):
    def __init__(self, session: Session, model_cls: Type[T]):
        self.session = session
        self.model_cls = model_cls

    def get(self, id: UUID) -> Optional[T]:
        return self.session.get(self.model_cls, id)

    def get_all(self) -> List[T]:
        statement = select(self.model_cls)
        return self.session.exec(statement).all()

    def create(self, entity: T) -> T:
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def update(self, id: UUID, data: dict) -> Optional[T]:
        entity = self.get(id)
        if not entity:
            return None
        
        for key, value in data.items():
            setattr(entity, key, value)
            
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def delete(self, id: UUID) -> bool:
        entity = self.get(id)
        if not entity:
            return False
        
        self.session.delete(entity)
        self.session.commit()
        return True
