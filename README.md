# FastAPI Template

FastAPI + SQLAlchemy 2.0 asosidagi oddiy CRUD API shablon. Misol: vazifalar (tasks).

## Ishga tushirish

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

## Endpointlar

| Method | URL | Vazifasi |
|---|---|---|
| GET | `/tasks/` | ro'yxat (`?is_done=true`, `?skip=0&limit=20`) |
| POST | `/tasks/` | yangi vazifa |
| GET | `/tasks/{id}` | bitta vazifa |
| PATCH | `/tasks/{id}` | o'zgartirish |
| DELETE | `/tasks/{id}` | o'chirish |

## Tuzilishi

```
app/
  database.py     engine, session, get_db
  models.py       SQLAlchemy modellari
  schemas.py      Pydantic sxemalar
  routers/tasks.py
  main.py
tests/
```

## Testlar

```bash
pytest
```
