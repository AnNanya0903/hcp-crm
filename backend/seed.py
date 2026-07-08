"""Run once to populate demo HCPs: `python seed.py`"""
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

for h in demo_hcps:
    exists = db.query(models.HCP).filter(models.HCP.name == h["name"]).first()
    if not exists:
        db.add(models.HCP(**h))

db.commit()
db.close()
print("Seeded demo HCPs.")
