from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import pages, tasks

Base.metadata.create_all(bind=engine)

app = FastAPI(title='FastAPI Template')

app.mount('/static', StaticFiles(directory=Path(__file__).resolve().parent / 'static'), name='static')

app.include_router(tasks.router)
app.include_router(pages.router)


@app.get('/')
def root():
    return {'message': 'FastAPI Template ishlayapti', 'docs': '/docs', 'pages': '/pages/tasks'}
