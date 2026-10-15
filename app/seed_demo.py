"""Datos de prueba para ver el dashboard de analítica con volumen.

SOLO PARA LA BD LOCAL O lummo_dev (nunca producción). Crea ~36 estudiantes ficticios (correo @demo.lummo.local)
con intentos completados, abandonados y vacíos, respuestas con tiempos y una
dificultad distinta por tema.

    docker exec -it backend-backend-1 python -m app.seed_demo            # crear
    docker exec -it backend-backend-1 python -m app.seed_demo --borrar   # quitar

Base de dev en la nube (nunca prod): DATABASE_URL=<url de lummo_dev> python -m app.seed_demo --nube-dev
"""
import os
import random
import sys
from datetime import datetime, timedelta
from .database import SessionLocal, DATABASE_URL
from .models import (
    Usuario, Rol, ResultadoDiag, RespuestaDiag, DetalleResultado,
    Diagnostico, Respuesta, TokenReporte,
)
from .core.security import hash_password
from .core.seleccion import preguntas_de_sesion

DOMINIO = "@demo.lummo.local"
NOMBRES = [
    "Ana Lucía", "José Pablo", "María Fernanda", "Diego", "Sofía", "Luis Fernando", "Valeria",
    "Carlos", "Gabriela", "Javier", "Andrea", "Kevin", "Daniela", "Rodrigo", "Mónica", "Esteban",
    "Paola", "Jorge", "Alejandra", "Marco", "Lucía", "Fernando", "Karla", "Brandon", "Ximena",
    "Héctor", "Camila", "Óscar", "Isabel", "Walter", "Rocío", "Emilio", "Natalia", "Pedro",
    "Mariela", "Sergio",
]
APELLIDOS = ["López", "García", "Pérez", "Morales", "Hernández", "Castillo", "Ramírez", "Méndez", "Juárez", "Ruiz"]


def _nivel(p):
    return "bajo" if p <= 30 else "medio" if p <= 60 else "alto"


def _verificar_local():
    nombre_bd = DATABASE_URL.rsplit("/", 1)[-1].split("?")[0]
    if "prod" in nombre_bd or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        sys.exit("Abortado: seed_demo nunca corre contra producción.")
    es_local = any(h in DATABASE_URL for h in ("@db:", "@localhost", "@127.0.0.1"))
    # La base de dev en la nube solo con permiso explícito
    if not es_local and not ("--nube-dev" in sys.argv and nombre_bd == "lummo_dev"):
        sys.exit("Abortado: fuera de local solo se permite lummo_dev, pasando --nube-dev.")


def borrar(db):
    users = db.query(Usuario).filter(Usuario.email.like(f"%{DOMINIO}")).all()
    uids = [u.id for u in users]
    if not uids:
        print("No hay datos demo.")
        return
    rids = [r.id for r in db.query(ResultadoDiag).filter(ResultadoDiag.usuario_id.in_(uids)).all()]
    if rids:
        db.query(RespuestaDiag).filter(RespuestaDiag.resultado_diag_id.in_(rids)).delete(synchronize_session=False)
        db.query(DetalleResultado).filter(DetalleResultado.resultado_diag_id.in_(rids)).delete(synchronize_session=False)
        db.query(TokenReporte).filter(TokenReporte.resultado_diag_id.in_(rids)).delete(synchronize_session=False)
        db.query(ResultadoDiag).filter(ResultadoDiag.id.in_(rids)).delete(synchronize_session=False)
    db.query(Usuario).filter(Usuario.id.in_(uids)).delete(synchronize_session=False)
    db.commit()
    print(f"Borrados {len(uids)} estudiantes demo y {len(rids)} intentos.")


