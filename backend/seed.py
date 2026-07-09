"""Run once to populate demo HCPs and interactions: `python seed.py`"""
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal, Base, engine
from app import models

Base.metadata.create_all(bind=engine)
db = SessionLocal()

demo_hcps = [
    dict(name="Dr. Ananya Mehta", specialty="Cardiology", hospital="City General Hospital",
         email="a.mehta@citygeneral.example", phone="+91-9000000001", preferred_channel="visit"),
    dict(name="Dr. Rohan Kapoor", specialty="Endocrinology", hospital="Sunrise Clinic",
         email="r.kapoor@sunrise.example", phone="+91-9000000002", preferred_channel="call"),
    dict(name="Dr. Priya Nair", specialty="Pulmonology", hospital="Lakeview Medical Center",
         email="p.nair@lakeview.example", phone="+91-9000000003", preferred_channel="email"),
]

hcps = {}
for h in demo_hcps:
    exists = db.query(models.HCP).filter(models.HCP.name == h["name"]).first()
    if not exists:
        hcp = models.HCP(**h)
        db.add(hcp)
        db.flush()
        hcps[h["name"]] = hcp
    else:
        hcps[h["name"]] = exists

db.commit()

now = datetime.now(timezone.utc)


def add_interaction(hcp_name, interaction_type, products, topics, sentiment, samples, sample_qty, follow_up_days, summary, source="form"):
    hcp = hcps.get(hcp_name)
    if not hcp:
        return
    exists = (
        db.query(models.Interaction)
        .filter(
            models.Interaction.hcp_id == hcp.id,
            models.Interaction.interaction_type == interaction_type,
            models.Interaction.summary == summary,
            models.Interaction.source == source,
        )
        .first()
    )
    if exists:
        return
    row = models.Interaction(
        hcp_id=hcp.id,
        interaction_type=interaction_type,
        interaction_date=now - timedelta(days=follow_up_days),
        products_discussed=products,
        topics=topics,
        sentiment=sentiment,
        samples_distributed=samples,
        sample_qty=sample_qty,
        follow_up_required=follow_up_days is not None,
        follow_up_date=(now + timedelta(days=follow_up_days)).isoformat() if follow_up_days is not None else None,
        summary=summary,
        source=source,
    )
    db.add(row)


add_interaction(
    "Dr. Ananya Mehta",
    "visit",
    ["CardioFlex"],
    ["clinical data"],
    "positive",
    True,
    5,
    7,
    "Discussed latest CardioFlex trial results. Dr. Mehta wants more samples for her clinic.",
)

add_interaction(
    "Dr. Rohan Kapoor",
    "call",
    ["Nexivar"],
    ["dosing questions", "new trial data"],
    "neutral",
    False,
    0,
    3,
    "Quick call about Nexivar dosing; promised to send updated protocol PDF.",
)

add_interaction(
    "Dr. Priya Nair",
    "conference",
    ["PulmoCare"],
    ["new clinical trial results", "dosage for COPD patients"],
    "positive",
    True,
    2,
    14,
    "Met at respiratory conference. She asked about efficacy vs competitor and requested samples.",
)

db.commit()
db.close()
print("Seeded demo HCPs and interactions.")
