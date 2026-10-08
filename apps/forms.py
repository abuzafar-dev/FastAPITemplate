from pydantic import BaseModel, EmailStr, Field


class ProfileResponse(BaseModel):
    id: int
    name: str
    age: int
    username: str
    email: EmailStr


class RegisterForm(BaseModel):
    name: str
    age: int
    username: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class VerifyForm(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResendForm(BaseModel):
    email: EmailStr


class LoginForm(BaseModel):
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
