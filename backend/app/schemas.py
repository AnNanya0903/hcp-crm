from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class HCPOut(BaseModel):
    id: str
    name: str
    specialty: Optional[str] = None
    hospital: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    preferred_channel: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class InteractionCreate(BaseModel):
    hcp_id: Optional[str] = None
    hcp_name: Optional[str] = None
    interaction_type: str = Field(description="call | visit | email | conference")
    interaction_date: Optional[datetime] = None
    products_discussed: list[str] = []
    topics: list[str] = []
    sentiment: str = "neutral"
    samples_distributed: bool = False
    sample_qty: int = 0
    follow_up_required: bool = False
    follow_up_date: Optional[datetime] = None
    summary: Optional[str] = None
    raw_input: Optional[str] = None
    source: str = "form"


class InteractionUpdate(BaseModel):
    interaction_type: Optional[str] = None
    products_discussed: Optional[list[str]] = None
    topics: Optional[list[str]] = None
    sentiment: Optional[str] = None
    samples_distributed: Optional[bool] = None
    sample_qty: Optional[int] = None
    follow_up_required: Optional[bool] = None
    follow_up_date: Optional[datetime] = None
    summary: Optional[str] = None


class InteractionOut(BaseModel):
    id: str
    hcp_id: str
    interaction_type: str
    interaction_date: datetime
    products_discussed: list[str]
    topics: list[str]
    sentiment: str
    samples_distributed: bool
    sample_qty: int
    follow_up_required: bool
    follow_up_date: Optional[datetime] = None
    summary: Optional[str] = None
    source: str

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    tool_used: Optional[str] = None
    preview: Optional[dict] = None


# --- LLM structured-extraction targets (used inside agent/tools.py) ---

class InteractionExtract(BaseModel):
    hcp_name: Optional[str] = None
    interaction_type: Optional[str] = None
    products_discussed: list[str] = []
    topics: list[str] = []
    sentiment: Optional[str] = None
    samples_distributed: bool = False
    sample_qty: int = 0
    follow_up_required: bool = False
    follow_up_date_text: Optional[str] = None  # raw relative text e.g. "next Tuesday"
    summary: Optional[str] = None
    missing_fields: list[str] = []
