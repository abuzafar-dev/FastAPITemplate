from typing import Annotated
from fastapi import FastAPI, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, select
from apps.forms import ProfileResponse
from apps.models import engine, User
from apps.utils import verify_token

security = HTTPBearer()
app = FastAPI()

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]
@app.get("/user/get/me" , response_model=ProfileResponse)
async def get_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
    username = verify_token(credentials.credentials, token_type="access")
    session = Session(engine)
    user = session.exec(select(User).where(User.username==username)).all()[0]
    return user.__dict__