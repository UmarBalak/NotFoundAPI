from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
from .models import Base, engine, User, SessionLocal
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy import or_

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Error while creating table: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    email: str = Header(..., description="User's email for authentication"),
    db: SQLAlchemySession = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user

class CreateUser(BaseModel):
    name: str
    email: str
    password: str

class LoginUser(BaseModel):
    email: str
    password: str

app = FastAPI()

@app.post("/register")
def register_user(user: CreateUser, db: SQLAlchemySession = Depends(get_db)):
    user_exist = db.query(User).filter(User.email == user.email).first()
    if user_exist:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        name=user.name,
        email=user.email,
        password=user.password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User registered successfully!", "user_id": new_user.id}

@app.post("/login")
def login(login_data: LoginUser, db: SQLAlchemySession = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email")
    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "password": user.password
        }
    }
