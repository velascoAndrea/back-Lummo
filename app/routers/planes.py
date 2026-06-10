from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Plan
from ..schemas import PlanOut

router = APIRouter(prefix="/planes", tags=["planes"])


@router.get("", response_model=list[PlanOut])
def get_planes(
    nivel_global: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    planes = db.query(Plan).filter(Plan.activo == True).all()
    result = []
    for p in planes:
        result.append(PlanOut(
            id=p.id,
            nombre=p.nombre,
            precio_mensual=p.precio_mensual,
            precio_anual=p.precio_anual,
            nivel_recomendado=p.nivel_recomendado,
            descripcion=p.descripcion,
            recomendado=(p.nivel_recomendado == nivel_global) if nivel_global else False,
        ))
    return result
