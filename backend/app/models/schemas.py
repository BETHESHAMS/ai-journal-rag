from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# --- Authentication & User Schemas ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="User password (min 6 characters)")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    created_at: Optional[datetime] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None


# --- Journal Entry Schemas ---

class JournalEntryCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Text of the journal entry")
    entry_date: Optional[date] = Field(default_factory=date.today, description="Date of the journal entry")


class JournalEntryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    entry_date: Optional[date] = None


class JournalEntryResponse(BaseModel):
    id: str
    user_id: str
    content: str
    entry_date: date
    created_at: datetime
    updated_at: datetime


# --- RAG & Chat Schemas ---

class ChatQueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question about past journal entries")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve")


class Citation(BaseModel):
    entry_id: str
    entry_date: str
    snippet: str
    similarity: float


class ChatQueryResponse(BaseModel):
    answer: str
    citations: List[Citation] = []
    provider_used: str
    model_used: str


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
    llm_model: str
    database_configured: bool
