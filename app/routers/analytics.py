"""Analítica del panel admin: resumen, dónde fallan los estudiantes y vista por estudiante.

Convenciones:
- Un "intento vacío" (resultado en progreso sin ninguna respuesta) no cuenta como
  abandono: es alguien que abrió el diagnóstico y salió antes de contestar.
- Los filtros `diagnostico_id`, `desde` y `hasta` se aplican sobre el intento
  (`resultado_diag.iniciado_en`).
"""
from collections import defaultdict, Counter
from datetime import date, datetime, timedelta
from statistics import median
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from ..database import get_db
from ..models import (
    Usuario, Rol, ResultadoDiag, RespuestaDiag, Pregunta, Respuesta,
    Diagnostico, Suscripcion, Subtema,
)
from ..core.security import get_current_admin
from ..core.seleccion import total_efectivo

router = APIRouter(prefix="/admin/analytics", tags=["analytics"])

NIVELES = ["bajo", "medio", "alto"]


def _estudiantes(db: Session):
    return (
        db.query(Usuario)
        .join(Rol, Rol.id == Usuario.rol_id)
        .filter(Rol.nombre == "estudiante")
        .all()
    )


def _intentos(db: Session, diagnostico_id, desde, hasta):
    q = db.query(ResultadoDiag).options(joinedload(ResultadoDiag.usuario))
    if diagnostico_id:
        q = q.filter(ResultadoDiag.diagnostico_id == diagnostico_id)
    if desde:
        q = q.filter(ResultadoDiag.iniciado_en >= datetime.combine(desde, datetime.min.time()))
    if hasta:
        q = q.filter(ResultadoDiag.iniciado_en < datetime.combine(hasta + timedelta(days=1), datetime.min.time()))
    return q.all()


def _conteo_respuestas(db: Session, ids):
    """{resultado_id: (respondidas, correctas)}"""
    if not ids:
        return {}
    out = defaultdict(lambda: [0, 0])
    rows = db.query(RespuestaDiag.resultado_diag_id, RespuestaDiag.es_correcta).filter(
        RespuestaDiag.resultado_diag_id.in_(ids)
    ).all()
    for rid, ok in rows:
        out[rid][0] += 1
        if ok:
            out[rid][1] += 1
    return out


def _pct(a, b):
    return round(a / b * 100, 1) if b else None


# ── Resumen ───────────────────────────────────────────────────────────────────

