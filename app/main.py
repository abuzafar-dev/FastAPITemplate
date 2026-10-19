from fastapi import FastAPI

from app.database import Base, engine
from app.routers import tasks

Base.metadata.create_all(bind=engine)

app = FastAPI(title='FastAPI Template')

app.include_router(tasks.router)


@app.get('/')
def root():
    return {'message': 'FastAPI Template ishlayapti', 'docs': '/docs'}
