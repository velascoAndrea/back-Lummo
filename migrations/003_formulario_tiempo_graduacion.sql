-- Migración: formulario consultable, tiempo límite y año de graduación
-- Ejecutar en local (docker) y en RDS (lummo_dev / lummo_prod)

ALTER TABLE usuario ADD COLUMN IF NOT EXISTS anio_graduacion INTEGER;
ALTER TABLE diagnostico ADD COLUMN IF NOT EXISTS tiempo_limite_minutos INTEGER;
ALTER TABLE diagnostico ADD COLUMN IF NOT EXISTS instrucciones TEXT;
ALTER TABLE diag_pregunta ADD COLUMN IF NOT EXISTS mostrar_formulario BOOLEAN DEFAULT FALSE;
ALTER TABLE resultado_diag ADD COLUMN IF NOT EXISTS duracion_segundos INTEGER;

-- Seed de instrucciones PAA (solo si el diagnóstico aún no tiene instrucciones)
UPDATE diagnostico SET instrucciones =
'MATEMÁTICA

Parte I — Opción múltiple
Instrucciones: Resuelve cada problema de esta sección. Selecciona luego la única respuesta correcta. Consulta el formulario cuando sea necesario y recuerda que NO está permitido el uso de calculadora.

Parte II — Respuesta escrita
Instrucciones: Resuelve cada problema de esta sección. Luego ingresa con el teclado la única respuesta correcta. Consulta el formulario cuando sea necesario y recuerda que NO está permitido el uso de calculadora.

Si la respuesta es una fracción debe escribirse con una diagonal, así: 5/7. Si es un número mixto debe convertirse a una fracción impropia.'
WHERE instrucciones IS NULL AND (nombre ILIKE '%matem%' OR nombre ILIKE '%cuantitat%');

UPDATE diagnostico SET instrucciones =
'LENGUAJE

Parte I — Lectura
Instrucciones: Selecciona la mejor respuesta para cada ejercicio basándote únicamente en lo que las lecturas afirman o sugieren. Lee todas las opciones antes de elegir.

Parte II — Redacción
Instrucciones: Selecciona la mejor respuesta para cada ejercicio basándote únicamente en lo que las lecturas afirman o sugieren. Lee todas las opciones antes de elegir.'
WHERE instrucciones IS NULL AND (nombre ILIKE '%lectura%' OR nombre ILIKE '%redac%' OR nombre ILIKE '%lenguaje%' OR nombre ILIKE '%verbal%');

UPDATE diagnostico SET instrucciones =
'INSTRUCCIONES PAA

LENGUAJE

Parte I — Lectura
Instrucciones: Selecciona la mejor respuesta para cada ejercicio basándote únicamente en lo que las lecturas afirman o sugieren. Lee todas las opciones antes de elegir.

Parte II — Redacción
Instrucciones: Selecciona la mejor respuesta para cada ejercicio basándote únicamente en lo que las lecturas afirman o sugieren. Lee todas las opciones antes de elegir.

MATEMÁTICA

Parte I — Opción múltiple
Instrucciones: Resuelve cada problema de esta sección. Selecciona luego la única respuesta correcta. Consulta el formulario cuando sea necesario y recuerda que NO está permitido el uso de calculadora.

Parte II — Respuesta escrita
Instrucciones: Resuelve cada problema de esta sección. Luego ingresa con el teclado la única respuesta correcta. Consulta el formulario cuando sea necesario y recuerda que NO está permitido el uso de calculadora.

Si la respuesta es una fracción debe escribirse con una diagonal, así: 5/7. Si es un número mixto debe convertirse a una fracción impropia.'
WHERE instrucciones IS NULL AND nombre ILIKE '%completo%';

CREATE TABLE IF NOT EXISTS formula (
    id SERIAL PRIMARY KEY,
    diagnostico_id INTEGER REFERENCES diagnostico(id),
    nombre VARCHAR(120) NOT NULL,
    contenido TEXT,
    imagen_url VARCHAR(500),
    tip TEXT,
    orden INTEGER DEFAULT 0,
    activo BOOLEAN DEFAULT TRUE
);

-- Si la tabla ya existía sin default (creada por SQLAlchemy), asegurar el default y limpiar NULLs
ALTER TABLE formula ALTER COLUMN activo SET DEFAULT TRUE;
UPDATE formula SET activo = TRUE WHERE activo IS NULL;

-- Seed de fórmulas de prueba (formulario PAA — geometría básica)
-- Se insertan para el diagnóstico 1 solo si aún no tiene fórmulas.
INSERT INTO formula (diagnostico_id, nombre, contenido, tip, orden, activo)
SELECT seed.*, TRUE FROM (VALUES
    (1, 'Área del círculo',        'A = πr²',        'r es el radio. Si te dan el diámetro, divide entre 2.', 0),
    (1, 'Circunferencia',          'C = 2πr',        NULL, 1),
    (1, 'Área del rectángulo',     'A = ℓ · a',      'Largo por ancho.', 2),
    (1, 'Área del triángulo',      'A = ½ · b · h',  'La altura es perpendicular a la base.', 3),
    (1, 'Volumen del prisma',      'V = ℓ · a · h',  NULL, 4),
    (1, 'Volumen del cilindro',    'V = πr² · h',    NULL, 5),
    (1, 'Teorema de Pitágoras',    'c² = a² + b²',   'Solo aplica en triángulos rectángulos. c es la hipotenusa.', 6),
    (1, 'Triángulo 30°-60°-90°',   'Lados: x, √3x, 2x', 'El lado menor (x) es opuesto al ángulo de 30°.', 7),
    (1, 'Triángulo 45°-45°-90°',   'Lados: s, s, √2s',  'La hipotenusa es √2 veces el cateto.', 8)
) AS seed(diagnostico_id, nombre, contenido, tip, orden)
WHERE NOT EXISTS (SELECT 1 FROM formula WHERE diagnostico_id = 1);
