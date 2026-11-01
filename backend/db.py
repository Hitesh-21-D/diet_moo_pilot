import json
import os
import time
import uuid
from pathlib import Path
from sqlalchemy import create_engine, String, Float, JSON, ForeignKey, Text, BigInteger, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parent.parent
settings = ROOT/'.local'/'app-settings.json'
DATABASE_URL = os.environ.get('DIETLAB_DATABASE_URL') or (json.loads(settings.read_text())['database_url'] if settings.exists() else 'postgresql+psycopg://dietlab@127.0.0.1:5433/dietlab')
engine = create_engine(DATABASE_URL, pool_pre_ping=True, **({'connect_args': {'check_same_thread': False}} if DATABASE_URL.startswith('sqlite') else {}))
if DATABASE_URL.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, record):
        connection.execute('PRAGMA foreign_keys=ON')
SessionLocal = sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def uid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(Text)
    created: Mapped[float] = mapped_column(Float, default=time.time)

class LoginSession(Base):
    __tablename__ = 'sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    expires: Mapped[float] = mapped_column(Float)

class Profile(Base):
    __tablename__ = 'profiles'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    updated: Mapped[float] = mapped_column(Float, default=time.time)

class Submission(Base):
    __tablename__ = 'submissions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    title: Mapped[str] = mapped_column(String(120))
    created: Mapped[float] = mapped_column(Float, default=time.time)

class DietDay(Base):
    __tablename__ = 'diet_days'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    submission_id: Mapped[str] = mapped_column(ForeignKey('submissions.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    label: Mapped[str] = mapped_column(String(100))
    date: Mapped[str] = mapped_column(String(10))
    diet: Mapped[dict] = mapped_column(JSON)
    updated: Mapped[float] = mapped_column(Float, default=time.time)

class Experiment(Base):
    __tablename__ = 'experiments'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True)
    day_id: Mapped[str] = mapped_column(ForeignKey('diet_days.id', ondelete='CASCADE'), index=True)
    label: Mapped[str] = mapped_column(String(100))
    created: Mapped[float] = mapped_column(Float, default=time.time)
    snapshot: Mapped[dict] = mapped_column(JSON)
    comparison: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)

class Run(Base):
    __tablename__ = 'runs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    experiment_id: Mapped[str] = mapped_column(ForeignKey('experiments.id', ondelete='CASCADE'), index=True)
    algorithm: Mapped[str] = mapped_column(String(40))
    seed: Mapped[int] = mapped_column(BigInteger)
    budget: Mapped[int]
    status: Mapped[str] = mapped_column(String(24), default='queued', index=True)
    progress: Mapped[int] = mapped_column(default=0)
    created: Mapped[float] = mapped_column(Float, default=time.time)
    started: Mapped[float | None] = mapped_column(Float, nullable=True)
    finished: Mapped[float | None] = mapped_column(Float, nullable=True)
    heartbeat: Mapped[float | None] = mapped_column(Float, nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON(none_as_null=True), nullable=True)

def get_db():
    with SessionLocal() as db:
        yield db
