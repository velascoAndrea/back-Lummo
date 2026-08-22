import os
import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db
from ..models import (
    Pregunta, Respuesta, Diagnostico, DiagPregunta,
    Usuario, Subtema, Componente, TipoDiagnostico,
    ResultadoDiag, Plan, Terminos, Formula, Configuracion,
)
from ..schemas import (
    PreguntaAdminIn, PreguntaAdminUpdate,
    DiagnosticoAdminIn, DiagnosticoAdminUpdate,
    SubtemaAdminIn, SubtemaAdminUpdate,
    TipoDiagnosticoIn,
    FormulaAdminIn, FormulaAdminUpdate, MostrarFormularioUpdate,
    ConfiguracionUpdate,
)
from ..core.security import get_current_admin

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Preguntas ─────────────────────────────────────────────────────────────────

@router.get("/preguntas")
def list_preguntas(
    subtema_id: Optional[int] = None,
    nivel: Optional[str] = None,
    activo: Optional[bool] = None,
    busqueda: Optional[str] = None,
    limit: int = Query(25, le=200),
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
    if busqueda:
        term = f"%{busqueda}%"
        from sqlalchemy import or_
        q = q.filter(or_(Pregunta.enunciado.ilike(term), Pregunta.codigo.ilike(term)))
    total = q.count()
    preguntas = q.offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": p.id,
                "codigo": p.codigo,
                "enunciado": p.enunciado[:80] + "..." if len(p.enunciado) > 80 else p.enunciado,
                "imagen_url": p.imagen_url,
                "tipo": p.tipo_pregunta.nombre if p.tipo_pregunta and p.tipo_pregunta.nombre else "opcion_multiple",
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
    if body.tipo_pregunta_id == 2:
        # Respuesta escrita: todas las filas son respuestas aceptadas
        if not body.respuestas or not all((r.texto or "").strip() for r in body.respuestas):
            raise HTTPException(status_code=400, detail="Agrega al menos una respuesta aceptada (sin textos vacíos)")
    elif len(correctas) != 1:
        raise HTTPException(status_code=400, detail="Debe haber exactamente una respuesta correcta")

    p = Pregunta(
        subtema_id=body.subtema_id,
        tipo_pregunta_id=body.tipo_pregunta_id,
        codigo=body.codigo,
        enunciado=body.enunciado,
        imagen_url=body.imagen_url or None,
        nivel=body.nivel,
    )
    db.add(p)
    db.flush()
    es_escrita = body.tipo_pregunta_id == 2
    for r in body.respuestas:
        db.add(Respuesta(
            pregunta_id=p.id,
            texto=r.texto,
            es_correcta=True if es_escrita else r.es_correcta,
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
    if body.codigo is not None and body.codigo.strip():
        existing = db.query(Pregunta).filter(Pregunta.codigo == body.codigo.strip(), Pregunta.id != pregunta_id).first()
        if existing:
            raise HTTPException(status_code=409, detail=f"El código '{body.codigo}' ya está en uso")
        p.codigo = body.codigo.strip().upper()
    if body.enunciado is not None:
        p.enunciado = body.enunciado
    if body.imagen_url is not None:
        p.imagen_url = body.imagen_url or None
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
            "tiempo_limite_minutos": d.tiempo_limite_minutos,
            "instrucciones": d.instrucciones,
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
        tiempo_limite_minutos=body.tiempo_limite_minutos,
        instrucciones=body.instrucciones,
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
    if "tiempo_limite_minutos" in body.model_fields_set:
        # None explícito ⇒ quitar el límite; entero ⇒ establecerlo
        d.tiempo_limite_minutos = body.tiempo_limite_minutos or None
    if "instrucciones" in body.model_fields_set:
        d.instrucciones = (body.instrucciones or "").strip() or None
    if body.pregunta_ids is not None:
        db.query(DiagPregunta).filter(DiagPregunta.diagnostico_id == diag_id).delete()
        for i, pid in enumerate(body.pregunta_ids):
            db.add(DiagPregunta(diagnostico_id=diag_id, pregunta_id=pid, orden=i))
    db.commit()
    return {"ok": True}


# ── Preguntas de un diagnóstico (gestión individual) ─────────────────────────

@router.get("/diagnosticos/{diag_id}/preguntas")
def get_preguntas_diagnostico(
    diag_id: int,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    d = db.query(Diagnostico).filter(Diagnostico.id == diag_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    items = sorted(d.preguntas, key=lambda x: x.orden)
    return [
        {
            "id": dp.pregunta.id,
            "codigo": dp.pregunta.codigo,
            "enunciado": dp.pregunta.enunciado[:100] + "..." if len(dp.pregunta.enunciado) > 100 else dp.pregunta.enunciado,
            "subtema": dp.pregunta.subtema.nombre if dp.pregunta.subtema else None,
            "nivel": dp.pregunta.nivel,
            "imagen_url": dp.pregunta.imagen_url,
            "orden": dp.orden,
            "mostrar_formulario": bool(dp.mostrar_formulario),
        }
        for dp in items
    ]


@router.post("/diagnosticos/{diag_id}/preguntas/{pregunta_id}", status_code=201)
def agregar_pregunta_diagnostico(
    diag_id: int,
    pregunta_id: int,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    d = db.query(Diagnostico).filter(Diagnostico.id == diag_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    p = db.query(Pregunta).filter(Pregunta.id == pregunta_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada")
    ya_existe = db.query(DiagPregunta).filter(
        DiagPregunta.diagnostico_id == diag_id,
        DiagPregunta.pregunta_id == pregunta_id,
    ).first()
    if ya_existe:
        raise HTTPException(status_code=409, detail="La pregunta ya está en este diagnóstico")
    max_orden = db.query(func.max(DiagPregunta.orden)).filter(DiagPregunta.diagnostico_id == diag_id).scalar() or -1
    db.add(DiagPregunta(diagnostico_id=diag_id, pregunta_id=pregunta_id, orden=max_orden + 1))
    db.commit()
    return {"ok": True}


@router.delete("/diagnosticos/{diag_id}/preguntas/{pregunta_id}")
def quitar_pregunta_diagnostico(
    diag_id: int,
    pregunta_id: int,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    dp = db.query(DiagPregunta).filter(
        DiagPregunta.diagnostico_id == diag_id,
        DiagPregunta.pregunta_id == pregunta_id,
    ).first()
    if not dp:
        raise HTTPException(status_code=404, detail="Pregunta no está en este diagnóstico")
    db.delete(dp)
    db.commit()
    return {"ok": True}


@router.put("/diagnosticos/{diag_id}/preguntas/{pregunta_id}/formulario")
def toggle_formulario_pregunta(
    diag_id: int,
    pregunta_id: int,
    body: MostrarFormularioUpdate,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    dp = db.query(DiagPregunta).filter(
        DiagPregunta.diagnostico_id == diag_id,
        DiagPregunta.pregunta_id == pregunta_id,
    ).first()
    if not dp:
        raise HTTPException(status_code=404, detail="Pregunta no está en este diagnóstico")
    dp.mostrar_formulario = body.mostrar_formulario
    db.commit()
    return {"ok": True, "mostrar_formulario": dp.mostrar_formulario}


# ── Formulario (fórmulas por diagnóstico) ─────────────────────────────────────

def _formula_out(f: Formula):
    return {
        "id": f.id,
        "diagnostico_id": f.diagnostico_id,
        "nombre": f.nombre,
        "contenido": f.contenido,
        "imagen_url": f.imagen_url,
        "tip": f.tip,
        "orden": f.orden,
        "activo": f.activo,
    }


@router.get("/diagnosticos/{diag_id}/formulas")
def list_formulas(diag_id: int, _admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    formulas = (
        db.query(Formula)
        .filter(Formula.diagnostico_id == diag_id)
        .order_by(Formula.orden, Formula.id)
        .all()
    )
    return [_formula_out(f) for f in formulas]


@router.post("/diagnosticos/{diag_id}/formulas", status_code=201)
def crear_formula(
    diag_id: int,
    body: FormulaAdminIn,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    d = db.query(Diagnostico).filter(Diagnostico.id == diag_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")
    if not body.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre de la fórmula es requerido")
    if not (body.contenido and body.contenido.strip()) and not body.imagen_url:
        raise HTTPException(status_code=400, detail="La fórmula debe tener contenido de texto o imagen")
    f = Formula(
        diagnostico_id=diag_id,
        nombre=body.nombre.strip(),
        contenido=body.contenido,
        imagen_url=body.imagen_url,
        tip=body.tip,
        orden=body.orden,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return _formula_out(f)


@router.put("/formulas/{formula_id}")
def editar_formula(
    formula_id: int,
    body: FormulaAdminUpdate,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    f = db.query(Formula).filter(Formula.id == formula_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fórmula no encontrada")
    if body.nombre is not None:
        f.nombre = body.nombre.strip()
    if "contenido" in body.model_fields_set:
        f.contenido = body.contenido
    if "imagen_url" in body.model_fields_set:
        f.imagen_url = body.imagen_url or None
    if "tip" in body.model_fields_set:
        f.tip = body.tip
    if body.orden is not None:
        f.orden = body.orden
    if body.activo is not None:
        f.activo = body.activo
    if not (f.contenido and f.contenido.strip()) and not f.imagen_url:
        raise HTTPException(status_code=400, detail="La fórmula debe tener contenido de texto o imagen")
    db.commit()
    return _formula_out(f)


@router.delete("/formulas/{formula_id}")
def eliminar_formula(formula_id: int, _admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    f = db.query(Formula).filter(Formula.id == formula_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Fórmula no encontrada")
    db.delete(f)
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


# ── Términos y Condiciones ────────────────────────────────────────────────────

@router.get("/terminos")
def get_terminos_admin(_admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    t = db.query(Terminos).filter(Terminos.id == 1).first()
    if not t:
        raise HTTPException(404, "Términos no encontrados")
    return {"contenido": t.contenido, "fecha_modificacion": t.fecha_modificacion, "version": t.version}


@router.put("/terminos")
def update_terminos(body: dict, _admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    import json
    contenido = body.get("contenido")
    version   = body.get("version", "1.0")
    if not contenido:
        raise HTTPException(400, "contenido es requerido")
    # Validate JSON structure
    try:
        parsed = json.loads(contenido) if isinstance(contenido, str) else contenido
        if not isinstance(parsed, list):
            raise ValueError
    except Exception:
        raise HTTPException(400, "contenido debe ser un array JSON de secciones")

    t = db.query(Terminos).filter(Terminos.id == 1).first()
    if t:
        t.contenido = json.dumps(parsed, ensure_ascii=False)
        t.fecha_modificacion = datetime.utcnow()
        t.version = version
    else:
        t = Terminos(id=1, contenido=json.dumps(parsed, ensure_ascii=False), version=version)
        db.add(t)
    db.commit()
    db.refresh(t)
    return {"ok": True, "fecha_modificacion": t.fecha_modificacion, "version": t.version}


# ── Upload de imágenes ─────────────────────────────────────────────────────────

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
EXT_MAP = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif", "image/webp": "webp"}

@router.post("/upload-imagen")
async def upload_imagen(
    file: UploadFile = File(...),
    _admin=Depends(get_current_admin),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Solo se permiten imágenes jpg, png, gif o webp")

    bucket = os.getenv("IMAGES_BUCKET")
    region = os.getenv("AWS_REGION", "us-east-1")
    if not bucket:
        raise HTTPException(500, "IMAGES_BUCKET no configurado en el servidor")

    try:
        import boto3
        content = await file.read()
        if len(content) > 8 * 1024 * 1024:
            raise HTTPException(400, "La imagen no puede superar 8 MB")
        ext = EXT_MAP.get(file.content_type, "jpg")
        key = f"images/{uuid.uuid4()}.{ext}"
        s3 = boto3.client("s3", region_name=region)
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=file.content_type,
            CacheControl="max-age=31536000",
        )
        url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        return {"url": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error al subir imagen: {str(e)}")


# ── Configuración global (clave/valor) ────────────────────────────────────────

@router.get("/configuracion")
def list_configuracion(_admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    from .planes import TASA_USD_DEFAULT
    items = {c.clave: c.valor for c in db.query(Configuracion).all()}
    items.setdefault("tasa_usd", str(TASA_USD_DEFAULT))
    return items


@router.put("/configuracion/{clave}")
def set_configuracion(
    clave: str,
    body: ConfiguracionUpdate,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if clave == "tasa_usd":
        try:
            tasa = float(body.valor)
        except ValueError:
            raise HTTPException(status_code=400, detail="La tasa debe ser un número")
        if tasa <= 0:
            raise HTTPException(status_code=400, detail="La tasa debe ser mayor a 0")
    cfg = db.query(Configuracion).filter(Configuracion.clave == clave).first()
    if cfg:
        cfg.valor = body.valor
    else:
        cfg = Configuracion(clave=clave, valor=body.valor)
        db.add(cfg)
    db.commit()
    return {"clave": clave, "valor": body.valor}