def crear(db):
    rnd = random.Random(2026)
    rol = db.query(Rol).filter(Rol.nombre == "estudiante").first()
    diags = db.query(Diagnostico).filter(Diagnostico.activo == True).order_by(Diagnostico.id).all()
    if not diags:
        sys.exit("No hay diagnósticos activos.")
    pw = hash_password("demo1234")
    ahora = datetime.utcnow()
    # Dificultad por tema: cada subtema resta algo a la probabilidad de acierto
    dificultad = {}
    dificultad_preg = {}

    n_intentos = 0
    for i, nombre in enumerate(NOMBRES):
        apellido = APELLIDOS[i % len(APELLIDOS)]
        email = f"{nombre.split()[0].lower().replace('í', 'i').replace('ó', 'o').replace('é', 'e')}.{i}{DOMINIO}"
        if db.query(Usuario).filter(Usuario.email == email).first():
            continue
        graduado = rnd.random() < 0.55
        creado = ahora - timedelta(days=rnd.randint(0, 29), hours=rnd.randint(0, 23))
        u = Usuario(
            nombre=f"{nombre} {apellido}", email=email, password_hash=pw, password_cambiado=True,
            rol_id=rol.id if rol else None, creado_en=creado,
            sector=rnd.choice(["publico", "publico", "privado"]),
            graduado=graduado,
            anio_graduacion=rnd.choice([2024, 2025]) if graduado else None,
            grado=None if graduado else rnd.choice(["4to Bachillerato", "5to Bachillerato", "6to Perito"]),
        )
        db.add(u)
        db.flush()
        habilidad = rnd.gauss(0.55 if u.sector == "privado" else 0.45, 0.15)

        for diag in rnd.sample(diags, k=min(len(diags), rnd.choice([1, 1, 1, 2]))):
            destino = rnd.random()   # <0.12 vacío, <0.40 abandona, resto completa
            inicio = creado + timedelta(minutes=rnd.randint(1, 600))
            r = ResultadoDiag(usuario_id=u.id, diagnostico_id=diag.id, estado="en_progreso", iniciado_en=inicio)
            db.add(r)
            db.flush()
            n_intentos += 1
            if destino < 0.12:
                continue
            dps = preguntas_de_sesion(db, diag.id, r.id)
            corte = len(dps) if destino >= 0.40 else rnd.randint(1, max(1, int(len(dps) * 0.7)))
            t = inicio
            stats = {}
            correctas = 0
            for dp in dps[:corte]:
                p = dp.pregunta
                sid = p.subtema_id
                if sid not in dificultad:
                    dificultad[sid] = rnd.uniform(-0.30, 0.30)
                if p.id not in dificultad_preg:
                    dificultad_preg[p.id] = rnd.gauss(0, 0.18)   # algunas preguntas son trampas
                prob = min(0.95, max(0.05, habilidad + dificultad[sid] + dificultad_preg[p.id]))
                ok = rnd.random() < prob
                opciones = sorted(p.respuestas, key=lambda x: x.orden or 0)
                buena = next((o for o in opciones if o.es_correcta), None)
                malas = [o for o in opciones if not o.es_correcta]
                es_escrita = p.tipo_pregunta and p.tipo_pregunta.nombre == "respuesta_escrita"
                segundos = max(8, int(rnd.gauss(55 + (40 if not ok else 0), 25)))
                t += timedelta(seconds=segundos)
                if es_escrita:
                    rd = RespuestaDiag(resultado_diag_id=r.id, pregunta_id=p.id, es_correcta=ok,
                                       respuesta_texto=(buena.texto if ok and buena else str(rnd.randint(1, 99))),
                                       tiempo_segundos=segundos)
                else:
                    # el primer distractor es "el tentador": recibe la mayoría de errores
                    elegida = buena if ok else (malas[0] if malas and rnd.random() < 0.6 else rnd.choice(malas or opciones))
                    ok = bool(elegida and elegida.es_correcta)
                    rd = RespuestaDiag(resultado_diag_id=r.id, pregunta_id=p.id, respuesta_id=elegida.id if elegida else None,
                                       es_correcta=ok, tiempo_segundos=segundos)
                db.add(rd)
                s = stats.setdefault(sid, [0, 0])
                s[1] += 1
                if ok:
                    s[0] += 1
                    correctas += 1
            if destino >= 0.40:
                puntaje = round(correctas / len(dps) * 100, 1) if dps else 0
                r.estado = "completado"
                r.puntaje_global = puntaje
                r.nivel_global = _nivel(puntaje)
                r.finalizado_en = t
                r.duracion_segundos = int((t - inicio).total_seconds())
                for sid, (c, tot) in stats.items():
                    pct = round(c / tot * 100, 1)
                    db.add(DetalleResultado(resultado_diag_id=r.id, subtema_id=sid, puntaje=pct,
                                            nivel=_nivel(pct), correctas=c, total=tot))
    db.commit()
    print(f"Creados estudiantes demo con {n_intentos} intentos. Contraseña de todos: demo1234")


if __name__ == "__main__":
    _verificar_local()
    db = SessionLocal()
    try:
        borrar(db) if "--borrar" in sys.argv else crear(db)
    finally:
        db.close()
