from typing import Optional
import os
from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException, status
from jose import jwt, JWTError

from ..core.models import User, AuthProvider
from ..repositories.user import UserRepository
from ..core.security import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM

class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def signup(self, email: str, password: str) -> str:
        existing_user = self.user_repository.get_by_email(email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_pw = get_password_hash(password)
        new_user = User(
            email=email, 
            hashed_password=hashed_pw,
            auth_provider=AuthProvider.EMAIL
        )
        self.user_repository.create(new_user)
        
        return create_access_token(data={"sub": str(new_user.id)})

    def login(self, email: str, password: str) -> str:
        user = self.user_repository.get_by_email(email)
        if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return create_access_token(data={"sub": str(user.id)})

    def google_login(self, token: str) -> str:
        try:
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            id_info = id_token.verify_oauth2_token(token, requests.Request(), client_id)
            email = id_info['email']
            
            user = self.user_repository.get_by_email(email)
            if not user:
                user = User(
                    email=email,
                    auth_provider=AuthProvider.GOOGLE,
                    hashed_password=None
                )
                self.user_repository.create(user)
            
            return create_access_token(data={"sub": str(user.id)})
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid Google token: {str(e)}")

    def get_current_user(self, token: str) -> User:
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
            
        user = self.user_repository.get(user_id)
        if user is None:
            raise credentials_exception
        return user
