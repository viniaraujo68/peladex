from datetime import timedelta

from fastapi import Depends, HTTPException, Request, Response, status
from sqlmodel import Session as DBSession
from sqlmodel import select

from .config import settings
from .db import get_session
from .models import GroupOwner, User, UserSession, utcnow
from .security import hash_token, new_token


def create_session(db: DBSession, user_id: int, response: Response) -> UserSession:
    token = new_token()
    expires_at = utcnow() + timedelta(days=settings.session_ttl_days)
    session = UserSession(token_hash=hash_token(token), user_id=user_id, expires_at=expires_at)
    db.add(session)
    db.commit()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_days * 24 * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
    return session


def current_token_hash(request: Request) -> str | None:
    token = request.cookies.get(settings.session_cookie_name)
    return hash_token(token) if token else None


def destroy_session(db: DBSession, request: Request, response: Response) -> None:
    token_hash = current_token_hash(request)
    if token_hash:
        existing = db.get(UserSession, token_hash)
        if existing:
            db.delete(existing)
            db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")


def revoke_other_sessions(db: DBSession, user_id: int, keep_token_hash: str | None) -> None:
    stmt = select(UserSession).where(UserSession.user_id == user_id)
    for session in db.exec(stmt):
        if session.token_hash != keep_token_hash:
            db.delete(session)


def revoke_all_sessions(db: DBSession, user_id: int) -> None:
    for session in db.exec(select(UserSession).where(UserSession.user_id == user_id)):
        db.delete(session)


def get_current_user(
    request: Request,
    db: DBSession = Depends(get_session),
) -> User:
    token_hash = current_token_hash(request)
    if not token_hash:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    session = db.get(UserSession, token_hash)
    if not session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    if session.expires_at < utcnow():
        db.delete(session)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


def require_owner(
    group_id: int,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_session),
) -> User:
    link = db.exec(
        select(GroupOwner).where(
            GroupOwner.group_id == group_id, GroupOwner.user_id == user.id
        )
    ).first()
    if not link:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not an owner of this group")
    return user
