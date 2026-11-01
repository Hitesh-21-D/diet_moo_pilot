import hashlib
import os
import secrets
import time
from collections import defaultdict, deque
from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from backend.db import get_db, LoginSession, User

hasher = PasswordHasher()
COOKIE = 'dietlab_session'
attempts = defaultdict(deque)

def throttle(request):
    key = request.client.host if request.client else 'unknown'
    now = time.time()
    q = attempts[key]
    while q and q[0] < now-60:
        q.popleft()
    if len(q) >= 12:
        raise HTTPException(429, 'Too many attempts. Please wait a minute.')
    q.append(now)

def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()

def create_session(db, user, response):
    token = secrets.token_urlsafe(48)
    db.add(LoginSession(token_hash=token_hash(token), user_id=user.id, expires=time.time()+7*86400))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=7*86400, httponly=True, samesite='strict',
                        secure=os.environ.get('DIETLAB_SECURE_COOKIES') == '1', path='/')

def current_user(request: Request, db: Session = Depends(get_db)):
    session = db.get(LoginSession, token_hash(request.cookies.get(COOKIE, '')))
    if not session or session.expires <= time.time():
        raise HTTPException(401, 'Please sign in to continue')
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(401, 'Session no longer exists')
    return user
