"""Selección de las preguntas que ve un estudiante en un intento.

Un diagnóstico puede tener más preguntas asignadas por tema de las que se
muestran: `DiagTema.cantidad` indica cuántas tomar al azar de cada tema.
La selección es determinística por `resultado_id` (mismo intento ⇒ mismas
preguntas y mismo orden), así el estudiante puede salir y volver.
"""
import random
from collections import defaultdict
from sqlalchemy.orm import Session
from ..models import DiagPregunta, DiagTema


def cantidades_por_tema(db: Session, diagnostico_id: int) -> dict:
    """{subtema_id: cantidad} solo para temas con límite configurado."""
    rows = db.query(DiagTema).filter(DiagTema.diagnostico_id == diagnostico_id).all()
    return {r.subtema_id: r.cantidad for r in rows if r.cantidad is not None}


def _agrupar(diag_preguntas: list) -> dict:
    grupos = defaultdict(list)
    for dp in diag_preguntas:
        grupos[dp.pregunta.subtema_id].append(dp)
    return grupos


def total_efectivo(db: Session, diagnostico_id: int) -> int:
    """Cuántas preguntas verá el estudiante en cada intento."""
    diag_preguntas = db.query(DiagPregunta).filter(DiagPregunta.diagnostico_id == diagnostico_id).all()
    cantidades = cantidades_por_tema(db, diagnostico_id)
    return sum(
        min(len(dps), cantidades.get(sid, len(dps)))
        for sid, dps in _agrupar(diag_preguntas).items()
    )


def preguntas_de_sesion(db: Session, diagnostico_id: int, resultado_id: int) -> list:
    """DiagPreguntas del intento: muestra aleatoria por tema + orden barajado."""
    diag_preguntas = (
        db.query(DiagPregunta)
        .filter(DiagPregunta.diagnostico_id == diagnostico_id)
        .order_by(DiagPregunta.orden, DiagPregunta.id)
        .all()
    )
    cantidades = cantidades_por_tema(db, diagnostico_id)
    rnd = random.Random(resultado_id)

    seleccion = []
    grupos = _agrupar(diag_preguntas)
    # Iterar los temas en orden estable para que el resultado no dependa del dict
    for sid in sorted(grupos, key=lambda x: (x is None, x or 0)):
        dps = grupos[sid]
        cantidad = cantidades.get(sid)
        if cantidad is not None and cantidad < len(dps):
            dps = rnd.sample(dps, max(cantidad, 0))
        seleccion.extend(dps)

    rnd.shuffle(seleccion)
    return seleccion
