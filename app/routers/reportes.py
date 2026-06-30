from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import TokenReporte, ResultadoDiag, RespuestaDiag, Respuesta, Plan
from ..schemas import ReporteResponse, DetalleSubtemaOut, ResumenPreguntaOut, PlanOut

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("/{token}", response_model=ReporteResponse)
def get_reporte(token: str, db: Session = Depends(get_db)):
    token_obj = db.query(TokenReporte).filter(TokenReporte.token == token).first()
    if not token_obj:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    resultado = db.query(ResultadoDiag).filter(
        ResultadoDiag.id == token_obj.resultado_diag_id
    ).first()
    if not resultado:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")

    # Heatmap por subtema
    heatmap = [
        DetalleSubtemaOut(
            subtema=d.subtema.nombre,
            subtema_id=d.subtema_id,
            puntaje=d.puntaje,
            nivel=d.nivel,
            correctas=d.correctas,
            total=d.total,
        )
        for d in resultado.detalles
    ]

    # Resumen de preguntas
    diag_preguntas = sorted(resultado.diagnostico.preguntas, key=lambda x: x.orden)
    respuestas_map = {r.pregunta_id: r for r in resultado.respuestas}

    resumen = []
    for dp in diag_preguntas:
        pregunta = dp.pregunta
        rd = respuestas_map.get(pregunta.id)
        if not rd:
            continue

        resp_correcta = next((r for r in pregunta.respuestas if r.es_correcta), None)
        resp_sel = rd.respuesta

        opcion_sel_letra = chr(65 + resp_sel.orden) if resp_sel else "?"
        opcion_cor_letra = chr(65 + resp_correcta.orden) if resp_correcta else "?"

        resumen.append(ResumenPreguntaOut(
            enunciado=pregunta.enunciado,
            opcion_seleccionada=opcion_sel_letra,
            es_correcta=rd.es_correcta,
            opcion_correcta=opcion_cor_letra,
            explicacion=resp_correcta.explicacion or "" if resp_correcta else "",
        ))

    # Plan recomendado
    plan = db.query(Plan).filter(
        Plan.nivel_recomendado == resultado.nivel_global,
        Plan.activo == True,
    ).first()
    if not plan:
        plan = db.query(Plan).filter(Plan.activo == True).first()

    plan_out = PlanOut(
        id=plan.id,
        nombre=plan.nombre,
        precio_mensual=plan.precio_mensual,
        precio_anual=plan.precio_anual,
        nivel_recomendado=plan.nivel_recomendado,
        descripcion=plan.descripcion,
        recomendado=True,
    )

    usuario = resultado.usuario
    return ReporteResponse(
        nivel_global=resultado.nivel_global,
        puntaje_global=resultado.puntaje_global,
        heatmap=heatmap,
        resumen_preguntas=resumen,
        plan_recomendado=plan_out,
        usuario={"nombre": usuario.nombre, "email": usuario.email},
    )


@router.post("/reenviar-link")
def reenviar_link(body: dict, db: Session = Depends(get_db)):
    from ..models import Usuario
    from ..core.email import send_results_email
    email = body.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email requerido")

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        return {"ok": True, "mensaje": "Si existe una cuenta, recibirás el enlace"}

    ultimo = (
        db.query(TokenReporte)
        .join(ResultadoDiag)
        .filter(ResultadoDiag.usuario_id == usuario.id)
        .order_by(TokenReporte.id.desc())
        .first()
    )
    if ultimo:
        resultado = ultimo.resultado
        send_results_email(
            to_email=usuario.email,
            nombre=usuario.nombre,
            nivel_global=resultado.nivel_global or "medio",
            puntaje_global=resultado.puntaje_global or 0,
            token_reporte=ultimo.token,
        )
    return {"ok": True, "mensaje": "Si existe una cuenta, recibirás el enlace"}
