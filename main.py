from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
from models import Base, engine, User, SessionLocal, Space
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy import or_
from passlib.context import CryptContext

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

class CreateSpace(BaseModel):
    space_name: str
    tags: List[str]
    category: str
    github_id: str
    description: str

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

@app.post("/register")
def register_user(user: CreateUser, db: SQLAlchemySession = Depends(get_db)):
    user_exist = db.query(User).filter(User.email == user.email).first()
    if user_exist:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        name=user.name,
        email=user.email,
        password=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User registered successfully!", "user_id": new_user.id}

@app.post("/login")
def login(login_data: LoginUser, db: SQLAlchemySession = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {
        "message": "Login successful",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
    }

@app.post("/spaces")
def create_space(space: CreateSpace, db: SQLAlchemySession = Depends(get_db)):
    new_space = Space(
        space_name=space.space_name,
        tags=",".join(space.tags),
        category=space.category,
        github_id=space.github_id,
        description=space.description
    )
    print(new_space)
    db.add(new_space)
    print("new space added")
    db.commit()
    print("new space committed")
    db.refresh(new_space)
    
    return {"message": "Space created successfully!", "space_id": new_space.id}

@app.get("/spaces")
def get_spaces(db: SQLAlchemySession = Depends(get_db)):
    spaces = db.query(Space).all()
    return spaces