@router.get("/resumen")
def resumen(
    diagnostico_id: Optional[int] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    estudiantes = _estudiantes(db)
    est_ids = {u.id for u in estudiantes}
    intentos = [r for r in _intentos(db, diagnostico_id, desde, hasta) if r.usuario_id in est_ids]
    conteo = _conteo_respuestas(db, [r.id for r in intentos])

    completados = [r for r in intentos if r.estado == "completado"]
    con_respuestas = [r for r in intentos if conteo.get(r.id, (0, 0))[0] > 0 or r.estado == "completado"]
    abandonados = [r for r in con_respuestas if r.estado != "completado"]
    suscritos = {s.usuario_id for s in db.query(Suscripcion).filter(Suscripcion.estado == "activa").all()}

    embudo = [
        {"etapa": "Registrados", "valor": len(est_ids)},
        {"etapa": "Iniciaron", "valor": len({r.usuario_id for r in intentos})},
        {"etapa": "Respondieron", "valor": len({r.usuario_id for r in con_respuestas})},
        {"etapa": "Completaron", "valor": len({r.usuario_id for r in completados})},
        {"etapa": "Suscritos", "valor": len(suscritos & est_ids)},
    ]

    # Actividad diaria (rango pedido o últimos 30 días)
    fin = hasta or date.today()
    ini = desde or (fin - timedelta(days=29))
    dias = {(ini + timedelta(days=i)).isoformat(): {"iniciados": 0, "completados": 0}
            for i in range((fin - ini).days + 1)}
    for r in con_respuestas:
        k = r.iniciado_en.date().isoformat() if r.iniciado_en else None
        if k in dias:
            dias[k]["iniciados"] += 1
    for r in completados:
        k = r.finalizado_en.date().isoformat() if r.finalizado_en else None
        if k in dias:
            dias[k]["completados"] += 1
    actividad = [{"fecha": k, **v} for k, v in dias.items()]

    niveles = Counter(r.nivel_global for r in completados if r.nivel_global)
    histograma = [{"rango": f"{i}–{i + 10}", "estudiantes": 0} for i in range(0, 100, 10)]
    for r in completados:
        if r.puntaje_global is not None:
            histograma[min(int(r.puntaje_global // 10), 9)]["estudiantes"] += 1

    # Abandono: tras cuántas preguntas se detuvieron los intentos sin terminar
    paradas = Counter()
    for r in abandonados:
        n = conteo.get(r.id, (0, 0))[0]
        b = (n - 1) // 5 * 5 + 1
        paradas[(b, b + 4)] += 1
    abandono = [{"rango": f"{a}–{b}", "intentos": c} for (a, b), c in sorted(paradas.items())]

    # Demografía (estudiantes con al menos un intento completado ⇒ puntaje)
    mejor = {}
    for r in completados:
        if r.puntaje_global is not None:
            mejor[r.usuario_id] = max(mejor.get(r.usuario_id, 0), r.puntaje_global)

    def grupo(clave_fn):
        g = defaultdict(lambda: {"estudiantes": 0, "completaron": 0, "puntajes": []})
        for u in estudiantes:
            k = clave_fn(u)
            g[k]["estudiantes"] += 1
            if u.id in mejor:
                g[k]["completaron"] += 1
                g[k]["puntajes"].append(mejor[u.id])
        return [
            {"grupo": k, "estudiantes": v["estudiantes"], "completaron": v["completaron"],
             "puntaje_promedio": round(sum(v["puntajes"]) / len(v["puntajes"]), 1) if v["puntajes"] else None}
            for k, v in g.items()
        ]

    duraciones = [r.duracion_segundos for r in completados if r.duracion_segundos]
    puntajes = [r.puntaje_global for r in completados if r.puntaje_global is not None]

    def _en_rango(dt):
        if dt is None:
            return False
        if desde and dt.date() < desde:
            return False
        if hasta and dt.date() > hasta:
            return False
        return True

    return {
        "kpis": {
            "estudiantes": len(est_ids),
            # Registrados dentro del periodo (para comparar contra el periodo anterior)
            "estudiantes_nuevos": sum(1 for u in estudiantes if _en_rango(u.creado_en)),
            "intentos_activos": len(con_respuestas),
            "intentos_vacios": len(intentos) - len(con_respuestas),
            "completados": len(completados),
            "tasa_finalizacion": _pct(len(completados), len(con_respuestas)),
            "puntaje_promedio": round(sum(puntajes) / len(puntajes), 1) if puntajes else None,
            "duracion_mediana_min": round(median(duraciones) / 60, 1) if duraciones else None,
        },
        "embudo": embudo,
        "actividad": actividad,
        "niveles": [{"nivel": n, "estudiantes": niveles.get(n, 0)} for n in NIVELES],
        "histograma": histograma,
        "abandono": abandono,
        "sector": grupo(lambda u: {"publico": "Público", "privado": "Privado"}.get(u.sector, "Sin dato")),
        "escolaridad": grupo(lambda u: "Graduado" if u.graduado else ("Cursando" if u.graduado is False else "Sin dato")),
    }


# ── Dónde fallan: temas y preguntas ───────────────────────────────────────────

@router.get("/aprendizaje")
def aprendizaje(
    diagnostico_id: Optional[int] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    ids = [r.id for r in _intentos(db, diagnostico_id, desde, hasta)]
    if not ids:
        return {"temas": [], "preguntas": [], "total_respuestas": 0}
    respuestas = (
        db.query(RespuestaDiag)
        .options(joinedload(RespuestaDiag.pregunta).joinedload(Pregunta.subtema).joinedload(Subtema.componente))
        .filter(RespuestaDiag.resultado_diag_id.in_(ids))
        .all()
    )

    temas = defaultdict(lambda: {"respuestas": 0, "correctas": 0, "tiempos": [], "preguntas": set()})
    preguntas = defaultdict(lambda: {"respuestas": 0, "correctas": 0, "tiempos": [], "elegidas": Counter(), "escritas": Counter()})
    for rd in respuestas:
        p = rd.pregunta
        if not p:
            continue
        st = p.subtema
        t = temas[st.id if st else None]
        t["nombre"] = st.nombre if st else "Sin tema"
        t["componente"] = st.componente.nombre if st and st.componente else None
        t["respuestas"] += 1
        t["preguntas"].add(p.id)
        pr = preguntas[p.id]
        pr["obj"] = p
        pr["respuestas"] += 1
        if rd.es_correcta:
            t["correctas"] += 1
            pr["correctas"] += 1
        else:
            if rd.respuesta_id:
                pr["elegidas"][rd.respuesta_id] += 1
            elif rd.respuesta_texto:
                pr["escritas"][rd.respuesta_texto.strip()] += 1
        if rd.tiempo_segundos:
            t["tiempos"].append(rd.tiempo_segundos)
            pr["tiempos"].append(rd.tiempo_segundos)

    textos = {}
    elegidas_ids = {rid for pr in preguntas.values() for rid in pr["elegidas"]}
    if elegidas_ids:
        for r in db.query(Respuesta).filter(Respuesta.id.in_(elegidas_ids)).all():
            textos[r.id] = (chr(65 + r.orden) if r.orden is not None else "", r.texto)

    temas_out = sorted([
        {
            "subtema_id": sid, "tema": v["nombre"], "componente": v["componente"],
            "respuestas": v["respuestas"], "correctas": v["correctas"],
            "pct_error": _pct(v["respuestas"] - v["correctas"], v["respuestas"]),
            "tiempo_promedio": round(sum(v["tiempos"]) / len(v["tiempos"]), 1) if v["tiempos"] else None,
            "preguntas": len(v["preguntas"]),
        }
        for sid, v in temas.items()
    ], key=lambda x: -(x["pct_error"] or 0))

    preguntas_out = []
    for pid, v in preguntas.items():
        p = v["obj"]
        incorrectas = v["respuestas"] - v["correctas"]
        distractor = None
        if v["elegidas"]:
            rid, c = v["elegidas"].most_common(1)[0]
            letra, texto = textos.get(rid, ("", ""))
            distractor = {"letra": letra, "texto": texto[:120], "veces": c, "pct_de_errores": _pct(c, incorrectas)}
        elif v["escritas"]:
            texto, c = v["escritas"].most_common(1)[0]
            distractor = {"letra": None, "texto": texto[:120], "veces": c, "pct_de_errores": _pct(c, incorrectas)}
        preguntas_out.append({
            "pregunta_id": pid, "codigo": p.codigo,
            "enunciado": p.enunciado[:160] + ("…" if len(p.enunciado) > 160 else ""),
            "tema": p.subtema.nombre if p.subtema else None, "nivel": p.nivel,
            "respuestas": v["respuestas"], "correctas": v["correctas"],
            "pct_error": _pct(incorrectas, v["respuestas"]),
            "tiempo_promedio": round(sum(v["tiempos"]) / len(v["tiempos"]), 1) if v["tiempos"] else None,
            "distractor": distractor,
        })
    preguntas_out.sort(key=lambda x: (-(x["pct_error"] or 0), -x["respuestas"]))

    return {"temas": temas_out, "preguntas": preguntas_out, "total_respuestas": len(respuestas)}


# ── Por estudiante ────────────────────────────────────────────────────────────

@router.get("/estudiantes")
def estudiantes(
    busqueda: Optional[str] = None,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    users = _estudiantes(db)
    if busqueda:
        b = busqueda.lower()
        users = [u for u in users if b in (u.nombre or "").lower() or b in (u.email or "").lower()]
    ids = [u.id for u in users]
    intentos = db.query(ResultadoDiag).options(joinedload(ResultadoDiag.diagnostico)).filter(
        ResultadoDiag.usuario_id.in_(ids)
    ).all() if ids else []
    conteo = _conteo_respuestas(db, [r.id for r in intentos])
    totales = {}

    por_usuario = defaultdict(list)
    for r in intentos:
        por_usuario[r.usuario_id].append(r)

    out = []
    for u in users:
        rs = por_usuario[u.id]
        activos = [r for r in rs if r.estado == "completado" or conteo.get(r.id, (0, 0))[0] > 0]
        comp = sorted([r for r in rs if r.estado == "completado"], key=lambda r: r.finalizado_en or datetime.min)
        abiertos = sorted([r for r in activos if r.estado != "completado"], key=lambda r: r.iniciado_en or datetime.min)
        ultimo = comp[-1] if comp else None
        progreso = None
        if abiertos:
            a = abiertos[-1]
            if a.diagnostico_id not in totales:
                totales[a.diagnostico_id] = total_efectivo(db, a.diagnostico_id)
            progreso = {"respondidas": conteo[a.id][0], "total": totales[a.diagnostico_id],
                        "diagnostico": a.diagnostico.nombre if a.diagnostico else None}
        fechas = [d for r in rs for d in (r.iniciado_en, r.finalizado_en) if d]
        out.append({
            "id": u.id, "nombre": u.nombre, "email": u.email, "sector": u.sector,
            "graduado": u.graduado, "grado": u.grado, "creado_en": u.creado_en,
            "intentos": len(activos), "completados": len(comp),
            "ultimo_puntaje": ultimo.puntaje_global if ultimo else None,
            "ultimo_nivel": ultimo.nivel_global if ultimo else None,
            "mejor_puntaje": max((r.puntaje_global for r in comp if r.puntaje_global is not None), default=None),
            "progreso": progreso,
            "ultima_actividad": max(fechas) if fechas else u.creado_en,
        })
    out.sort(key=lambda x: x["ultima_actividad"] or datetime.min, reverse=True)
    return out


@router.get("/estudiantes/{usuario_id}")
def estudiante_detalle(
    usuario_id: int,
    _admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    intentos = (
        db.query(ResultadoDiag).options(joinedload(ResultadoDiag.diagnostico))
        .filter(ResultadoDiag.usuario_id == usuario_id)
        .order_by(ResultadoDiag.iniciado_en.desc())
        .all()
    )
    ids = [r.id for r in intentos]
    respuestas = (
        db.query(RespuestaDiag)
        .options(joinedload(RespuestaDiag.pregunta).joinedload(Pregunta.subtema),
                 joinedload(RespuestaDiag.respuesta))
        .filter(RespuestaDiag.resultado_diag_id.in_(ids))
        .order_by(RespuestaDiag.id)
        .all()
    ) if ids else []

    correctas_por_pregunta = {}
    pids = {rd.pregunta_id for rd in respuestas}
    if pids:
        for r in db.query(Respuesta).filter(Respuesta.pregunta_id.in_(pids), Respuesta.es_correcta == True).all():
            correctas_por_pregunta.setdefault(r.pregunta_id, r)

    por_intento = defaultdict(list)
    temas = defaultdict(lambda: {"correctas": 0, "total": 0, "tiempos": []})
    for rd in respuestas:
        p = rd.pregunta
        ok = correctas_por_pregunta.get(rd.pregunta_id)
        por_intento[rd.resultado_diag_id].append({
            "codigo": p.codigo if p else None,
            "enunciado": (p.enunciado[:140] + ("…" if len(p.enunciado) > 140 else "")) if p else None,
            "tema": p.subtema.nombre if p and p.subtema else None,
            "es_correcta": bool(rd.es_correcta),
            "elegida": rd.respuesta.texto if rd.respuesta else rd.respuesta_texto,
            "correcta": ok.texto if ok else None,
            "tiempo_segundos": rd.tiempo_segundos,
        })
        t = temas[p.subtema.nombre if p and p.subtema else "Sin tema"]
        t["total"] += 1
        t["correctas"] += 1 if rd.es_correcta else 0
        if rd.tiempo_segundos:
            t["tiempos"].append(rd.tiempo_segundos)

    totales = {}
    intentos_out = []
    for r in intentos:
        rs = por_intento.get(r.id, [])
        if r.estado != "completado" and not rs:
            continue  # intento vacío
        if r.diagnostico_id not in totales:
            totales[r.diagnostico_id] = total_efectivo(db, r.diagnostico_id)
        intentos_out.append({
            "id": r.id, "diagnostico": r.diagnostico.nombre if r.diagnostico else None,
            "estado": r.estado, "puntaje": r.puntaje_global, "nivel": r.nivel_global,
            "iniciado_en": r.iniciado_en, "finalizado_en": r.finalizado_en,
            "duracion_min": round(r.duracion_segundos / 60, 1) if r.duracion_segundos else None,
            "respondidas": len(rs), "correctas": sum(1 for x in rs if x["es_correcta"]),
            "total": totales[r.diagnostico_id],
            "respuestas": rs,
        })

    return {
        "usuario": {
            "id": u.id, "nombre": u.nombre, "email": u.email, "sector": u.sector,
            "graduado": u.graduado, "anio_graduacion": u.anio_graduacion, "grado": u.grado,
            "creado_en": u.creado_en,
        },
        "temas": sorted([
            {"tema": k, "correctas": v["correctas"], "total": v["total"],
             "pct_acierto": _pct(v["correctas"], v["total"]),
             "tiempo_promedio": round(sum(v["tiempos"]) / len(v["tiempos"]), 1) if v["tiempos"] else None}
            for k, v in temas.items()
        ], key=lambda x: x["pct_acierto"] or 0),
        "intentos": intentos_out,
        "intentos_vacios": sum(1 for r in intentos if r.estado != "completado" and not por_intento.get(r.id)),
    }


@router.get("/diagnosticos")
def diagnosticos_filtro(_admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    """Lista corta para el selector de filtro del dashboard."""
    return [{"id": d.id, "nombre": d.nombre} for d in db.query(Diagnostico).order_by(Diagnostico.id).all()]
