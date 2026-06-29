from typing import List, Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship, Column
# pyrefly: ignore [missing-import]
from pgvector.sqlalchemy import Vector

# ==========================================
# HALF A: THE CLINICAL LIBRARY (Static)
# ==========================================
class MainTopic(SQLModel, table=True):
    __tablename__ = "main_topics"
    id: Optional[int] = Field(default=None, primary_key=True)
    book_title: str 
    topic_number: str
    title: str
    comprehensive_summary: str
    summary_embedding: List[float] = Field(sa_column=Column(Vector(768)))
    sub_contents: List["SubContent"] = Relationship(back_populates="topic", cascade_delete=True)

class SubContent(SQLModel, table=True):
    __tablename__ = "sub_contents"
    id: Optional[int] = Field(default=None, primary_key=True)
    topic_id: Optional[int] = Field(default=None, foreign_key="main_topics.id", ondelete="CASCADE")
    sub_id: str
    sub_title: str
    content_value: str
    topic: Optional[MainTopic] = Relationship(back_populates="sub_contents")


# ==========================================
# HALF B: THE PATIENT FILE (Lifelong Memory)
# ==========================================
class ChatSessionRecord(SQLModel, table=True):
    __tablename__ = "chat_sessions"
    id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    title: str = Field(default="Therapy Session")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    user: Optional["User"] = Relationship(back_populates="chat_sessions")
    turns: List["ChatTurn"] = Relationship(back_populates="session", cascade_delete=True)

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(primary_key=True)
    
    therapeutic_phase: int = Field(default=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    turns: List["ChatTurn"] = Relationship(back_populates="user", cascade_delete=True)
    hydrated_states: List["HydratedState"] = Relationship(back_populates="user", cascade_delete=True)
    chat_sessions: List["ChatSessionRecord"] = Relationship(back_populates="user", cascade_delete=True)

class ChatTurn(SQLModel, table=True):
    __tablename__ = "chat_turns"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    session_id: Optional[str] = Field(default=None, foreign_key="chat_sessions.id", ondelete="CASCADE", index=True)
    
    turn_number: int 
    role: str # 'user' or 'ai'
    content: str 
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    user: Optional[User] = Relationship(back_populates="turns")
    session: Optional[ChatSessionRecord] = Relationship(back_populates="turns")

class HydratedState(SQLModel, table=True):
    __tablename__ = "hydrated_states"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    
    start_turn: int
    end_turn: int
    state_summary: str 
    state_embedding: List[float] = Field(sa_column=Column(Vector(768)))
    dynamic_instruction: str = Field(default="PHASE 1: This is a new patient. Ask ONE curious, open question to get them talking.")
    
    # --- NEW EMOTIONAL TRACKING FIELDS ---
    emotional_state: str = Field(default="Neutral")
    intensity: float = Field(default=0.0)
    response_mode: str = Field(default="Establish Rapport")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user: Optional[User] = Relationship(back_populates="hydrated_states")