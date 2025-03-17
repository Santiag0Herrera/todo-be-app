from typing import Annotated
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from models import Users
from database import SessionLocal
from starlette import status
from .auth import get_current_user
from passlib.context import CryptContext

router = APIRouter(
  prefix='/users',
  tags=['Users']
)

def get_db():
  db = SessionLocal()
  try: 
    yield db
  finally:
    db.close() 

class UserVerification(BaseModel):
  password: str
  new_password: str = Field(min_length=6)


bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

@router.get("/me", status_code=status.HTTP_200_OK)
async def get_current_user_info(user: user_dependency, db: db_dependency):
  if user is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found or not logged in')
  return db.query(Users).filter(Users.id == user.get('id')).first()

@router.put("/me/changePassword", status_code=status.HTTP_200_OK)
async def change_password(user: user_dependency, db: db_dependency, user_verification: UserVerification):
  if user is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found or not logged in')
  
  user_model = db.query(Users).filter(Users.id == user.get('id')).first()
  if not bcrypt_context.verify(user_verification.password, user_model.hashed_password):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect password')
  user_model.hashed_password = bcrypt_context.hash(user_verification.new_password)
  db.add(user_model)
  db.commit()