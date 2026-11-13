"""HTML sahifalar (Jinja2) — API bilan bir xil baza, lekin brauzer uchun."""
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task

# Papka yo'li fayl joylashuviga nisbatan — qaysi papkadan ishga tushirilsa ham topiladi
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / 'templates'
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix='/pages', tags=['pages'], include_in_schema=False)


@router.get('/tasks', response_class=HTMLResponse)
def tasks_page(request: Request, db: Session = Depends(get_db)):
    tasks = db.scalars(select(Task).order_by(Task.id.desc())).all()
    return templates.TemplateResponse(request, 'tasks.html', {'tasks': tasks})


@router.post('/tasks')
def tasks_create(title: str = Form(..., min_length=1, max_length=200), db: Session = Depends(get_db)):
    db.add(Task(title=title.strip()))
    db.commit()
    # POST dan keyin redirect (PRG) — sahifa yangilansa forma qayta yuborilmaydi
    return RedirectResponse('/pages/tasks', status_code=status.HTTP_303_SEE_OTHER)


@router.post('/tasks/{task_id}/toggle')
def tasks_toggle(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is not None:
        task.is_done = not task.is_done
        db.commit()
    return RedirectResponse('/pages/tasks', status_code=status.HTTP_303_SEE_OTHER)
