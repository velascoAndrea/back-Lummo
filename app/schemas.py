from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nuevo: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: dict


# ── Diagnóstico ───────────────────────────────────────────────────────────────

class IniciarDiagnosticoRequest(BaseModel):
    nombre: str
    email: EmailStr
    diagnostico_id: int
    graduado: Optional[bool] = None
    grado: Optional[str] = None
    sector: Optional[str] = None


class TipoDiagnosticoIn(BaseModel):
    nombre: str
    subtitulo: Optional[str] = None
    descripcion: Optional[str] = None
    areas: Optional[str] = None   # comma-separated tags
    activo: Optional[bool] = True


class IniciarDiagnosticoResponse(BaseModel):
    resultado_id: int
    sesion_token: str
    es_cuenta_nueva: bool
    total_preguntas: int
    ya_existe: bool = False
    token_reporte: Optional[str] = None


class OpcionOut(BaseModel):
    id: int
    texto: str
    orden: int

    class Config:
        from_attributes = True


class PreguntaOut(BaseModel):
    id: int
    enunciado: str
    opciones: List[OpcionOut]

    class Config:
        from_attributes = True


class RespuestaResumen(BaseModel):
    pregunta_id: int
    respuesta_id: int
    es_correcta: bool
    respuesta_correcta_id: Optional[int] = None
    respuesta_correcta_letra: Optional[str] = None
    respuesta_correcta_texto: Optional[str] = None
    explicacion: Optional[str] = None


class PreguntasResponse(BaseModel):
    preguntas: List[PreguntaOut]
    ultima_respondida: int
    ids_respondidas: List[int] = []
    respuestas_dadas: List[RespuestaResumen] = []


class ResponderRequest(BaseModel):
    pregunta_id: int
    respuesta_id: int


class ResponderResponse(BaseModel):
    es_correcta: bool
    explicacion: Optional[str] = None
    respuesta_correcta_texto: Optional[str] = None
    respuesta_correcta_letra: Optional[str] = None
    siguiente_pregunta_id: Optional[int] = None
    es_ultima: bool


class DetalleSubtemaOut(BaseModel):
    subtema: str
    subtema_id: int
    puntaje: float
    nivel: str
    correctas: int
    total: int


class PlanOut(BaseModel):
    id: int
    nombre: str
    precio_mensual: int
    precio_anual: int
    nivel_recomendado: str
    descripcion: Optional[str] = None
    recomendado: bool = False

    class Config:
        from_attributes = True


class FinalizarResponse(BaseModel):
    nivel_global: str
    puntaje_global: float
    detalles_por_subtema: List[DetalleSubtemaOut]
    plan_recomendado: PlanOut
    token_reporte: str
    email_enviado: bool
    password_temporal: Optional[str] = None


# ── Reporte ───────────────────────────────────────────────────────────────────

class ResumenPreguntaOut(BaseModel):
    enunciado: str
    opcion_seleccionada: str
    es_correcta: bool
    opcion_correcta: str
    explicacion: str


class ReporteResponse(BaseModel):
    nivel_global: str
    puntaje_global: float
    heatmap: List[DetalleSubtemaOut]
    resumen_preguntas: List[ResumenPreguntaOut]
    plan_recomendado: PlanOut
    usuario: dict


# ── Admin ─────────────────────────────────────────────────────────────────────

class RespuestaAdminIn(BaseModel):
    texto: str
    es_correcta: bool
    orden: int
    explicacion: Optional[str] = None


class PreguntaAdminIn(BaseModel):
    subtema_id: int
    tipo_pregunta_id: int = 1
    codigo: str
    enunciado: str
    nivel: str
    respuestas: List[RespuestaAdminIn]


class RespuestaAdminUpdate(BaseModel):
    id: int
    texto: Optional[str] = None
    explicacion: Optional[str] = None


class PreguntaAdminUpdate(BaseModel):
    enunciado: Optional[str] = None
    nivel: Optional[str] = None
    activo: Optional[bool] = None
    respuestas: Optional[List[RespuestaAdminUpdate]] = None


class DiagnosticoAdminIn(BaseModel):
    tipo_diagnostico_id: int
    nombre: str
    version: str = "1.0"
    pregunta_ids: List[int]


class DiagnosticoAdminUpdate(BaseModel):
    nombre: Optional[str] = None
    version: Optional[str] = None
    activo: Optional[bool] = None
    pregunta_ids: Optional[List[int]] = None


class SubtemaAdminIn(BaseModel):
    componente_id: int
    nombre: str
    descripcion: Optional[str] = None
    orden: int = 0


class SubtemaAdminUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    orden: Optional[int] = None
