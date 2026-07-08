# AI-First CRM — HCP Module: Log Interaction Screen
### Design Document

## 1. Objective & Mindset

Field reps meet Healthcare Professionals (HCPs) under time pressure — in hallways, between
surgeries, over five-minute calls. The single biggest failure mode of traditional CRM tools is
that logging the interaction feels like a *second job*: ten dropdowns, three tabs, forget-and-
never-do-it-again. An AI-first CRM should let the rep talk (or type) the way they'd talk to a
colleague — *"Just met Dr. Mehta, discussed the new cardiology data, she wants samples and a
follow-up next month"* — and have the system do the structuring, coding, and filing.

That's the lens for this design: the LLM/agent is not a chatbot bolted onto a CRM. It **is** the
data-entry layer. The structured form still exists (compliance teams and power users want it),
but it's a peer input mode to the conversation, not the primary one — both write to the same
underlying record.

## 2. Tech Stack

| Layer | Choice |
|---|---|
| Frontend | React + Redux (Redux Toolkit) |
| Backend | Python, FastAPI |
| Agent framework | LangGraph |
| LLM | Groq `gemma2-9b-it` (primary), `llama-3.3-70b-versatile` (fallback / heavier reasoning) |
| Database | PostgreSQL (SQLAlchemy ORM) |
| Font | Google Inter |

## 3. Log Interaction Screen — UX

Single screen, two tabs sharing one Redux slice and one backend record shape:

- **Structured Form tab** — HCP selector, interaction type (call / visit / email / conference),
  date, products discussed, topics, sentiment, samples given, follow-up toggle + date, free-text
  notes.
- **Conversational tab** — chat box. The rep dictates/types naturally. The agent asks
  clarifying questions only for fields it can't infer ("Which products did you discuss?") and
  shows a live-updating **preview card** of the structured record it's building, so the rep can
  see the form filling itself in real time before confirming.

Both tabs submit to the same `POST /interactions` → LangGraph agent pipeline, so a structured
submission still passes through the agent for entity-linking/validation, and a conversational
submission ends up as the exact same row in Postgres.

## 4. Role of the LangGraph Agent

The LangGraph agent is the **orchestration brain** sitting behind both entry modes. Concretely
it:

1. **Routes intent** — on every chat turn it classifies whether the rep wants to log a new
   interaction, edit/correct one just logged, look up an HCP's history, or schedule a follow-up,
   and picks the right tool.
2. **Extracts structure from unstructured speech** — turns a rambling paragraph into
   `hcp_id, interaction_type, products_discussed[], topics[], sentiment, follow_up_date` using
   the LLM node for entity extraction + summarization.
3. **Grounds itself in real data** — before writing anything, it calls `get_hcp_profile` so it
   never invents an HCP or mis-links an interaction; it uses that profile as tool-context for
   the LLM node.
