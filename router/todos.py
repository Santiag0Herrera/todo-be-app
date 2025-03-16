from typing import Annotated
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query
from models import Todos
from database import SessionLocal
from starlette import status
from .auth import get_current_user


router = APIRouter(
  prefix='/todo',
  tags=['To Do']
)


class TodoRequest(BaseModel):
  title: str = Field(min_length=3)
  description: str = Field(min_length=3, max_length=100)
  priority: int = Field(gt=-1, lt=11)
  complete: bool


def get_db():
  db = SessionLocal()
  try: 
    yield db
  finally:
    db.close()
  

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


def validate_user(user: user_dependency):
  if user is None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not authenticated')


@router.get("/all")
async def get_all_todos(user: user_dependency, db: db_dependency):
  return db.query(Todos).filter(Todos.owner_id == user.get('id')).all()


@router.get("/getById", status_code=status.HTTP_200_OK)
async def get_todo_by_id(user: user_dependency, db: db_dependency, todo_id: int = Query(gt=0)):
  validate_user(user)
  todo_model = db.query(Todos).filter(Todos.id == todo_id).filter(Todos.owner_id == user.get('id')).first()
  if todo_model is not None:
    return todo_model
  else:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo {todo_id} not found")


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_new_todo(user: user_dependency, db: db_dependency, todo_request: TodoRequest):
  validate_user(user)
  todo_model = Todos(**todo_request.model_dump(), owner_id=user.get('id'))
  db.add(todo_model)
  db.commit()


@router.put("/updateById", status_code=status.HTTP_200_OK)
async def update_existing_todo(user: user_dependency, db: db_dependency, todo_request: TodoRequest, todo_id: int = Query(gt=0)):
  validate_user(user)
  todo_model = db.query(Todos).filter(Todos.id == todo_id).filter(Todos.owner_id == user.get('id')).first()

  if todo_model is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo {todo_id} not found")
  
  todo_model.title = todo_request.title
  todo_model.description = todo_request.description
  todo_model.priority = todo_request.priority
  todo_model.complete = todo_request.complete
  db.add(todo_model)
  db.commit()


@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(user: user_dependency, db: db_dependency, todo_id: int = Query(gt=0)):
  validate_user(user)
  todo_model = db.query(Todos).filter(Todos.id == todo_id).filter(Todos.owner_id == user.get('id')).first()
  if todo_model is None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Todo {todo_id} not found")
  db.query(Todos).filter(Todos.id == todo_id).delete()
  db.commit()