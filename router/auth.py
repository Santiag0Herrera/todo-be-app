from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette import status
from pydantic import BaseModel, Field
from database import SessionLocal
from models import Users
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import timedelta, datetime, timezone

router = APIRouter(
  prefix='/auth',
  tags=['Authentication']
)

SECRET_KEY = 'bf75bf97eb8839552b6d64790c35fdecbe8874bd1791917b650494d3d54c60b5'
ALGORITHM = 'HS256'

def get_db():
  db = SessionLocal()
  try: 
    yield db
  finally:
    db.close()

db_dependency = Annotated[Session, Depends(get_db)]
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')


class CreateUserRequest(BaseModel):
  username: str
  email: str
  first_name: str
  last_name: str
  password: str
  role: str


class Token(BaseModel):
  access_token: str
  token_type: str


def authenticate_user(username: str, password: str, db):
  user = db.query(Users).filter(Users.username == username).first()
  if not user:
    return False
  if not bcrypt_context.verify(password, user.hashed_password):
    return False
  return user


def create_token(username: str, user_id: int, role: str, expires_delta: timedelta):
  encode = {'sub': username, 'id': user_id, 'role': role}
  expires = datetime.now(timezone.utc) + expires_delta
  encode.update({'exp': expires})
  return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
  try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username: str = payload.get('sub')
    user_id: int = payload.get('id')
    user_role: str = payload.get('role')
    if username is None or user_id is None:
      raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid Credentials') 
    return {'username': username, 'id': user_id, 'user_role': user_role}
  except JWTError:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid Credentials')


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
  create_user_model = Users(
    email=create_user_request.email,
    username=create_user_request.username,
    first_name=create_user_request.first_name,
    last_name=create_user_request.last_name,
    hashed_password=bcrypt_context.hash(create_user_request.password),
    is_active=True,
    role= create_user_request.role
  )
  db.add(create_user_model)
  db.commit()


@router.post("/token", response_model=Token)
async def get_login_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
  user = authenticate_user(form_data.username, form_data.password, db)
  if not user: 
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user.')
  token = create_token(user.username, user.id, user.role, timedelta(minutes=20 ))
  return {'access_token': token, 'token_type': 'bearer'}


@router.get("/users", status_code=status.HTTP_200_OK)
async def get_users(db: db_dependency):
  return db.query(Users).all()

@router.delete("/users", status_code=status.HTTP_202_ACCEPTED)
async def delete_user(db: db_dependency, user_id: int):
  user_model = db.query(Users).filter(Users.id == user_id).first()
  if user_model is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found")
  db.query(Users).filter(Users.id == user_id).delete()
  db.commit()