4. **Holds a short-term conversational state** (LangGraph's checkpointer) so "actually make that
   next Tuesday, not Monday" resolves against the interaction it just created, without the rep
   repeating the whole context.
5. **Enforces guardrails** — refuses to log clinical claims outside label, flags missing
   mandatory fields, and always returns a structured JSON object the frontend can render as a
   preview card before final save (human-in-the-loop confirmation, important in a life-sciences
   compliance context).

Graph shape (LangGraph):

```
        ┌─────────────┐
        │   router    │  (LLM classifies intent → chooses tool)
        └──────┬──────┘
               │
   ┌───────────┼─────────────┬─────────────────┬──────────────────┐
   ▼           ▼              ▼                 ▼                  ▼
log_interaction edit_interaction get_hcp_profile schedule_follow_up search_interactions
   │           │              │                 │                  │
   └───────────┴──────────────┴────────┬────────┴──────────────────┘
                                        ▼
                               ┌─────────────────┐
                               │ responder node   │ (formats reply + preview card)
                               └─────────────────┘
```

## 5. The Five Tools

### 5.1 `log_interaction` (mandatory)

**Purpose:** Create a new HCP interaction record from either free text (chat) or a structured
payload (form).

**How it captures data:**
- Input: raw rep text (chat) *or* a pre-filled JSON (form).
- If raw text: the LLM node (Groq `gemma2-9b-it`) runs a **structured-extraction prompt**
  against a Pydantic schema (`InteractionExtract`), pulling out:
  - `hcp_name` → resolved to `hcp_id` via fuzzy match against the `hcps` table
  - `interaction_type` (call/visit/email/conference)
  - `products_discussed[]`, `topics[]` (entity extraction, matched against a controlled
    vocabulary table so the LLM can't invent product names)
  - `sentiment` (positive/neutral/negative — short classification pass)
  - `samples_distributed` (bool + qty if mentioned)
  - `follow_up_required` (bool) + `follow_up_date` (parsed from relative dates like "next
    Tuesday" using the interaction date as anchor)
  - `summary` — a 1–2 sentence LLM-generated summary of the whole interaction, stored alongside
    the raw text for audit purposes
- The tool validates the extraction against the Pydantic schema; if required fields are still
  missing (most commonly `hcp_id` or `interaction_type`), it returns a `needs_clarification`
  status back to the router instead of writing to the DB, and the agent asks one targeted
  follow-up question.
- On success: writes a row to `interactions`, returns the created record for the frontend
  preview card.

### 5.2 `edit_interaction` (mandatory)

**Purpose:** Modify a previously logged interaction — via chat correction or the form's edit
mode.

**How it works:**
- Input: `interaction_id` (resolved from conversation state if the rep says "actually, change
  that…", or passed explicitly by the frontend edit button) + a natural-language delta *or* a
  partial structured payload.
- If natural language ("change the follow-up to next Friday instead"): the LLM node runs a
  **diff-extraction prompt** — given the existing record as context, it identifies which
  field(s) changed and to what value, producing a JSON patch (`{"follow_up_date": "2026-07-17"}`)
  rather than re-extracting the whole record. This avoids accidentally overwriting untouched
  fields.
- The tool applies the patch via SQLAlchemy, stamps `updated_at` and `edited_by`, and keeps the
  previous value in an `interaction_audit_log` table (compliance requirement — HCP interaction
  records are frequently audited).
- Returns the updated record + a diff summary ("Follow-up moved from Mon Jul 13 → Fri Jul 17")
  for the frontend to render as a confirmation toast.

### 5.3 `get_hcp_profile`

**Purpose:** Fetch an HCP's profile and recent interaction history so the agent (and rep) has
context before/while logging — prevents duplicate/contradictory entries and lets the LLM
personalize summaries ("as discussed last visit…").

- Input: `hcp_name` or `hcp_id`.
- Returns: specialty, hospital/institution, contact preferences, last 5 interactions
  (date/type/summary), open follow-ups, products of interest.
- Used automatically by `log_interaction` and `edit_interaction` as grounding context, and
  directly callable by the rep ("what did we last discuss with Dr. Mehta?").

### 5.4 `schedule_follow_up`

**Purpose:** Create/update a follow-up task tied to an interaction, independent of the main log
(so follow-ups can be rescheduled without touching the interaction record itself).

- Input: `hcp_id`, `due_date` (accepts relative language, resolved via the LLM's date-parsing
  pass), `reason`, optional `interaction_id` link.
- Writes to a `follow_ups` table; returns the created task. Enables a "My Follow-ups Today"
  widget elsewhere in the CRM (out of scope for this screen but a natural extension).

### 5.5 `search_interactions`

**Purpose:** Sales-rep-facing recall — "show me everything with Dr. Mehta this quarter", "which
HCPs haven't I visited in 60 days".

- Input: free-text query; the LLM node translates it into structured filters
  (`hcp_id?, date_from?, date_to?, product?, sentiment?`) against a lightweight filter schema.
- Executes a parameterized SQL query (never LLM-generated raw SQL, to avoid injection/hallucinated
  queries) and returns matching rows, which the responder node summarizes conversationally.

## 6. Data Model (Postgres)

- `hcps(id, name, specialty, hospital, email, phone, preferred_channel, notes, created_at)`
- `interactions(id, hcp_id FK, rep_id, interaction_type, interaction_date, products_discussed JSONB,
  topics JSONB, sentiment, samples_distributed, sample_qty, follow_up_required, follow_up_date,
  summary, raw_input, source ENUM[form,chat], created_at, updated_at)`
- `follow_ups(id, hcp_id FK, interaction_id FK nullable, due_date, reason, status, created_at)`
- `interaction_audit_log(id, interaction_id FK, field, old_value, new_value, edited_at)`

## 7. API Surface (FastAPI)

- `POST /interactions` — create (form path; internally calls the agent's `log_interaction` tool)
- `PATCH /interactions/{id}` — edit (form path; calls `edit_interaction`)
- `GET /interactions` — list/filter
- `GET /hcps/{id}` — profile
- `POST /chat` — conversational entrypoint; body `{session_id, message}`, runs the LangGraph
  agent end-to-end, returns `{reply, preview, tool_used}`

## 8. Why this satisfies "AI-first"

Every write path — form or chat — passes through the same LangGraph agent and the same LLM
extraction/validation logic, rather than the AI being a sidebar feature. The form exists for
speed and compliance familiarity; the intelligence layer (entity resolution, summarization,
duplicate/conflict detection, natural date parsing) is shared infrastructure underneath both.
