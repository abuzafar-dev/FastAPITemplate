import bcrypt
from pydantic import BaseModel, field_validator, model_validator
from sqlmodel import Session, select

from apps.models import engine, User


class ProfileResponse(BaseModel):
    id : int
    name : str
    age : int
    username: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LoginForm(BaseModel):
    username: str
    password : str
    @model_validator(mode='after')
    def validate__entire_model(self):
        statement = select(User).where(User.username == self.username)
        session: Session = Session(engine)
        data = session.exec(statement).all()
        if data:
            user = data[0]
            if not bcrypt.checkpw(self.password.encode() , user.password.encode()):
                raise ValueError("Password xato !")
        else:
            raise ValueError("User topilmadi !")
        return self

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token : str

class RegisterForm(BaseModel):
    name : str
    age : int
    username : str
    password : str

    @field_validator('username')
    @classmethod
    def validate_username(cls ,  value : str):
        statement = select(User).where(User.username == value)
        session: Session = Session(engine)
        data = session.exec(statement).all()
        if data:
            raise ValueError("Bunday username oldin takrorlangan")
        return value

    @field_validator('password')
    @classmethod
    def validate_password(cls, value : str):
        return bcrypt.hashpw(value.encode() , salt=bcrypt.gensalt()).decode()