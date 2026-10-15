-- Migración: cantidad de preguntas por tema (subtema) en cada diagnóstico
-- Si un tema tiene más preguntas asignadas que `cantidad`, se eligen al azar por intento.
-- Sin fila (o cantidad NULL) ⇒ se muestran todas las preguntas del tema.
-- Ejecutar en local (docker) y en RDS (lummo_dev / lummo_prod)

CREATE TABLE IF NOT EXISTS diag_tema (
    id SERIAL PRIMARY KEY,
    diagnostico_id INTEGER NOT NULL REFERENCES diagnostico(id),
    subtema_id INTEGER NOT NULL REFERENCES subtema(id),
    cantidad INTEGER,
    UNIQUE (diagnostico_id, subtema_id)
);
