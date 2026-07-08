"""
The five sales-facing tools available to the LangGraph agent.

Each tool is a plain Python function: (db: Session, **kwargs) -> dict.
They are called directly by the graph nodes in agent/graph.py, which keeps
DB-session handling explicit and simple rather than routing it through
LangGraph's generic ToolNode.
"""
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app import models
from app.agent.llm import extract_json, chat

CONTROLLED_PRODUCTS = [
    "CardioFlex", "Nexivar", "GlucoBalance", "PulmoCare", "OncoShield",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_hcp(db: Session, name: str | None, hcp_id: str | None) -> models.HCP | None:
    if hcp_id:
        return db.query(models.HCP).filter(models.HCP.id == hcp_id).first()
    if name:
        return (
            db.query(models.HCP)
            .filter(models.HCP.name.ilike(f"%{name}%"))
            .first()
        )
    return None


def _parse_relative_date(text: str | None, anchor: datetime | None = None) -> datetime | None:
    if not text:
        return None
    anchor = anchor or datetime.utcnow()
    try:
        return dateparser.parse(text, default=anchor, fuzzy=True)
    except (ValueError, OverflowError):
        return None


# ---------------------------------------------------------------------------
# Tool 1: log_interaction  (mandatory)
# ---------------------------------------------------------------------------

def log_interaction(db: Session, raw_text: str | None = None, structured: dict | None = None) -> dict:
    """
    Create a new interaction record.

    - If `structured` is provided (form submission), it's used directly.
    - If `raw_text` is provided (chat), the LLM extracts structured fields
      first, grounded against the controlled product vocabulary.
    """
    if structured:
        data = structured
        hcp = _resolve_hcp(db, data.get("hcp_name"), data.get("hcp_id"))
    else:
        system = (
            "You are a life-sciences CRM assistant. Extract structured interaction "
            "details from a field rep's free-text note about a meeting/call with a "
            "Healthcare Professional (HCP). Known products: "
            f"{', '.join(CONTROLLED_PRODUCTS)}. "
            "Fields to return: hcp_name, interaction_type (call|visit|email|conference), "
            "products_discussed (list, only from the known products list), "
            "topics (list of short phrases), sentiment (positive|neutral|negative), "
            "samples_distributed (bool), sample_qty (int), follow_up_required (bool), "
            "follow_up_date_text (raw phrase like 'next Tuesday', or null), "
            "summary (1-2 sentence summary), missing_fields (list of any of "
            "[hcp_name, interaction_type] that could not be determined)."
        )
        extracted = extract_json(system, raw_text)
        data = extracted
        hcp = _resolve_hcp(db, extracted.get("hcp_name"), None)

    if hcp is None:
        return {
            "status": "needs_clarification",
            "message": "I couldn't identify which HCP this interaction is with. "
                       "Could you confirm the HCP's name?",
        }
    if not data.get("interaction_type"):
        return {
            "status": "needs_clarification",
            "message": "What type of interaction was this — call, visit, email, or conference?",
        }

    follow_up_date = data.get("follow_up_date")
    if not follow_up_date and data.get("follow_up_date_text"):
        follow_up_date = _parse_relative_date(data["follow_up_date_text"])

    interaction = models.Interaction(
        hcp_id=hcp.id,
        interaction_type=data.get("interaction_type", "call"),
        interaction_date=data.get("interaction_date") or datetime.utcnow(),
        products_discussed=[p for p in data.get("products_discussed", []) if p in CONTROLLED_PRODUCTS],
        topics=data.get("topics", []),
        sentiment=data.get("sentiment") or "neutral",
        samples_distributed=bool(data.get("samples_distributed", False)),
        sample_qty=int(data.get("sample_qty") or 0),
        follow_up_required=bool(data.get("follow_up_required", False)),
        follow_up_date=follow_up_date,
        summary=data.get("summary"),
        raw_input=raw_text,
        source="chat" if raw_text else "form",
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    return {
        "status": "success",
        "interaction_id": interaction.id,
        "record": _interaction_to_dict(interaction),
        "message": f"Logged {interaction.interaction_type} with {hcp.name}.",
    }


# ---------------------------------------------------------------------------
# Tool 2: edit_interaction  (mandatory)
# ---------------------------------------------------------------------------

def edit_interaction(db: Session, interaction_id: str, raw_text: str | None = None,
                      structured_patch: dict | None = None) -> dict:
    """
    Modify an existing interaction. Accepts either an explicit structured
    patch (form edit) or a natural-language correction (chat), in which case
    the LLM produces a JSON patch against the existing record.
    """
    interaction = db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
    if not interaction:
        return {"status": "error", "message": "Interaction not found."}

    if structured_patch:
        patch = structured_patch
    else:
        current = _interaction_to_dict(interaction)
        system = (
            "You are a CRM assistant. Given the CURRENT interaction record (JSON) and a "
            "rep's natural-language correction, output ONLY a JSON patch object containing "
            "the fields that should change and their new values. Do not include unchanged "
            "fields. Valid fields: interaction_type, products_discussed, topics, sentiment, "
            "samples_distributed, sample_qty, follow_up_required, follow_up_date_text, summary."
        )
        user = f"CURRENT RECORD:\n{current}\n\nCORRECTION:\n{raw_text}"
        patch = extract_json(system, user)

    diffs = []
    for field, new_value in patch.items():
        if field == "follow_up_date_text":
            new_value = _parse_relative_date(new_value, interaction.interaction_date)
            field = "follow_up_date"
        if not hasattr(interaction, field):
            continue
        old_value = getattr(interaction, field)
        if str(old_value) == str(new_value):
            continue
        db.add(models.InteractionAuditLog(
            interaction_id=interaction.id,
            field=field,
            old_value=str(old_value),
            new_value=str(new_value),
        ))
        setattr(interaction, field, new_value)
        diffs.append(f"{field}: {old_value} → {new_value}")

    interaction.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(interaction)

    return {
        "status": "success",
        "interaction_id": interaction.id,
        "record": _interaction_to_dict(interaction),
        "diffs": diffs,
        "message": "Updated: " + "; ".join(diffs) if diffs else "No changes detected.",
    }


# ---------------------------------------------------------------------------
# Tool 3: get_hcp_profile
# ---------------------------------------------------------------------------

def get_hcp_profile(db: Session, hcp_name: str | None = None, hcp_id: str | None = None) -> dict:
    hcp = _resolve_hcp(db, hcp_name, hcp_id)
    if not hcp:
        return {"status": "not_found", "message": f"No HCP found matching '{hcp_name}'."}

    recent = (
        db.query(models.Interaction)
        .filter(models.Interaction.hcp_id == hcp.id)
        .order_by(models.Interaction.interaction_date.desc())
        .limit(5)
        .all()
    )
    open_follow_ups = (
        db.query(models.FollowUp)
        .filter(models.FollowUp.hcp_id == hcp.id, models.FollowUp.status == "open")
        .all()
    )

    return {
        "status": "success",
        "hcp": {
            "id": hcp.id, "name": hcp.name, "specialty": hcp.specialty,
            "hospital": hcp.hospital, "preferred_channel": hcp.preferred_channel,
        },
        "recent_interactions": [_interaction_to_dict(i) for i in recent],
        "open_follow_ups": [
            {"id": f.id, "due_date": str(f.due_date), "reason": f.reason} for f in open_follow_ups
        ],
    }


# ---------------------------------------------------------------------------
# Tool 4: schedule_follow_up
# ---------------------------------------------------------------------------

def schedule_follow_up(db: Session, hcp_name: str | None = None, hcp_id: str | None = None,
                        due_date_text: str | None = None, reason: str | None = None,
                        interaction_id: str | None = None) -> dict:
    hcp = _resolve_hcp(db, hcp_name, hcp_id)
    if not hcp:
        return {"status": "needs_clarification", "message": "Which HCP is this follow-up for?"}

    due_date = _parse_relative_date(due_date_text) or (datetime.utcnow() + timedelta(days=7))

    follow_up = models.FollowUp(
        hcp_id=hcp.id,
        interaction_id=interaction_id,
        due_date=due_date,
        reason=reason or "Follow-up",
        status="open",
    )
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)

    return {
        "status": "success",
        "follow_up_id": follow_up.id,
        "message": f"Follow-up with {hcp.name} scheduled for {due_date.strftime('%b %d, %Y')}.",
    }


# ---------------------------------------------------------------------------
# Tool 5: search_interactions
# ---------------------------------------------------------------------------

def search_interactions(db: Session, query_text: str) -> dict:
    system = (
        "Translate the rep's natural-language search request into a JSON filter object "
        "with optional keys: hcp_name (string), date_from (ISO date), date_to (ISO date), "
        "product (string, one of: " + ", ".join(CONTROLLED_PRODUCTS) + "), "
        "sentiment (positive|neutral|negative). Omit keys that don't apply."
    )
    filters = extract_json(system, query_text)

    q = db.query(models.Interaction).join(models.HCP)
    if filters.get("hcp_name"):
        q = q.filter(models.HCP.name.ilike(f"%{filters['hcp_name']}%"))
    if filters.get("date_from"):
        q = q.filter(models.Interaction.interaction_date >= filters["date_from"])
    if filters.get("date_to"):
        q = q.filter(models.Interaction.interaction_date <= filters["date_to"])
    if filters.get("sentiment"):
        q = q.filter(models.Interaction.sentiment == filters["sentiment"])
    if filters.get("product"):
        q = q.filter(models.Interaction.products_discussed.contains([filters["product"]]))

    results = q.order_by(models.Interaction.interaction_date.desc()).limit(20).all()
    return {
        "status": "success",
        "filters_used": filters,
        "count": len(results),
        "results": [_interaction_to_dict(i) for i in results],
    }


# ---------------------------------------------------------------------------

def _interaction_to_dict(i: models.Interaction) -> dict:
    return {
        "id": i.id,
        "hcp_id": i.hcp_id,
        "interaction_type": str(i.interaction_type.value if hasattr(i.interaction_type, "value") else i.interaction_type),
        "interaction_date": str(i.interaction_date),
        "products_discussed": i.products_discussed or [],
        "topics": i.topics or [],
        "sentiment": str(i.sentiment.value if hasattr(i.sentiment, "value") else i.sentiment),
        "samples_distributed": i.samples_distributed,
        "sample_qty": i.sample_qty,
        "follow_up_required": i.follow_up_required,
        "follow_up_date": str(i.follow_up_date) if i.follow_up_date else None,
        "summary": i.summary,
        "source": str(i.source.value if hasattr(i.source, "value") else i.source),
    }
