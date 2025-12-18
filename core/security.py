from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import hashlib

def verify_password(plain_password, hashed_password):
    # Pre-hash with SHA256 to handle long passwords
    sha256_password = hashlib.sha256(plain_password.encode()).hexdigest()
    return pwd_context.verify(sha256_password, hashed_password)

def get_password_hash(password):
    # Pre-hash with SHA256 to handle long passwords
    sha256_password = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.hash(sha256_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
