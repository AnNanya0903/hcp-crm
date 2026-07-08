from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import schemas
from app.agent import tools as T

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("", response_model=None)
def create_interaction(payload: schemas.InteractionCreate, db: Session = Depends(get_db)):
    result = T.log_interaction(db, structured=payload.model_dump())
    if result["status"] != "success":
        raise HTTPException(status_code=422, detail=result["message"])
    return result


@router.patch("/{interaction_id}", response_model=None)
def edit_interaction(interaction_id: str, payload: schemas.InteractionUpdate, db: Session = Depends(get_db)):
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    result = T.edit_interaction(db, interaction_id=interaction_id, structured_patch=patch)
    if result["status"] != "success":
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.get("", response_model=None)
def list_interactions(hcp_id: str | None = None, db: Session = Depends(get_db)):
    from app import models
    q = db.query(models.Interaction)
    if hcp_id:
        q = q.filter(models.Interaction.hcp_id == hcp_id)
    rows = q.order_by(models.Interaction.interaction_date.desc()).limit(100).all()
    return [T._interaction_to_dict(r) for r in rows]


@router.get("/hcps", response_model=list[schemas.HCPOut])
def list_hcps(db: Session = Depends(get_db)):
    from app import models
    return db.query(models.HCP).order_by(models.HCP.name).all()
