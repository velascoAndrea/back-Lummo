from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Plan, Configuracion
from ..schemas import PlanOut

router = APIRouter(prefix="/planes", tags=["planes"])

TASA_USD_DEFAULT = 7.75


@router.get("/tasa-usd")
def get_tasa_usd(db: Session = Depends(get_db)):
    """Tasa de referencia GTQ → USD, pública, para mostrar precios equivalentes."""
    cfg = db.query(Configuracion).filter(Configuracion.clave == "tasa_usd").first()
    try:
        tasa = float(cfg.valor) if cfg else TASA_USD_DEFAULT
    except (TypeError, ValueError):
        tasa = TASA_USD_DEFAULT
    return {"tasa_usd": tasa}


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
