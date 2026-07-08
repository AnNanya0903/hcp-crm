from typing import Optional, TypedDict, Any


class AgentState(TypedDict, total=False):
    session_id: str
    message: str                 # latest user message
    last_interaction_id: Optional[str]  # for "edit the one I just logged"
    intent: Optional[str]        # log | edit | profile | follow_up | search | chat
    tool_used: Optional[str]
    reply: Optional[str]
    preview: Optional[dict[str, Any]]
    needs_clarification: bool
