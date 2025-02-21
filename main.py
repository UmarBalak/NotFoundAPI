from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
from models import Base, engine, User, SessionLocal, Space, CollaborationRequest
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

class CollaborationRequestCreate(BaseModel):
    space_id: int
    collaborator_email: str

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
    # Validate input
    if not space.space_name or not space.tags or not space.category or not space.github_id:
        raise HTTPException(status_code=400, detail="All fields are required")
    
    # Clean tags
    tags = [tag.strip() for tag in space.tags if tag.strip()]
    if not tags:
        raise HTTPException(status_code=400, detail="At least one valid tag is required")
    
    new_space = Space(
        space_name=space.space_name.strip(),
        tags=",".join(tags),
        category=space.category.strip(),
        github_id=space.github_id.strip(),
        description=space.description.strip()
    )
    
    try:
        db.add(new_space)
        db.commit()
        db.refresh(new_space)
        return {"message": "Space created successfully!", "space_id": new_space.id}
    except Exception as e:
        db.rollback()
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error occurred: {str(e)}")

@app.get("/spaces")
def get_spaces(db: SQLAlchemySession = Depends(get_db)):
    spaces = db.query(Space).all()
    return spaces

@app.post("/collaborate")
def request_collaboration(request: CollaborationRequestCreate, db: SQLAlchemySession = Depends(get_db)):
    space = db.query(Space).filter(Space.id == request.space_id).first()
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    
    existing_request = db.query(CollaborationRequest).filter(
        CollaborationRequest.space_id == request.space_id,
        CollaborationRequest.collaborator_email == request.collaborator_email
    ).first()
    
    if existing_request:
        raise HTTPException(status_code=400, detail="Collaboration request already exists")
    
    new_request = CollaborationRequest(
        space_id=request.space_id,
        collaborator_email=request.collaborator_email
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return {"message": "Collaboration request sent"}

@app.get("/notifications")
def get_notifications(email: str, db: SQLAlchemySession = Depends(get_db)):
    requests = db.query(CollaborationRequest).filter(CollaborationRequest.collaborator_email == email).all()
    notifications = []
    for request in requests:
        space = db.query(Space).filter(Space.id == request.space_id).first()
        if space:
            notifications.append({
                "space_id": space.id,
                "space_name": space.space_name,
                "status": request.status
            })
    return notifications

@app.post("/approve_collaboration")
def approve_collaboration(space_id: int, collaborator_email: str, db: SQLAlchemySession = Depends(get_db)):
    request = db.query(CollaborationRequest).filter(
        CollaborationRequest.space_id == space_id,
        CollaborationRequest.collaborator_email == collaborator_email
    ).first()
    
    if not request:
        raise HTTPException(status_code=404, detail="Collaboration request not found")
    
    request.status = "approved"
    db.commit()
    return {"message": "Collaboration approved"}