from apps.forms import RegisterForm, LoginForm, Token, RefreshTokenRequest
from apps.models import User
from apps.utils import create_access_and_refresh_tokens, verify_token
from apps.views.main import app, SessionDep


@app.post('/user/register')
async def register(register_form : RegisterForm , session: SessionDep):
    instance = User(**register_form.__dict__)
    session.add(instance)

    session.commit()
    return {"message" : "Success create!" , "status":201}

@app.post('/user/login')
async def login(login_form : LoginForm ):
    access , refresh = create_access_and_refresh_tokens(login_form.username)
    return Token(access_token=access, token_type="bearer" , refresh_token=refresh)

@app.post("/refresh", response_model=Token)
async def refresh_access_token(request: RefreshTokenRequest):
    username = verify_token(request.refresh_token, token_type="refresh")
    access_token, refresh_token = create_access_and_refresh_tokens(username)
    return Token(access_token=access_token,refresh_token=refresh_token, token_type='bearer')
