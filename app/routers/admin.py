from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import (
    Pregunta, Respuesta, Diagnostico, DiagPregunta,
    Usuario, Subtema, Componente, TipoDiagnostico,
    ResultadoDiag, Plan,
)
from ..schemas import (
    PreguntaAdminIn, PreguntaAdminUpdate,
    DiagnosticoAdminIn, DiagnosticoAdminUpdate,
    SubtemaAdminIn, SubtemaAdminUpdate,
    TipoDiagnosticoIn,
)
from ..core.security import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Preguntas ─────────────────────────────────────────────────────────────────

@router.get("/preguntas")
def list_preguntas(
    subtema_id: Optional[int] = None,
    nivel: Optional[str] = None,
    activo: Optional[bool] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Pregunta)
    if subtema_id:
        q = q.filter(Pregunta.subtema_id == subtema_id)
    if nivel:
        q = q.filter(Pregunta.nivel == nivel)
    if activo is not None:
        q = q.filter(Pregunta.activo == activo)
    total = q.count()
    preguntas = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": p.id,
                "codigo": p.codigo,
                "enunciado": p.enunciado[:80] + "..." if len(p.enunciado) > 80 else p.enunciado,
                "subtema": p.subtema.nombre if p.subtema else None,
                "subtema_id": p.subtema_id,
                "nivel": p.nivel,
                "activo": p.activo,
                "respuestas": [
                    {"id": r.id, "texto": r.texto, "es_correcta": r.es_correcta,
                     "orden": r.orden, "explicacion": r.explicacion}
                    for r in sorted(p.respuestas, key=lambda x: x.orden)
                ],
            }
            for p in preguntas
        ],
    }


