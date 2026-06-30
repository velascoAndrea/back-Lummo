from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import (
    Usuario, Rol, ResultadoDiag, RespuestaDiag, DetalleResultado,
    Diagnostico, DiagPregunta, Pregunta, Respuesta, Plan, TokenReporte,
    TipoDiagnostico,
)
from ..schemas import (
    IniciarDiagnosticoRequest, IniciarDiagnosticoResponse,
    PreguntasResponse, PreguntaOut, OpcionOut,
    ResponderRequest, ResponderResponse,
    FinalizarResponse, DetalleSubtemaOut, PlanOut,
    RespuestaResumen,
)
from ..core.security import (
    create_access_token, generate_temp_password, hash_password,
    generate_report_token, get_sesion_token,
)
from ..core.email import send_results_email

router = APIRouter(prefix="/diagnosticos", tags=["diagnosticos"])


def _nivel_from_puntaje(pct: float) -> str:
    if pct <= 30:
        return "bajo"
    if pct <= 60:
        return "medio"
    return "alto"


@router.get("/catalogo")
def get_catalogo(db: Session = Depends(get_db)):
    """Devuelve todos los TipoDiagnostico activos con sus Diagnosticos disponibles."""
    tipos = db.query(TipoDiagnostico).filter(TipoDiagnostico.activo == True).order_by(TipoDiagnostico.id).all()
    result = []
    for tipo in tipos:
        diagnosticos = (
            db.query(Diagnostico)
            .filter(Diagnostico.tipo_diagnostico_id == tipo.id, Diagnostico.activo == True)
            .order_by(Diagnostico.id)
            .all()
        )
        diag_list = []
        for d in diagnosticos:
            total_q = db.query(DiagPregunta).filter(DiagPregunta.diagnostico_id == d.id).count()
            diag_list.append({
                "id": d.id,
                "nombre": d.nombre,
                "version": d.version,
                "total_preguntas": total_q,
            })
        if diag_list:
            result.append({
                "id": tipo.id,
                "nombre": tipo.nombre,
                "subtitulo": tipo.subtitulo,
                "descripcion": tipo.descripcion,
                "areas": tipo.areas,
                "diagnosticos": diag_list,
            })
    return result


@router.post("/iniciar", response_model=IniciarDiagnosticoResponse)
def iniciar_diagnostico(req: IniciarDiagnosticoRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == req.email).first()
    es_cuenta_nueva = False
    password_temporal = None

    if usuario:
        resultado_existente = (
            db.query(ResultadoDiag)
            .filter(
                ResultadoDiag.usuario_id == usuario.id,
                ResultadoDiag.diagnostico_id == req.diagnostico_id,
                ResultadoDiag.estado == "completado",
            )
            .first()
        )
        if resultado_existente:
            token_obj = db.query(TokenReporte).filter(
                TokenReporte.resultado_diag_id == resultado_existente.id
            ).first()
            return IniciarDiagnosticoResponse(
                resultado_id=resultado_existente.id,
                sesion_token="",
                es_cuenta_nueva=False,
                total_preguntas=0,
                ya_existe=True,
                token_reporte=token_obj.token if token_obj else None,
            )
    else:
        password_temporal = generate_temp_password()
        rol_est = db.query(Rol).filter(Rol.nombre == "estudiante").first()
        usuario = Usuario(
            nombre=req.nombre,
            email=req.email,
            password_hash=hash_password(password_temporal),
            password_cambiado=False,
            rol_id=rol_est.id if rol_est else None,
            graduado=req.graduado,
            grado=req.grado,
            sector=req.sector,
        )
        db.add(usuario)
        db.flush()
        es_cuenta_nueva = True

    diagnostico = db.query(Diagnostico).filter(
        Diagnostico.id == req.diagnostico_id,
        Diagnostico.activo == True,
    ).first()
    if not diagnostico:
        raise HTTPException(status_code=404, detail="Diagnóstico no encontrado")

    total_preguntas = db.query(DiagPregunta).filter(
        DiagPregunta.diagnostico_id == diagnostico.id
    ).count()

    resultado = ResultadoDiag(
        usuario_id=usuario.id,
        diagnostico_id=diagnostico.id,
        estado="en_progreso",
    )
    db.add(resultado)
    db.commit()
    db.refresh(resultado)

    sesion_token = create_access_token(
        {"resultado_id": resultado.id, "usuario_id": usuario.id},
        expires_delta=timedelta(hours=4),
    )

    return IniciarDiagnosticoResponse(
        resultado_id=resultado.id,
        sesion_token=sesion_token,
        es_cuenta_nueva=es_cuenta_nueva,
        total_preguntas=total_preguntas,
        ya_existe=False,
    )


