# FastAPI Template

FastAPI + SQLAlchemy 2.0 asosidagi oddiy CRUD API shablon. Misol: vazifalar (tasks).

## Quick start

```bash
make run     # creates .venv and .env, installs deps, starts the app
make test    # checks + tests
```

## Ishga tushirish

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs  
HTML sahifa (Jinja2): http://127.0.0.1:8000/pages/tasks

## Endpointlar

| Method | URL | Vazifasi |
|---|---|---|
| GET | `/tasks/` | ro'yxat (`?is_done=true`, `?skip=0&limit=20`) |
| POST | `/tasks/` | yangi vazifa |
| GET | `/tasks/{id}` | bitta vazifa |
| PATCH | `/tasks/{id}` | o'zgartirish |
| DELETE | `/tasks/{id}` | o'chirish |

### HTML sahifalar (Jinja2 + forma)

| Method | URL | Vazifasi |
|---|---|---|
| GET | `/pages/tasks` | vazifalar ro'yxati + qo'shish formasi |
| POST | `/pages/tasks` | formadan yangi vazifa (`Form(...)`), keyin redirect |
| POST | `/pages/tasks/{id}/toggle` | bajarildi / bajarilmadi |

## Tuzilishi

```
app/
  database.py     engine, session, get_db
  models.py       SQLAlchemy modellari
  schemas.py      Pydantic sxemalar
  routers/tasks.py   JSON API
  routers/pages.py   HTML sahifalar (Jinja2Templates, Form)
  templates/         base.html, tasks.html
  static/            style.css
  main.py
tests/
```

## Testlar

```bash
pytest
```
