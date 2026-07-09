from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.agent import tools as T

router = APIRouter(prefix="/hcps", tags=["hcps"])


@router.get("", response_model=list[schemas.HCPOut])
def list_hcps(db: Session = Depends(get_db)):
    return db.query(models.HCP).order_by(models.HCP.name).all()


@router.post("", response_model=schemas.HCPOut)
def create_hcp(payload: dict, db: Session = Depends(get_db)):
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    existing = db.query(models.HCP).filter(models.HCP.name.ilike(name)).first()
    if existing:
        return existing
    hcp = models.HCP(
        name=name,
        specialty=payload.get("specialty"),
        hospital=payload.get("hospital"),
        email=payload.get("email"),
        phone=payload.get("phone"),
        preferred_channel=payload.get("preferred_channel", "visit"),
        notes=payload.get("notes"),
    )
    db.add(hcp)
    db.commit()
    db.refresh(hcp)
    return hcp
