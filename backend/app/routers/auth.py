from fastapi import APIRouter, Depends, Request, Response, status
from sqlmodel import Session as DBSession
from sqlmodel import select

from .. import schemas
from ..auth import (
    create_session,
    current_token_hash,
    destroy_session,
    get_current_user,
    revoke_all_sessions,
    revoke_other_sessions,
)
from ..config import settings
from ..db import get_session
from ..errors import api_error
from ..models import User
from ..ratelimit import limiter
from ..security import dummy_verify, hash_password, needs_rehash, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
@limiter.limit(settings.rate_limit_register)
def register(request: Request, creds: schemas.Credentials, response: Response,
             db: DBSession = Depends(get_session)):
    if not settings.allow_registration:
        raise api_error(status.HTTP_403_FORBIDDEN, "registration_closed",
                        "O cadastro está fechado nesta instalação")
    exists = db.exec(select(User).where(User.username == creds.username)).first()
    if exists:
        raise api_error(status.HTTP_409_CONFLICT, "username_taken", "Nome de usuário já existe")
    user = User(username=creds.username, password_hash=hash_password(creds.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    create_session(db, user.id, response)
    return schemas.UserOut(id=user.id, username=user.username)


@router.post("/login", response_model=schemas.UserOut)
@limiter.limit(settings.rate_limit_login)
def login(request: Request, creds: schemas.Credentials, response: Response,
          db: DBSession = Depends(get_session)):
    user = db.exec(select(User).where(User.username == creds.username)).first()
    if not user:
        dummy_verify(creds.password)
        raise api_error(status.HTTP_401_UNAUTHORIZED, "invalid_credentials",
                        "Usuário ou senha inválidos")
    if not verify_password(creds.password, user.password_hash):
        raise api_error(status.HTTP_401_UNAUTHORIZED, "invalid_credentials",
                        "Usuário ou senha inválidos")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(creds.password)
        db.add(user)
        db.commit()
    create_session(db, user.id, response)
    return schemas.UserOut(id=user.id, username=user.username)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DBSession = Depends(get_session)):
    destroy_session(db, request, response)


@router.post("/change-password", status_code=204)
def change_password(request: Request, body: schemas.PasswordChange,
                    db: DBSession = Depends(get_session),
                    user: User = Depends(get_current_user)):
    if not verify_password(body.current_password, user.password_hash):
        raise api_error(status.HTTP_401_UNAUTHORIZED, "invalid_credentials",
                        "Usuário ou senha inválidos")
    user.password_hash = hash_password(body.new_password)
    db.add(user)
    revoke_other_sessions(db, user.id, current_token_hash(request))
    db.commit()


@router.post("/logout-all", status_code=204)
def logout_all(request: Request, response: Response, db: DBSession = Depends(get_session),
               user: User = Depends(get_current_user)):
    revoke_all_sessions(db, user.id)
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")


@router.get("/me", response_model=schemas.UserOut)
def me(user: User = Depends(get_current_user)):
    return schemas.UserOut(id=user.id, username=user.username)
