from pydantic import BaseModel, EmailStr, Field, field_validator

# bcrypt faqat 72 BAYTni qabul qiladi (bcrypt 5 undan uzunida ValueError beradi).
# Kirill harfi 2 bayt, shuning uchun belgilar soni emas, baytlar tekshiriladi.
MAX_PASSWORD_BYTES = 72


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
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Parol {MAX_PASSWORD_BYTES} baytdan oshmasligi kerak")
        return value


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