@router.get("/{resultado_id}/preguntas", response_model=PreguntasResponse)
def get_preguntas(
    resultado_id: int,
    sesion: dict = Depends(get_sesion_token),
    db: Session = Depends(get_db),
):
    resultado = db.query(ResultadoDiag).filter(ResultadoDiag.id == resultado_id).first()
    if not resultado:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")

    diag_preguntas = (
        db.query(DiagPregunta)
        .filter(DiagPregunta.diagnostico_id == resultado.diagnostico_id)
        .order_by(DiagPregunta.orden)
        .all()
    )

    respondidas_rows = db.query(RespuestaDiag).filter(
        RespuestaDiag.resultado_diag_id == resultado_id
    ).all()
    ids_respondidas = [r.pregunta_id for r in respondidas_rows]

    # Build per-question answer detail (needed to show correct/incorrect on review)
    from ..schemas import RespuestaResumen
    respuestas_dadas = []
    for rd in respondidas_rows:
        item = RespuestaResumen(
            pregunta_id=rd.pregunta_id,
            respuesta_id=rd.respuesta_id,
            es_correcta=rd.es_correcta,
        )
        if not rd.es_correcta:
            correcta = db.query(Respuesta).filter(
                Respuesta.pregunta_id == rd.pregunta_id,
                Respuesta.es_correcta == True,
            ).first()
            if correcta:
                item.respuesta_correcta_id    = correcta.id
                item.respuesta_correcta_letra = chr(65 + correcta.orden)
                item.respuesta_correcta_texto = correcta.texto
                item.explicacion              = correcta.explicacion
        respuestas_dadas.append(item)

    preguntas_out = []
    for dp in diag_preguntas:
        p = dp.pregunta
        opciones = [
            OpcionOut(id=r.id, texto=r.texto, orden=r.orden)
            for r in sorted(p.respuestas, key=lambda x: x.orden)
        ]
        preguntas_out.append(PreguntaOut(id=p.id, enunciado=p.enunciado, imagen_url=p.imagen_url, opciones=opciones))

    return PreguntasResponse(
        preguntas=preguntas_out,
        ultima_respondida=len(ids_respondidas),
        ids_respondidas=ids_respondidas,
        respuestas_dadas=respuestas_dadas,
    )


@router.post("/{resultado_id}/responder", response_model=ResponderResponse)
def responder_pregunta(
    resultado_id: int,
    req: ResponderRequest,
    sesion: dict = Depends(get_sesion_token),
    db: Session = Depends(get_db),
):
    resultado = db.query(ResultadoDiag).filter(ResultadoDiag.id == resultado_id).first()
    if not resultado or resultado.estado != "en_progreso":
        raise HTTPException(status_code=400, detail="Diagnóstico no disponible")

    ya_existe = db.query(RespuestaDiag).filter(
        RespuestaDiag.resultado_diag_id == resultado_id,
        RespuestaDiag.pregunta_id == req.pregunta_id,
    ).first()
    if ya_existe:
        raise HTTPException(status_code=409, detail="Pregunta ya respondida")

    respuesta_sel = db.query(Respuesta).filter(Respuesta.id == req.respuesta_id).first()
    if not respuesta_sel:
        raise HTTPException(status_code=404, detail="Respuesta no encontrada")

    es_correcta = respuesta_sel.es_correcta

    resp_diag = RespuestaDiag(
        resultado_diag_id=resultado_id,
        pregunta_id=req.pregunta_id,
        respuesta_id=req.respuesta_id,
        es_correcta=es_correcta,
    )
    db.add(resp_diag)
    db.commit()

    # Siguiente pregunta
    diag_preguntas = (
        db.query(DiagPregunta)
        .filter(DiagPregunta.diagnostico_id == resultado.diagnostico_id)
        .order_by(DiagPregunta.orden)
        .all()
    )
    pregunta_ids = [dp.pregunta_id for dp in diag_preguntas]
    try:
        idx = pregunta_ids.index(req.pregunta_id)
    except ValueError:
        idx = len(pregunta_ids) - 1

    es_ultima = idx == len(pregunta_ids) - 1
    siguiente_id = pregunta_ids[idx + 1] if not es_ultima else None

    # Retroalimentación solo si incorrecta
    explicacion = None
    correcta_texto = None
    correcta_letra = None
    if not es_correcta:
        resp_correcta = db.query(Respuesta).filter(
            Respuesta.pregunta_id == req.pregunta_id,
            Respuesta.es_correcta == True,
        ).first()
        if resp_correcta:
            explicacion = resp_correcta.explicacion
            correcta_texto = resp_correcta.texto
            correcta_letra = chr(65 + resp_correcta.orden)

    return ResponderResponse(
        es_correcta=es_correcta,
        explicacion=explicacion,
        respuesta_correcta_texto=correcta_texto,
        respuesta_correcta_letra=correcta_letra,
        siguiente_pregunta_id=siguiente_id,
        es_ultima=es_ultima,
    )


