"""
LangGraph agent that powers the conversational Log Interaction tab.

Graph shape:

    router --> one of [log_interaction, edit_interaction, get_hcp_profile,
                        schedule_follow_up, search_interactions, direct_reply]
            --> responder --> END

The router node classifies intent with the LLM. Each tool node calls the
matching function in agent/tools.py against the current DB session, then
hands off to the responder node which turns the tool's raw result into a
natural-language reply plus a `preview` dict the frontend renders as a card.
"""
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.agent.state import AgentState
from app.agent.llm import extract_json, chat
from app.agent import tools as T

# In-memory per-session scratchpad: last interaction id touched, for
# "edit that follow-up date" style follow-ups. Keyed by session_id.
_SESSION_MEMORY: dict[str, dict] = {}


def _router_node(state: AgentState) -> AgentState:
    system = (
        "Classify the field rep's message into exactly one intent: "
        "'log' (logging a new HCP interaction), "
        "'edit' (correcting/modifying an interaction just discussed), "
        "'profile' (asking about an HCP's history/profile), "
        "'follow_up' (scheduling a follow-up/reminder), "
        "'search' (looking up past interactions with filters), or "
        "'chat' (anything else, e.g. greetings, questions about the CRM). "
        "Return JSON: {\"intent\": \"...\"}"
    )
    result = extract_json(system, state["message"])
    state["intent"] = result.get("intent", "chat")
    return state


def _log_node(state: AgentState, db: Session) -> AgentState:
    result = T.log_interaction(db, raw_text=state["message"])
    state["tool_used"] = "log_interaction"
    if result["status"] == "success":
        _SESSION_MEMORY.setdefault(state["session_id"], {})["last_interaction_id"] = result["interaction_id"]
        state["last_interaction_id"] = result["interaction_id"]
        state["preview"] = result["record"]
        state["reply"] = result["message"]
    else:
        state["needs_clarification"] = True
        state["reply"] = result["message"]
    return state


def _edit_node(state: AgentState, db: Session) -> AgentState:
    interaction_id = state.get("last_interaction_id") or _SESSION_MEMORY.get(
        state["session_id"], {}
    ).get("last_interaction_id")
    state["tool_used"] = "edit_interaction"
    if not interaction_id:
        state["reply"] = "I don't have a recent interaction in this conversation to edit — which one do you mean?"
        state["needs_clarification"] = True
        return state
    result = T.edit_interaction(db, interaction_id=interaction_id, raw_text=state["message"])
    state["preview"] = result.get("record")
    state["reply"] = result["message"]
    return state


def _profile_node(state: AgentState, db: Session) -> AgentState:
    system = "Extract the HCP name being asked about. Return JSON: {\"hcp_name\": \"...\"}"
    parsed = extract_json(system, state["message"])
    result = T.get_hcp_profile(db, hcp_name=parsed.get("hcp_name"))
    state["tool_used"] = "get_hcp_profile"
    if result["status"] != "success":
        state["reply"] = result["message"]
        return state
    state["preview"] = result
    summary = chat(
        "Summarize this HCP profile and recent interaction history for a sales rep in 2-3 "
        "friendly sentences.",
        str(result),
    )
    state["reply"] = summary
    return state


def _follow_up_node(state: AgentState, db: Session) -> AgentState:
    system = (
        "Extract fields for scheduling a follow-up: hcp_name, due_date_text "
        "(raw phrase like 'next Monday'), reason. Return JSON with those keys."
    )
    parsed = extract_json(system, state["message"])
    result = T.schedule_follow_up(
        db,
        hcp_name=parsed.get("hcp_name"),
        due_date_text=parsed.get("due_date_text"),
        reason=parsed.get("reason"),
        interaction_id=_SESSION_MEMORY.get(state["session_id"], {}).get("last_interaction_id"),
    )
    state["tool_used"] = "schedule_follow_up"
    state["reply"] = result["message"]
    return state


def _search_node(state: AgentState, db: Session) -> AgentState:
    result = T.search_interactions(db, query_text=state["message"])
    state["tool_used"] = "search_interactions"
    state["preview"] = result
    state["reply"] = chat(
        "Summarize these search results for a sales rep in 2-3 sentences, mentioning count "
        "and any standout pattern.",
        str(result),
    )
    return state


def _direct_reply_node(state: AgentState, db: Session) -> AgentState:
    state["tool_used"] = None
    state["reply"] = chat(
        "You are a helpful assistant inside a life-sciences CRM's HCP interaction logger. "
        "Answer briefly and steer the rep toward logging/editing interactions, checking "
        "HCP profiles, scheduling follow-ups, or searching past interactions.",
        state["message"],
    )
    return state


def _route_decision(state: AgentState) -> str:
    return state.get("intent", "chat")


def build_graph(db: Session):
    """Builds a fresh graph bound to the given DB session (per-request)."""
    graph = StateGraph(AgentState)

    graph.add_node("router", _router_node)
    graph.add_node("log", lambda s: _log_node(s, db))
    graph.add_node("edit", lambda s: _edit_node(s, db))
    graph.add_node("profile", lambda s: _profile_node(s, db))
    graph.add_node("follow_up", lambda s: _follow_up_node(s, db))
    graph.add_node("search", lambda s: _search_node(s, db))
    graph.add_node("chat", lambda s: _direct_reply_node(s, db))

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        _route_decision,
        {
            "log": "log",
            "edit": "edit",
            "profile": "profile",
            "follow_up": "follow_up",
            "search": "search",
            "chat": "chat",
        },
    )
    for node in ["log", "edit", "profile", "follow_up", "search", "chat"]:
        graph.add_edge(node, END)

    return graph.compile()


def run_agent(db: Session, session_id: str, message: str) -> AgentState:
    remembered = _SESSION_MEMORY.get(session_id, {})
    initial_state: AgentState = {
        "session_id": session_id,
        "message": message,
        "last_interaction_id": remembered.get("last_interaction_id"),
        "needs_clarification": False,
    }
    app = build_graph(db)
    return app.invoke(initial_state)