@router.post("/preguntas", status_code=201)
def crear_pregunta(
    body: PreguntaAdminIn,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if db.query(Pregunta).filter(Pregunta.codigo == body.codigo).first():
        raise HTTPException(status_code=409, detail="Ya existe una pregunta con ese código")
    correctas = [r for r in body.respuestas if r.es_correcta]
    if len(correctas) != 1:
        raise HTTPException(status_code=400, detail="Debe haber exactamente una respuesta correcta")

    p = Pregunta(
        subtema_id=body.subtema_id,
        tipo_pregunta_id=body.tipo_pregunta_id,
        codigo=body.codigo,
        enunciado=body.enunciado,
        nivel=body.nivel,
    )
    db.add(p)
    db.flush()
    for r in body.respuestas:
        db.add(Respuesta(
            pregunta_id=p.id,
            texto=r.texto,
            es_correcta=r.es_correcta,
            orden=r.orden,
            explicacion=r.explicacion,
        ))
    db.commit()
    return {"id": p.id, "codigo": p.codigo}


@router.put("/preguntas/{pregunta_id}")
def editar_pregunta(
    pregunta_id: int,
    body: PreguntaAdminUpdate,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    p = db.query(Pregunta).filter(Pregunta.id == pregunta_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    if body.enunciado is not None:
        p.enunciado = body.enunciado
    if body.nivel is not None:
        p.nivel = body.nivel
    if body.activo is not None:
        p.activo = body.activo
    if body.respuestas:
        for ru in body.respuestas:
            r = db.query(Respuesta).filter(Respuesta.id == ru.id).first()
            if r:
                if ru.texto is not None:
                    r.texto = ru.texto
                if ru.explicacion is not None:
                    r.explicacion = ru.explicacion
    db.commit()
    return {"ok": True}


@router.delete("/preguntas/{pregunta_id}")
def eliminar_pregunta(
    pregunta_id: int,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    p = db.query(Pregunta).filter(Pregunta.id == pregunta_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    p.activo = False
    db.commit()
    return {"ok": True}


# ── Tipos de Diagnóstico ─────────────────────────────────────────────────────

def _tipo_out(t):
    return {
        "id": t.id, "nombre": t.nombre, "subtitulo": t.subtitulo,
        "descripcion": t.descripcion, "areas": t.areas, "activo": t.activo,
    }


@router.get("/tipos-diagnostico")
def list_tipos_diagnostico(_admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    tipos = db.query(TipoDiagnostico).order_by(TipoDiagnostico.id).all()
    return [_tipo_out(t) for t in tipos]


@router.post("/tipos-diagnostico")
def crear_tipo_diagnostico(
    body: TipoDiagnosticoIn,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    tipo = TipoDiagnostico(
        nombre=body.nombre, subtitulo=body.subtitulo,
        descripcion=body.descripcion, areas=body.areas, activo=True,
    )
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return _tipo_out(tipo)


@router.put("/tipos-diagnostico/{tipo_id}")
def editar_tipo_diagnostico(
    tipo_id: int,
    body: TipoDiagnosticoIn,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    tipo = db.query(TipoDiagnostico).filter(TipoDiagnostico.id == tipo_id).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    tipo.nombre = body.nombre
    if body.subtitulo is not None:
        tipo.subtitulo = body.subtitulo
    if body.descripcion is not None:
        tipo.descripcion = body.descripcion
    if body.areas is not None:
        tipo.areas = body.areas
    if body.activo is not None:
        tipo.activo = body.activo
    db.commit()
    return _tipo_out(tipo)


# ── Diagnósticos ─────────────────────────────────────────────────────────────

@router.get("/diagnosticos")
def list_diagnosticos(_admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    diagnosticos = db.query(Diagnostico).all()
    return [
        {
            "id": d.id,
            "nombre": d.nombre,
            "version": d.version,
            "tipo": d.tipo_diagnostico.nombre if d.tipo_diagnostico else None,
            "activo": d.activo,
            "total_preguntas": len(d.preguntas),
            "veces_completado": db.query(ResultadoDiag).filter(
                ResultadoDiag.diagnostico_id == d.id,
                ResultadoDiag.estado == "completado",
            ).count(),
        }
        for d in diagnosticos
    ]


@router.post("/diagnosticos", status_code=201)
def crear_diagnostico(
    body: DiagnosticoAdminIn,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    d = Diagnostico(
        tipo_diagnostico_id=body.tipo_diagnostico_id,
        nombre=body.nombre,
        version=body.version,
    )
    db.add(d)
    db.flush()
    for i, pid in enumerate(body.pregunta_ids):
        db.add(DiagPregunta(diagnostico_id=d.id, pregunta_id=pid, orden=i))
    db.commit()
    return {"id": d.id}


@router.put("/diagnosticos/{diag_id}")
def editar_diagnostico(
    diag_id: int,
    body: DiagnosticoAdminUpdate,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    d = db.query(Diagnostico).filter(Diagnostico.id == diag_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    if body.nombre is not None:
        d.nombre = body.nombre
    if body.version is not None:
        d.version = body.version
    if body.activo is not None:
        d.activo = body.activo
    if body.pregunta_ids is not None:
        db.query(DiagPregunta).filter(DiagPregunta.diagnostico_id == diag_id).delete()
        for i, pid in enumerate(body.pregunta_ids):
            db.add(DiagPregunta(diagnostico_id=diag_id, pregunta_id=pid, orden=i))
    db.commit()
    return {"ok": True}


# ── Usuarios ──────────────────────────────────────────────────────────────────

@router.get("/usuarios")
def list_usuarios(
    email: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(Usuario)
    if email:
        q = q.filter(Usuario.email.ilike(f"%{email}%"))
    total = q.count()
    usuarios = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": u.id,
                "nombre": u.nombre,
                "email": u.email,
                "rol": u.rol.nombre if u.rol else None,
                "activo": u.activo,
                "creado_en": u.creado_en.isoformat() if u.creado_en else None,
                "diagnosticos_completados": db.query(ResultadoDiag).filter(
                    ResultadoDiag.usuario_id == u.id,
                    ResultadoDiag.estado == "completado",
                ).count(),
                "graduado": u.graduado,
                "grado": u.grado,
                "sector": u.sector,
            }
            for u in usuarios
        ],
    }


# ── Subtemas ──────────────────────────────────────────────────────────────────

@router.get("/subtemas")
def list_subtemas(_admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    subtemas = (
        db.query(Subtema)
        .join(Componente)
        .join(TipoDiagnostico)
        .order_by(TipoDiagnostico.id, Componente.orden, Subtema.orden)
        .all()
    )
    return [
        {
            "id": s.id,
            "nombre": s.nombre,
            "descripcion": s.descripcion,
            "orden": s.orden,
            "componente": s.componente.nombre if s.componente else None,
            "componente_id": s.componente_id,
            "tipo_diagnostico": s.componente.tipo_diagnostico.nombre if s.componente and s.componente.tipo_diagnostico else None,
        }
        for s in subtemas
    ]


@router.post("/subtemas", status_code=201)
def crear_subtema(
    body: SubtemaAdminIn,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = Subtema(
        componente_id=body.componente_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        orden=body.orden,
    )
    db.add(s)
    db.commit()
    return {"id": s.id}


@router.put("/subtemas/{subtema_id}")
def editar_subtema(
    subtema_id: int,
    body: SubtemaAdminUpdate,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = db.query(Subtema).filter(Subtema.id == subtema_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Subtema no encontrado")
    if body.nombre is not None:
        s.nombre = body.nombre
    if body.descripcion is not None:
        s.descripcion = body.descripcion
    if body.orden is not None:
        s.orden = body.orden
    db.commit()
    return {"ok": True}


# ── Analytics Dashboard ───────────────────────────────────────────────────────

@router.get("/analytics/dashboard")
def dashboard(_admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    hoy = datetime.utcnow().replace(hour=0, minute=0, second=0)
    semana = datetime.utcnow().replace(hour=0, minute=0, second=0)
    from datetime import timedelta
    semana = hoy - timedelta(days=7)

    total_usuarios = db.query(Usuario).count()
    diag_hoy = db.query(ResultadoDiag).filter(
        ResultadoDiag.iniciado_en >= hoy,
        ResultadoDiag.estado == "completado",
    ).count()
    diag_semana = db.query(ResultadoDiag).filter(
        ResultadoDiag.iniciado_en >= semana,
        ResultadoDiag.estado == "completado",
    ).count()
    preguntas_activas = db.query(Pregunta).filter(Pregunta.activo == True).count()

    total_completados = db.query(ResultadoDiag).filter(ResultadoDiag.estado == "completado").count()
    # tasa_conversion: placeholder — requiere tabla de suscripciones con datos
    tasa_conversion = 0.0

    return {
        "total_usuarios": total_usuarios,
        "diagnosticos_hoy": diag_hoy,
        "diagnosticos_semana": diag_semana,
        "tasa_conversion": tasa_conversion,
        "preguntas_activas": preguntas_activas,
        "total_completados": total_completados,
    }
