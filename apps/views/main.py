from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from apps.forms import ProfileResponse
from apps.models import engine, User
from apps.utils import verify_token

security = HTTPBearer()
app = FastAPI()


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/user/get/me", response_model=ProfileResponse)
async def get_profile(session: SessionDep,
                      credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = verify_token(credentials.credentials, token_type="access")
    user = session.get(User, int(user_id))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User topilmadi")
    return user
