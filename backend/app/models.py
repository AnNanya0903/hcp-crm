import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, Integer, Enum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class SourceEnum(str, enum.Enum):
    form = "form"
    chat = "chat"


class SentimentEnum(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class InteractionTypeEnum(str, enum.Enum):
    call = "call"
    visit = "visit"
    email = "email"
    conference = "conference"


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False, index=True)
    specialty = Column(String)
    hospital = Column(String)
    email = Column(String)
    phone = Column(String)
    preferred_channel = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="hcp")
    follow_ups = relationship("FollowUp", back_populates="hcp")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    hcp_id = Column(UUID(as_uuid=False), ForeignKey("hcps.id"), nullable=False)
    rep_id = Column(String, default="demo-rep")
    interaction_type = Column(Enum(InteractionTypeEnum), nullable=False)
    interaction_date = Column(DateTime, default=datetime.utcnow)
    products_discussed = Column(JSONB, default=list)
    topics = Column(JSONB, default=list)
    sentiment = Column(Enum(SentimentEnum), default=SentimentEnum.neutral)
    samples_distributed = Column(Boolean, default=False)
    sample_qty = Column(Integer, default=0)
    follow_up_required = Column(Boolean, default=False)
    follow_up_date = Column(DateTime, nullable=True)
    summary = Column(Text)
    raw_input = Column(Text)
    source = Column(Enum(SourceEnum), default=SourceEnum.form)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    hcp_id = Column(UUID(as_uuid=False), ForeignKey("hcps.id"), nullable=False)
    interaction_id = Column(UUID(as_uuid=False), ForeignKey("interactions.id"), nullable=True)
    due_date = Column(DateTime, nullable=False)
    reason = Column(Text)
    status = Column(String, default="open")  # open | done | cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

    hcp = relationship("HCP", back_populates="follow_ups")


class InteractionAuditLog(Base):
    __tablename__ = "interaction_audit_log"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    interaction_id = Column(UUID(as_uuid=False), ForeignKey("interactions.id"), nullable=False)
    field = Column(String)
    old_value = Column(Text)
    new_value = Column(Text)
    edited_at = Column(DateTime, default=datetime.utcnow)
