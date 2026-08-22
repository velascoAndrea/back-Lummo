"""
Lista de espera de la landing (soylummo.com).

Único endpoint público de escritura sin autenticación, así que lleva sus propios
frenos: normaliza el correo, valida formato, y limita por IP para que no se pueda
llenar la tabla desde un script.
"""
import re
import time
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ListaEspera

router = APIRouter(prefix="/lista-espera", tags=["lista-espera"])

RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

# Freno simple en memoria: 5 altas por IP cada 10 minutos.
# Vive por instancia de Lambda; no es una defensa fuerte, es un tope de cortesía
# para que un formulario público no se convierta en un grifo abierto.
_VENTANA_SEG = 600
_TOPE = 5
_intentos: dict[str, list[float]] = defaultdict(list)


def _ip_de(request: Request) -> str:
    reenviado = request.headers.get("x-forwarded-for")
    if reenviado:
        return reenviado.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"


def _pasa_el_freno(ip: str) -> bool:
    ahora = time.time()
    recientes = [t for t in _intentos[ip] if ahora - t < _VENTANA_SEG]
    _intentos[ip] = recientes
    if len(recientes) >= _TOPE:
        return False
    _intentos[ip].append(ahora)
    return True


class AltaLista(BaseModel):
    correo: str = Field(..., max_length=160)
    origen: str = Field(default="landing", max_length=40)


@router.post("", status_code=201)
def apuntarse(datos: AltaLista, request: Request, db: Session = Depends(get_db)):
    correo = datos.correo.strip().lower()

    if not RE_CORREO.match(correo):
        raise HTTPException(status_code=422, detail="Ese correo no se ve bien. Revísalo.")

    if not _pasa_el_freno(_ip_de(request)):
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos. Espera unos minutos e intenta de nuevo.",
        )

    fila = ListaEspera(correo=correo, origen=datos.origen.strip()[:40] or "landing")
    db.add(fila)
    try:
        db.commit()
    except IntegrityError:
        # Ya estaba apuntado. Para quien lo hace no es un error.
        db.rollback()
        raise HTTPException(status_code=409, detail="Ese correo ya está en la lista.")

    return {"ok": True, "correo": correo}


@router.get("/conteo")
def conteo(db: Session = Depends(get_db)):
    """Cuántos van. Público: sirve para prueba social cuando el número valga la pena."""
    return {"total": db.query(ListaEspera).count()}