@router.post("/{resultado_id}/finalizar", response_model=FinalizarResponse)
def finalizar_diagnostico(
    resultado_id: int,
    sesion: dict = Depends(get_sesion_token),
    db: Session = Depends(get_db),
):
    resultado = db.query(ResultadoDiag).filter(ResultadoDiag.id == resultado_id).first()
    if not resultado:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")
    if resultado.estado == "completado":
        raise HTTPException(status_code=400, detail="Diagnóstico ya finalizado")

    # Cargar todas las respuestas del diagnóstico
    diag_preguntas = (
        db.query(DiagPregunta)
        .filter(DiagPregunta.diagnostico_id == resultado.diagnostico_id)
        .all()
    )
    respuestas_diag = (
        db.query(RespuestaDiag)
        .filter(RespuestaDiag.resultado_diag_id == resultado_id)
        .all()
    )
    respuestas_map = {r.pregunta_id: r for r in respuestas_diag}

    # Calcular puntaje por subtema
    subtema_stats: dict = {}
    for dp in diag_preguntas:
        subtema = dp.pregunta.subtema
        if subtema.id not in subtema_stats:
            subtema_stats[subtema.id] = {"nombre": subtema.nombre, "correctas": 0, "total": 0}
        subtema_stats[subtema.id]["total"] += 1
        rd = respuestas_map.get(dp.pregunta_id)
        if rd and rd.es_correcta:
            subtema_stats[subtema.id]["correctas"] += 1

    detalles = []
    for subtema_id, stats in subtema_stats.items():
        pct = (stats["correctas"] / stats["total"] * 100) if stats["total"] > 0 else 0
        nivel = _nivel_from_puntaje(pct)
        d = DetalleResultado(
            resultado_diag_id=resultado_id,
            subtema_id=subtema_id,
            puntaje=round(pct, 1),
            nivel=nivel,
            correctas=stats["correctas"],
            total=stats["total"],
        )
        db.add(d)
        detalles.append(DetalleSubtemaOut(
            subtema=stats["nombre"],
            subtema_id=subtema_id,
            puntaje=round(pct, 1),
            nivel=nivel,
            correctas=stats["correctas"],
            total=stats["total"],
        ))

    total_correctas = sum(1 for r in respuestas_diag if r.es_correcta)
    total_preguntas = len(diag_preguntas)
    puntaje_global = round((total_correctas / total_preguntas * 100) if total_preguntas > 0 else 0, 1)
    nivel_global = _nivel_from_puntaje(puntaje_global)

    resultado.estado = "completado"
    resultado.nivel_global = nivel_global
    resultado.puntaje_global = puntaje_global
    resultado.finalizado_en = datetime.utcnow()
    db.flush()

    # Token de reporte
    token_str = generate_report_token()
    token_obj = TokenReporte(
        usuario_id=resultado.usuario_id,
        resultado_diag_id=resultado_id,
        token=token_str,
        expira_en=datetime.utcnow() + timedelta(days=365),
    )
    db.add(token_obj)

    # Plan recomendado
    plan = db.query(Plan).filter(Plan.nivel_recomendado == nivel_global, Plan.activo == True).first()
    if not plan:
        plan = db.query(Plan).filter(Plan.activo == True).first()

    db.commit()

    # Email stub
    usuario = resultado.usuario
    password_temporal = None
    if not usuario.password_cambiado:
        password_temporal = generate_temp_password()
        usuario.password_hash = hash_password(password_temporal)
        usuario.password_cambiado = False
        db.commit()

    send_results_email(
        to_email=usuario.email,
        nombre=usuario.nombre,
        nivel_global=nivel_global,
        puntaje_global=puntaje_global,
        token_reporte=token_str,
        password_temporal=password_temporal,
    )

    plan_out = PlanOut(
        id=plan.id,
        nombre=plan.nombre,
        precio_mensual=plan.precio_mensual,
        precio_anual=plan.precio_anual,
        nivel_recomendado=plan.nivel_recomendado,
        descripcion=plan.descripcion,
        recomendado=True,
    )

    return FinalizarResponse(
        nivel_global=nivel_global,
        puntaje_global=puntaje_global,
        detalles_por_subtema=detalles,
        plan_recomendado=plan_out,
        token_reporte=token_str,
        email_enviado=True,
        password_temporal=password_temporal,
    )
