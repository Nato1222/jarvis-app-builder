import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .database.database import get_connection

# Environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "change_me_to_a_secure_value")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

router = APIRouter()

class User(BaseModel):
    username: str

class UserInDB(User):
    password_hash: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user_from_token(token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    conn = get_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (token_data.username,)).fetchone()
    conn.close()

    if user is None:
        raise credentials_exception
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    return await get_user_from_token(token)

async def get_current_user_ws(token: str = Query(...)):
    return await get_user_from_token(token)

@router.get("/me")
def me(current_user = Depends(get_current_user)):
    """Return minimal current user info for the UI."""
    return {
        "id": current_user["user_id"] if "user_id" in current_user else current_user.get("id"),
        "username": current_user["username"],
        "role": current_user.get("role", "ceo"),
    }

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(user_data: UserLogin):
    conn = get_connection()
    try:
        # Check if user already exists
        existing_user = conn.execute('SELECT user_id FROM users WHERE username = ?', (user_data.username,)).fetchone()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered",
            )
        
        hashed_password = get_password_hash(user_data.password)
        conn.execute(
            'INSERT INTO users (username, password_hash) VALUES (?, ?)',
            (user_data.username, hashed_password)
        )
        conn.commit()
    finally:
        conn.close()
        
    return {"message": "User created successfully"}


@router.post("/login", response_model=Token)
def login(user_data: UserLogin):
    conn = get_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (user_data.username,)).fetchone()
    conn.close()

    if not user or not verify_password(user_data.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user['username']}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
