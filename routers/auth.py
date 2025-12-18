from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select
from ..database import get_session
from ..models import User, AuthProvider
from ..security import get_password_hash, verify_password, create_access_token
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class UserCreate(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/signup", response_model=Token)
async def signup(user_data: UserCreate, session: Session = Depends(get_session)):
    # Check if user exists
    existing_user = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_pw = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email, 
        hashed_password=hashed_pw,
        auth_provider=AuthProvider.EMAIL
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    # Create token
    access_token = create_access_token(data={"sub": str(new_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

from google.oauth2 import id_token
from google.auth.transport import requests
import os

class GoogleToken(BaseModel):
    token: str

@router.post("/google", response_model=Token)
async def google_login(token_data: GoogleToken, session: Session = Depends(get_session)):
    try:
        # Verify Google Token
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        id_info = id_token.verify_oauth2_token(token_data.token, requests.Request(), client_id)
        
        email = id_info['email']
        
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            # Create user if not exists
            user = User(
                email=email,
                auth_provider=AuthProvider.GOOGLE,
                hashed_password=None
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        
        access_token = create_access_token(data={"sub": str(user.id)})
        return {"access_token": access_token, "token_type": "bearer"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")

from jose import jwt, JWTError
from ..security import SECRET_KEY, ALGORITHM

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = session.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user
