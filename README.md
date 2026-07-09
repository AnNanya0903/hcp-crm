# AI-First CRM — HCP Module: Log Interaction Screen

A prototype of the **Log Interaction** screen for a life-sciences CRM's Healthcare Professional
(HCP) module. Field reps can log an interaction either through a **structured form** or by
**chatting naturally** with a LangGraph-powered agent — both paths write to the same database
record.

See [`design-doc.md`](./design-doc.md) for the full architecture writeup, the LangGraph agent's
role, and detailed documentation of all five tools.

## What's inside

```
hcp-crm/
├── design-doc.md          ← architecture + agent/tool design doc
├── backend/                ← FastAPI + LangGraph + Groq
│   └── app/
│       ├── agent/
│       │   ├── tools.py    ← the 5 LangGraph tools
│       │   ├── graph.py    ← LangGraph StateGraph wiring
│       │   ├── llm.py      ← Groq client wrapper
│       │   └── state.py
│       ├── routers/        ← /interactions (form) and /chat (conversational) endpoints
│       ├── models.py       ← SQLAlchemy models (Postgres)
│       ├── schemas.py      ← Pydantic request/response + LLM extraction schemas
│       └── main.py
└── frontend/                ← React + Redux Toolkit
    └── src/
        ├── components/      ← StructuredForm, ChatInterface, InteractionsList
        ├── store/            ← Redux slices
        └── api/
```

## The 5 LangGraph Tools

1. **`log_interaction`** *(mandatory)* — creates a new interaction; extracts structured fields
   (HCP, products, topics, sentiment, follow-up) from free text using Groq `gemma2-9b-it`.
2. **`edit_interaction`** *(mandatory)* — modifies an existing interaction via a natural-language
   correction (LLM produces a JSON patch) or a structured payload; keeps an audit log.
3. **`get_hcp_profile`** — fetches an HCP's profile and recent interaction history for context.
4. **`schedule_follow_up`** — creates a follow-up task, parsing relative dates like "next Tuesday".
5. **`search_interactions`** — translates a natural-language query into structured DB filters.

The LangGraph agent (`backend/app/agent/graph.py`) is a `StateGraph` with a **router** node that
classifies intent, one node per tool, and a **responder** step that turns tool output into a
conversational reply plus a JSON `preview` the frontend renders as a card.

## Running it locally



# 1. Start Postgres (Docker)
docker start hcp-crm-pg

# 2. Backend
cd hcp-crm\backend
.\venv\Scripts\Activate.ps1
python seed.py
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd hcp-crm\frontend
npm start

### 2. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in GROQ_API_KEY and DATABASE_URL
python seed.py             # seeds 3 demo HCPs
uvicorn app.main:app --reload --port 8000
```

The API will be live at `http://localhost:8000` (interactive docs at `/docs`).

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

Opens at `http://localhost:3000`. It talks to the backend at `http://localhost:8000` by default
(override with `REACT_APP_API_URL` in a `.env` file).

## Try it

- **Structured Form tab**: pick an HCP, fill in the fields, click "Log Interaction".
- **Conversational tab**: type something like
  *"Just met Dr. Mehta, discussed CardioFlex data, she wants samples and a follow-up next
  Tuesday"* — the agent extracts the record and shows a preview card. Then try
  *"actually make that Friday instead"* to see `edit_interaction` in action, or
  *"what's Dr. Mehta's history?"* to see `get_hcp_profile`.

## Notes on the AI-first design

Both entry points (form and chat) funnel through the same tool functions in
`backend/app/agent/tools.py`, so the intelligence layer — entity resolution against a controlled
product vocabulary, natural-date parsing, summarization, duplicate-safe editing with audit
logging — is shared infrastructure rather than a bolt-on chatbot. See `design-doc.md` §8 for
more on this.
