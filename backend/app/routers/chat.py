from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import schemas
from app.agent.graph import run_agent

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=schemas.ChatResponse)
def chat_endpoint(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    final_state = run_agent(db, session_id=payload.session_id, message=payload.message)
    return schemas.ChatResponse(
        reply=final_state.get("reply", ""),
        tool_used=final_state.get("tool_used"),
        preview=final_state.get("preview"),
    )
