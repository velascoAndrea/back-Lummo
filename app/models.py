from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float,
    DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from .database import Base


# ── Catálogo ──────────────────────────────────────────────────────────────────

class TipoDiagnostico(Base):
    __tablename__ = "tipo_diagnostico"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), unique=True, nullable=False)
    subtitulo = Column(String(200))          # e.g. "Prueba de Aptitud Académica"
    descripcion = Column(Text)
    areas = Column(Text)                     # comma-separated, e.g. "Aptitud Verbal,Cuantitativa"
    activo = Column(Boolean, default=True)
    componentes = relationship("Componente", back_populates="tipo_diagnostico")


class Componente(Base):
    __tablename__ = "componente"
    id = Column(Integer, primary_key=True)
    tipo_diagnostico_id = Column(Integer, ForeignKey("tipo_diagnostico.id"))
    nombre = Column(String(100), nullable=False)
    orden = Column(Integer, default=0)
    tipo_diagnostico = relationship("TipoDiagnostico", back_populates="componentes")
    subtemas = relationship("Subtema", back_populates="componente")


class Subtema(Base):
    __tablename__ = "subtema"
    id = Column(Integer, primary_key=True)
    componente_id = Column(Integer, ForeignKey("componente.id"))
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    orden = Column(Integer, default=0)
    componente = relationship("Componente", back_populates="subtemas")
    preguntas = relationship("Pregunta", back_populates="subtema")


class TipoPregunta(Base):
    __tablename__ = "tipo_pregunta"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(50))


class Pregunta(Base):
    __tablename__ = "pregunta"
    id = Column(Integer, primary_key=True)
    subtema_id = Column(Integer, ForeignKey("subtema.id"))
    tipo_pregunta_id = Column(Integer, ForeignKey("tipo_pregunta.id"))
    codigo = Column(String(10), unique=True)
    enunciado = Column(Text, nullable=False)
    imagen_url = Column(String(500), nullable=True)
    nivel = Column(String(10))
    activo = Column(Boolean, default=True)
    subtema = relationship("Subtema", back_populates="preguntas")
    tipo_pregunta = relationship("TipoPregunta")
    respuestas = relationship(
        "Respuesta", back_populates="pregunta",
        order_by="Respuesta.orden"
    )


class Respuesta(Base):
    __tablename__ = "respuesta"
    id = Column(Integer, primary_key=True)
    pregunta_id = Column(Integer, ForeignKey("pregunta.id"))
    texto = Column(Text, nullable=False)
    es_correcta = Column(Boolean, default=False)
    orden = Column(Integer)
    explicacion = Column(Text)
    pregunta = relationship("Pregunta", back_populates="respuestas")


class Diagnostico(Base):
    __tablename__ = "diagnostico"
    id = Column(Integer, primary_key=True)
    tipo_diagnostico_id = Column(Integer, ForeignKey("tipo_diagnostico.id"))
    nombre = Column(String(200), nullable=False)
    version = Column(String(10), default="1.0")
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    tipo_diagnostico = relationship("TipoDiagnostico")
    preguntas = relationship(
        "DiagPregunta", back_populates="diagnostico",
        order_by="DiagPregunta.orden"
    )


class DiagPregunta(Base):
    __tablename__ = "diag_pregunta"
    id = Column(Integer, primary_key=True)
    diagnostico_id = Column(Integer, ForeignKey("diagnostico.id"))
    pregunta_id = Column(Integer, ForeignKey("pregunta.id"))
    orden = Column(Integer)
    diagnostico = relationship("Diagnostico", back_populates="preguntas")
    pregunta = relationship("Pregunta")


# ── Usuario ───────────────────────────────────────────────────────────────────

class Rol(Base):
    __tablename__ = "rol"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(20), unique=True)


class Usuario(Base):
    __tablename__ = "usuario"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(200), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    password_cambiado = Column(Boolean, default=False)
    rol_id = Column(Integer, ForeignKey("rol.id"))
    creado_en = Column(DateTime, default=datetime.utcnow)
    activo = Column(Boolean, default=True)
    graduado = Column(Boolean, nullable=True)
    grado = Column(String(50), nullable=True)
    sector = Column(String(20), nullable=True)   # "publico" | "privado"
    rol = relationship("Rol")


class Plan(Base):
    __tablename__ = "plan"
    id = Column(Integer, primary_key=True)
    nombre = Column(String(50))
    precio_mensual = Column(Integer)
    precio_anual = Column(Integer)
    nivel_recomendado = Column(String(10))
    descripcion = Column(Text)
    activo = Column(Boolean, default=True)


class ResultadoDiag(Base):
    __tablename__ = "resultado_diag"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"))
    diagnostico_id = Column(Integer, ForeignKey("diagnostico.id"))
    estado = Column(String(20), default="en_progreso")
    nivel_global = Column(String(10))
    puntaje_global = Column(Float)
    iniciado_en = Column(DateTime, default=datetime.utcnow)
    finalizado_en = Column(DateTime, nullable=True)
    usuario = relationship("Usuario")
    diagnostico = relationship("Diagnostico")
    respuestas = relationship("RespuestaDiag", back_populates="resultado")
    detalles = relationship("DetalleResultado", back_populates="resultado")


class RespuestaDiag(Base):
    __tablename__ = "respuesta_diag"
    id = Column(Integer, primary_key=True)
    resultado_diag_id = Column(Integer, ForeignKey("resultado_diag.id"))
    pregunta_id = Column(Integer, ForeignKey("pregunta.id"))
    respuesta_id = Column(Integer, ForeignKey("respuesta.id"), nullable=True)
    es_correcta = Column(Boolean)
    tiempo_segundos = Column(Integer, nullable=True)
    resultado = relationship("ResultadoDiag", back_populates="respuestas")
    pregunta = relationship("Pregunta")
    respuesta = relationship("Respuesta")


class DetalleResultado(Base):
    __tablename__ = "detalle_resultado"
    id = Column(Integer, primary_key=True)
    resultado_diag_id = Column(Integer, ForeignKey("resultado_diag.id"))
    subtema_id = Column(Integer, ForeignKey("subtema.id"))
    puntaje = Column(Float)
    nivel = Column(String(10))
    correctas = Column(Integer, default=0)
    total = Column(Integer, default=0)
    resultado = relationship("ResultadoDiag", back_populates="detalles")
    subtema = relationship("Subtema")


class TokenReporte(Base):
    __tablename__ = "token_reporte"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"))
    resultado_diag_id = Column(Integer, ForeignKey("resultado_diag.id"))
    token = Column(String(36), unique=True, index=True)
    expira_en = Column(DateTime)
    usado = Column(Boolean, default=False)
    usuario = relationship("Usuario")
    resultado = relationship("ResultadoDiag")


class Terminos(Base):
    __tablename__ = "terminos"
    id = Column(Integer, primary_key=True, default=1)
    contenido = Column(Text, nullable=False)   # JSON array of {title, items[]}
    fecha_modificacion = Column(DateTime, default=datetime.utcnow)
    version = Column(String(20), default="1.0")


class Suscripcion(Base):
    __tablename__ = "suscripcion"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"))
    plan_id = Column(Integer, ForeignKey("plan.id"))
    modalidad = Column(String(10))
    estado = Column(String(20))
    inicia_en = Column(DateTime)
    vence_en = Column(DateTime)
    pago_referencia = Column(String(100), nullable=True)
    renovacion_automatica = Column(Boolean, default=False)
    usuario = relationship("Usuario")
    plan = relationship("Plan")
