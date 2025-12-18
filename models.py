from sqlmodel import SQLModel, Field, Relationship, AutoString
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
import uuid
from sqlalchemy.dialects.postgresql import JSON

class AuthProvider(str, Enum):
    EMAIL = "email"
    GOOGLE = "google"
    APPLE = "apple"

class SessionStatus(str, Enum):
    PLANNING = "planning"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class StepType(str, Enum):
    SCREENING = "screening"
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SYSTEM_DESIGN = "system_design"

class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    auth_provider: AuthProvider = Field(default=AuthProvider.EMAIL)
    hashed_password: Optional[str] = None
    subscription_tier: str = Field(default="free")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    resumes: List["Resume"] = Relationship(back_populates="user")
    sessions: List["Session"] = Relationship(back_populates="user")

class Resume(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    file_path: str
    parsed_content: str
    
    user: User = Relationship(back_populates="resumes")

class RoleLevel(str, Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    MANAGER = "manager"

class Session(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    job_title: str
    company_name: str
    jd_content: str
    role_level: RoleLevel = Field(default=RoleLevel.MID, sa_type=AutoString)
    duration_minutes: int = Field(default=15)
    status: SessionStatus = Field(default=SessionStatus.PLANNING)
    
    # Research Status
    research_status: str = Field(default="pending") # pending, processing, completed, failed
    research_data: Optional[Dict] = Field(default=None, sa_type=JSON)

    current_step: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="sessions")
    steps: List["SessionStep"] = Relationship(back_populates="session")
    context_data: List["ContextData"] = Relationship(back_populates="session")

class SessionStep(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="session.id")
    step_type: StepType
    status: StepStatus = Field(default=StepStatus.PENDING)
    interaction_log: List = Field(default=[], sa_type=JSON)
    feedback: Optional[str] = None
    started_at: Optional[datetime] = Field(default=None)
    title: Optional[str] = Field(default=None)
    roadmap: Optional[List[str]] = Field(default=None, sa_type=JSON)
    
    session: Session = Relationship(back_populates="steps")

class ContextData(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="session.id")
    source: str
    content: str
    
    session: Session = Relationship(back_populates="context_data")

class KnowledgeBase(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category: str
    title: str
    content: str
