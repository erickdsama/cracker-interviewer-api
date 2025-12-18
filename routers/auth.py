from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session
from ..core.database import get_session
from ..core.models import User
from pydantic import BaseModel
from ..repositories.user import UserRepository
from ..services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class GoogleToken(BaseModel):
    token: str

def get_user_repository(session: Session = Depends(get_session)) -> UserRepository:
    return UserRepository(session)

def get_auth_service(user_repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    return AuthService(user_repo)

@router.post("/signup", response_model=Token)
async def signup(user_data: UserCreate, auth_service: AuthService = Depends(get_auth_service)):
    access_token = auth_service.signup(user_data.email, user_data.password)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), auth_service: AuthService = Depends(get_auth_service)):
    access_token = auth_service.login(form_data.username, form_data.password)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/google", response_model=Token)
async def google_login(token_data: GoogleToken, auth_service: AuthService = Depends(get_auth_service)):
    access_token = auth_service.google_login(token_data.token)
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme), auth_service: AuthService = Depends(get_auth_service)):
    return auth_service.get_current_user(token)
