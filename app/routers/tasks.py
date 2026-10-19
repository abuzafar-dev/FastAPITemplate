from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task
from app.schemas import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix='/tasks', tags=['tasks'])


def get_task_or_404(task_id: int, db: Session):
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Vazifa topilmadi')
    return task


@router.get('/', response_model=list[TaskRead])
def list_tasks(is_done: bool | None = None, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    query = select(Task).order_by(Task.id.desc())
    if is_done is not None:
        query = query.where(Task.is_done == is_done)
    return db.scalars(query.offset(skip).limit(limit)).all()


@router.post('/', response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    task = Task(**data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get('/{task_id}', response_model=TaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)):
    return get_task_or_404(task_id, db)


@router.patch('/{task_id}', response_model=TaskRead)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    task = get_task_or_404(task_id, db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


@router.delete('/{task_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = get_task_or_404(task_id, db)
    db.delete(task)
    db.commit()
