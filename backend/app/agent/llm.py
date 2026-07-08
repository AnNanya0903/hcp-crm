"""
Thin wrapper around the Groq API.

Two helpers:
- chat(): plain conversational completion (router / responder nodes)
- extract_json(): forces the model to return ONLY a JSON object matching a
  given field description, used by log_interaction / edit_interaction /
  search_interactions for structured extraction from free text.
"""
import json
from groq import Groq

from app.config import settings

_client = Groq(api_key=settings.groq_api_key)


def chat(system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    model = model or settings.groq_model_primary
    resp = _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


def extract_json(system_prompt: str, user_prompt: str, model: str | None = None) -> dict:
    """
    Calls the LLM with an instruction to respond with raw JSON only, then
    parses it defensively (models occasionally wrap in ```json fences).
    """
    model = model or settings.groq_model_primary
    full_system = (
        system_prompt
        + "\n\nRespond with ONLY a valid JSON object. No markdown fences, "
        "no preamble, no explanation text."
    )
    resp = _client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": full_system},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )
    raw = resp.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # fallback: try to locate the first {...} block
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end + 1])
        raise
