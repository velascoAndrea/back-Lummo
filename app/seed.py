"""
Seed script — carga datos iniciales si la DB está vacía.
Ejecutado automáticamente en el startup de FastAPI.
"""
from datetime import timedelta, datetime
from .database import SessionLocal
from .models import (
    Rol, TipoDiagnostico, Componente, Subtema, TipoPregunta,
    Pregunta, Respuesta, Diagnostico, DiagPregunta, Plan, Usuario,
)
from .core.security import hash_password


# ── Preguntas reales del diagnóstico PAA ─────────────────────────────────────

MATE_ARITMETICA = [
    {"id": "A1", "q": "¿Cuál es el valor de la expresión?   18 + 2³ ÷ 4 × 2 − 5", "opts": ["9", "17", "13", "21"], "ans": 1, "explanation": "Aplicando jerarquía de operaciones (PEMDAS): primero el exponente 2³ = 8; luego la división 8 ÷ 4 = 2; luego la multiplicación 2 × 2 = 4; finalmente 18 + 4 − 5 = 17."},
    {"id": "A2", "q": "En una clase hay 15 niñas y 10 niños. ¿Cuál es la razón de niñas a niños expresada en su mínima expresión?", "opts": ["3 : 2", "2 : 3", "15 : 10", "1 : 2"], "ans": 0, "explanation": "La razón niñas : niños = 15 : 10. Dividiendo entre el MCD (5): 15 ÷ 5 = 3 y 10 ÷ 5 = 2. La razón en mínima expresión es 3 : 2."},
    {"id": "A3", "q": "Una camisa cuesta Q250.00 y está rebajada un 20%. ¿Cuál es el precio final?", "opts": ["Q50.00", "Q200.00", "Q230.00", "Q300.00"], "ans": 1, "explanation": "El descuento es: 20% × 250 = 0.20 × 250 = Q50.00. Precio final = 250 − 50 = Q200.00."},
    {"id": "A4", "q": "¿Cuál de las siguientes opciones representa la propiedad conmutativa de la multiplicación?", "opts": ["a × (b + c) = a×b + a×c", "(a × b) × c = a × (b × c)", "a × b = b × a", "a × 1 = a"], "ans": 2, "explanation": "La propiedad conmutativa establece que el orden de los factores no altera el producto: a × b = b × a. La opción A es distributiva; B es asociativa; D es el elemento neutro."},
    {"id": "A5", "q": "¿En cuál punto de la recta numérica se ubica la fracción 8/3?", "opts": ["Entre 1 y 2", "Entre 2 y 3", "Entre 3 y 4", "Entre 4 y 5"], "ans": 1, "explanation": "8 ÷ 3 = 2.666... por lo tanto 8/3 se ubica entre 2 y 3 en la recta numérica."},
    {"id": "A6", "q": "¿Cuál es la notación científica del número 0.00045?", "opts": ["4.5 × 10⁻⁴", "4.5 × 10⁴", "45 × 10⁻⁵", "0.45 × 10⁻³"], "ans": 0, "explanation": "Para expresar 0.00045 en notación científica, se mueve el punto decimal 4 lugares a la derecha: 4.5 × 10⁻⁴. La opción C no cumple el formato estándar (el coeficiente debe ser ≥ 1 y < 10)."},
    {"id": "A7", "q": "¿Cuál es el mínimo común múltiplo de 12 y 18?", "opts": ["6", "36", "72", "216"], "ans": 1, "explanation": "12 = 2² × 3 y 18 = 2 × 3². El MCM toma el mayor exponente de cada factor primo: MCM = 2² × 3² = 4 × 9 = 36."},
    {"id": "A8", "q": "¿Cuál es la factorización prima de 360?", "opts": ["2² × 3 × 5²", "2³ × 3² × 5", "2 × 3³ × 5", "2⁴ × 3 × 5"], "ans": 1, "explanation": "Dividiendo: 360 ÷ 2 = 180 ÷ 2 = 90 ÷ 2 = 45 ÷ 5 = 9 = 3². Se obtiene: 2³ × 3² × 5."},
    {"id": "A9", "q": "La distancia entre dos ciudades es 347.86 km. Redondeando a la decena más cercana, ¿cuál es el estimado?", "opts": ["340 km", "347 km", "348 km", "350 km"], "ans": 3, "explanation": "Al redondear 347.86 a la decena más cercana, la cifra de las unidades es 7 ≥ 5, por lo tanto se redondea hacia arriba: 350 km."},
    {"id": "A10", "q": "¿Cuál es el valor de la expresión (2³)² ÷ 2²?", "opts": ["4", "8", "16", "32"], "ans": 2, "explanation": "(2³)² = 2⁶ = 64. Luego, 64 ÷ 2² = 64 ÷ 4 = 16."},
]

MATE_ALGEBRA = [
    {"id": "B1", "q": "Si 3x − 7 = 2x + 5, ¿cuál es el valor de x?", "opts": ["x = −2", "x = 2", "x = 12", "x = −12"], "ans": 2, "explanation": "3x − 2x = 5 + 7 → x = 12."},
    {"id": "B2", "q": "¿Cuál es la forma simplificada de 4x² − 3x + 2x² + 5x − 1?", "opts": ["6x² + 2x − 1", "2x² + 8x − 1", "6x² − 8x + 1", "6x² + 2x + 1"], "ans": 0, "explanation": "Agrupando términos semejantes: (4x² + 2x²) + (−3x + 5x) + (−1) = 6x² + 2x − 1."},
    {"id": "B3", "q": "Para f(x) = x² − 4x + 3, ¿cuáles son las raíces (ceros) de la función?", "opts": ["x = 0 y x = 4", "x = 1 y x = 3", "x = −1 y x = −3", "x = 2 y x = −1"], "ans": 1, "explanation": "Factorizando: x² − 4x + 3 = (x−1)(x−3) = 0, por lo tanto x = 1 o x = 3."},
    {"id": "B4", "q": "¿Cuál es el conjunto solución de la desigualdad 2x + 3 < 11?", "opts": ["x < 4", "x > 4", "x < 7", "x > 7"], "ans": 0, "explanation": "2x + 3 < 11 → 2x < 8 → x < 4. El conjunto solución es {x | x < 4}."},
    {"id": "B5", "q": "¿Cuál es el producto de (x + 3)(x − 5)?", "opts": ["x² − 2x − 15", "x² + 2x − 15", "x² − 2x + 15", "x² + 8x − 15"], "ans": 0, "explanation": "Usando FOIL: x·x = x²; x·(−5) = −5x; 3·x = 3x; 3·(−5) = −15. Sumando: x² + (−5x + 3x) − 15 = x² − 2x − 15."},
    {"id": "B6", "q": "¿Cuál es el valor simplificado de √(49x⁶)?", "opts": ["7x²", "7x³", "49x³", "7x⁶"], "ans": 1, "explanation": "√(49x⁶) = √49 · √(x⁶) = 7 · x^(6/2) = 7x³."},
    {"id": "B7", "q": "¿Cuál es la solución del sistema y = 2x − 1 e y = −x + 5?", "opts": ["(1, 4)", "(2, 3)", "(3, 2)", "(0, 5)"], "ans": 1, "explanation": "Igualando: 2x − 1 = −x + 5 → 3x = 6 → x = 2. Sustituyendo: y = 2(2) − 1 = 3. Solución: (2, 3)."},
    {"id": "B8", "q": "Si y varía directamente con x, y cuando x = 4 el valor de y = 20, ¿cuál es y cuando x = 7?", "opts": ["28", "35", "40", "56"], "ans": 1, "explanation": "En variación directa: y = kx. Usando x=4, y=20: k = 20/4 = 5. Para x=7: y = 5 × 7 = 35."},
    {"id": "B9", "q": "Si f(x) = 3x² − 2x + 1, ¿cuál es el valor de f(−2)?", "opts": ["9", "13", "17", "21"], "ans": 2, "explanation": "f(−2) = 3(−2)² − 2(−2) + 1 = 3(4) + 4 + 1 = 12 + 4 + 1 = 17."},
    {"id": "B10", "q": "¿Cuál es el término que falta en la sucesión: 2, 6, 18, ___, 162?", "opts": ["36", "54", "72", "81"], "ans": 1, "explanation": "La sucesión es geométrica con razón r = 6/2 = 3. El término faltante es 18 × 3 = 54."},
]

MATE_GEOMETRIA = [
    {"id": "C1", "q": "En un triángulo rectángulo, los catetos miden a = 4 y b = 3. ¿Cuál es la longitud de la hipotenusa c?", "opts": ["5", "7", "√7", "25"], "ans": 0, "explanation": "c = √(a² + b²) = √(16 + 9) = √25 = 5. Esta es la terna pitagórica clásica (3, 4, 5)."},
    {"id": "C2", "q": "Un rectángulo tiene largo = 12 cm y ancho = 7 cm. ¿Cuál es su área?", "opts": ["38 cm", "38 cm²", "84 cm²", "84 cm"], "ans": 2, "explanation": "Área del rectángulo = largo × ancho = 12 × 7 = 84 cm²."},
    {"id": "C3", "q": "Si un ángulo mide 68°, ¿cuál es la medida de su ángulo suplementario?", "opts": ["22°", "32°", "112°", "122°"], "ans": 2, "explanation": "Dos ángulos son suplementarios si suman 180°. El suplemento de 68° = 180° − 68° = 112°."},
    {"id": "C4", "q": "Un círculo tiene radio r = 5 cm. ¿Cuál es la longitud de la circunferencia? (Use π ≈ 3.1416)", "opts": ["15.71 cm", "31.42 cm", "78.54 cm", "25 cm"], "ans": 1, "explanation": "Circunferencia = 2πr = 2 × 3.1416 × 5 = 31.416 cm ≈ 31.42 cm."},
    {"id": "C5", "q": "Dos triángulos semejantes tienen un lado de 6 cm y 9 cm respectivamente. Si otro lado del primero mide 8 cm, ¿cuánto mide el correspondiente del segundo?", "opts": ["10 cm", "11 cm", "12 cm", "15 cm"], "ans": 2, "explanation": "La razón de semejanza es 9/6 = 3/2. El lado correspondiente = 8 × (3/2) = 12 cm."},
    {"id": "C6", "q": "Una caja rectangular tiene largo = 10 cm, ancho = 6 cm y alto = 4 cm. ¿Cuál es su volumen?", "opts": ["240 cm²", "240 cm³", "188 cm³", "120 cm³"], "ans": 1, "explanation": "Volumen del prisma = largo × ancho × alto = 10 × 6 × 4 = 240 cm³."},
    {"id": "C7", "q": "P(1, 2) y Q(5, 5) son dos puntos en el plano cartesiano. ¿Cuál es la distancia PQ?", "opts": ["4 unidades", "5 unidades", "7 unidades", "√7 unidades"], "ans": 1, "explanation": "d = √[(x₂−x₁)² + (y₂−y₁)²] = √[(5−1)² + (5−2)²] = √[16 + 9] = √25 = 5 unidades."},
    {"id": "C8", "q": "El punto P(3, −4) se refleja sobre el eje x. ¿Cuáles son las coordenadas de su imagen P'?", "opts": ["(−3, −4)", "(3, 4)", "(−3, 4)", "(4, 3)"], "ans": 1, "explanation": "Al reflejar sobre el eje x, la coordenada x permanece igual y la coordenada y cambia de signo: P(3, −4) → P'(3, 4)."},
    {"id": "C9", "q": "Un cilindro tiene radio r = 3 cm y altura h = 10 cm. ¿Cuál es su volumen? (Use π ≈ 3.1416)", "opts": ["94.25 cm³", "188.50 cm³", "282.74 cm³", "301.59 cm³"], "ans": 2, "explanation": "V = πr²h = 3.1416 × (3)² × 10 = 3.1416 × 9 × 10 = 282.74 cm³."},
    {"id": "C10", "q": "En un triángulo, dos ángulos miden 47° y 85°. ¿Cuánto mide el tercer ángulo?", "opts": ["38°", "48°", "52°", "58°"], "ans": 1, "explanation": "La suma de los ángulos interiores de todo triángulo es 180°. Tercer ángulo = 180° − 47° − 85° = 48°."},
]

MATE_DATOS = [
    {"id": "D1", "q": "Las calificaciones de un estudiante en cinco exámenes son: 78, 85, 92, 67 y 88. ¿Cuál es la media aritmética?", "opts": ["80", "82", "85", "88"], "ans": 1, "explanation": "Media = (78 + 85 + 92 + 67 + 88) / 5 = 410 / 5 = 82."},
    {"id": "D2", "q": "En una gráfica de calificaciones, Ciencias = 75 e Historia = 88. ¿Cuál es la diferencia entre ambas materias?", "opts": ["Matemática y Español (diferencia 10)", "Español y Ciencias (diferencia 11)", "Ciencias e Historia (diferencia 13)", "Historia y Arte (diferencia 15)"], "ans": 2, "explanation": "Ciencias = 75 e Historia = 88. Diferencia = 88 − 75 = 13 puntos."},
    {"id": "D3", "q": "El conjunto de datos es: {5, 8, 3, 8, 7, 8, 2, 6}. ¿Cuáles son la mediana y la moda?", "opts": ["Mediana = 7 y Moda = 8", "Mediana = 6.5 y Moda = 8", "Mediana = 7.5 y Moda = 6", "Mediana = 6 y Moda = 7"], "ans": 1, "explanation": "Datos ordenados: {2, 3, 5, 6, 7, 8, 8, 8}. Mediana = promedio de los dos centrales = (6+7)/2 = 6.5. Moda = 8 (aparece 3 veces)."},
    {"id": "D4", "q": "Una bolsa contiene 4 canicas rojas, 3 azules y 5 verdes. Si se extrae una al azar, ¿cuál es la probabilidad de que sea azul?", "opts": ["1/4", "1/3", "3/12", "3/7"], "ans": 2, "explanation": "Total de canicas = 4 + 3 + 5 = 12. P(azul) = 3/12 = 1/4."},
    {"id": "D5", "q": "En una gráfica de temperatura mensual, diciembre registra 17°C y enero 18°C. ¿En qué mes la temperatura fue menor?", "opts": ["Enero", "Marzo", "Noviembre", "Diciembre"], "ans": 3, "explanation": "Diciembre registra la temperatura más baja con 17°C, menor que Enero (18°C)."},
    {"id": "D6", "q": "Los pesos (en kg) de seis estudiantes son: 52, 68, 71, 49, 85, 63. ¿Cuál es el rango del conjunto?", "opts": ["33", "36", "40", "44"], "ans": 1, "explanation": "Rango = valor máximo − valor mínimo = 85 − 49 = 36."},
    {"id": "D7", "q": "Un estudiante debe elegir 2 materias electivas de entre 5 opciones. ¿De cuántas maneras puede hacerlo?", "opts": ["10", "20", "25", "120"], "ans": 0, "explanation": "Se usa combinación porque el orden no importa: C(5,2) = 5! / (2! × 3!) = (5 × 4) / (2 × 1) = 10 maneras."},
    {"id": "D8", "q": "Una gráfica circular muestra que vivienda representa el 25% del presupuesto. Si el ingreso mensual es Q10,000, ¿cuánto se destina a vivienda?", "opts": ["Q1,500", "Q2,000", "Q2,500", "Q3,500"], "ans": 2, "explanation": "Vivienda representa el 25% del presupuesto. Q10,000 × 0.25 = Q2,500."},
    {"id": "D9", "q": "Un investigador selecciona 500 estudiantes de 10 colegios para estudiar hábitos de estudio en Guatemala. ¿Cómo se denomina ese grupo de 500 estudiantes?", "opts": ["Población", "Muestra", "Parámetro", "Variable"], "ans": 1, "explanation": "La población es el conjunto completo. Los 500 estudiantes seleccionados son un subconjunto representativo llamado muestra."},
    {"id": "D10", "q": "La probabilidad de que llueva mañana es 0.35. ¿Cuál es la probabilidad de que NO llueva?", "opts": ["0.35", "0.50", "0.65", "0.70"], "ans": 2, "explanation": "La probabilidad del evento complementario es: P(no llueva) = 1 − P(llueva) = 1 − 0.35 = 0.65."},
]

LYR_VOCABULARIO = [
    {"id": "V1", "q": '"El científico observó un comportamiento extraño en la sustancia, lo que lo llevó a replantear su hipótesis." La palabra "extraño" en el contexto de la oración significa:', "opts": ["Extranjero", "Desconocido", "Poco común", "Ajeno"], "ans": 2, "explanation": 'En el contexto científico, "extraño" no alude a algo foráneo sino a algo que sale de lo esperado: poco común.'},
    {"id": "V2", "q": '"El autor plantea una crítica aguda al sistema educativo actual." La palabra "aguda" significa:', "opts": ["Dolorosa", "Intensa", "Afilada", "Superficial"], "ans": 1, "explanation": '"Aguda" modifica una crítica intelectual; en este contexto equivale a intensa, penetrante.'},
    {"id": "V3", "q": '"El público quedó impactado por la fuerza del discurso." La palabra "impactado" significa:', "opts": ["Golpeado", "Sorprendido", "Molesto", "Distraído"], "ans": 1, "explanation": 'Ante un discurso, "impactado" hace referencia a una conmoción emocional: sorprendido o profundamente afectado.'},
    {"id": "V4", "q": '"El ambiente en la sala era tenso, nadie se atrevía a hablar." La palabra "tenso" significa:', "opts": ["Rígido", "Incómodo", "Estresante", "Silencioso"], "ans": 1, "explanation": 'La clave está en "nadie se atrevía a hablar": el ambiente era de tensión social, es decir, incómodo.'},
    {"id": "V5", "q": '"...estos avances han provocado una interacción más superficial, donde se prioriza la inmediatez por sobre la profundidad de los vínculos." La palabra "superficial" significa:', "opts": ["Rápida", "Liviana", "Poco profunda", "Innecesaria"], "ans": 2, "explanation": 'El texto contrasta "superficial" con "profundidad de los vínculos", por lo que el significado contextual es poco profundo.'},
    {"id": "V6", "q": '"Su éxito no fue inmediato, sino el resultado de un proceso paulatino que permitió corregir errores." La palabra "paulatino" significa:', "opts": ["Lento", "Progresivo", "Inseguro", "Variable"], "ans": 1, "explanation": 'El texto opone "inmediato" a "paulatino", indicando que el proceso tomó tiempo y tuvo etapas. Progresivo captura ese sentido gradual.'},
    {"id": "V7", "q": '"La novela presenta una visión crítica de la sociedad contemporánea, destacando sus desigualdades y cuestionando ciertos valores." La palabra "crítica" significa:', "opts": ["Negativa", "Analítica", "Destructiva", "Reflexiva"], "ans": 3, "explanation": 'Una visión crítica en literatura implica un examen reflexivo y cuestionador de la realidad.'},
    {"id": "V8", "q": '"El científico presentó una teoría innovadora que desafiaba las ideas tradicionales." La palabra "innovadora" significa:', "opts": ["Arriesgada", "Original", "Compleja", "Moderna"], "ans": 1, "explanation": '"Innovadora" se usa en contraste con "ideas tradicionales", lo que indica novedad y originalidad.'},
    {"id": "V9", "q": '"El autor describe el fenómeno desde una perspectiva objetiva, evitando emitir juicios personales." La palabra "objetiva" significa:', "opts": ["Clara", "Imparcial", "Directa", "Concreta"], "ans": 1, "explanation": 'La clave está en "evitando emitir juicios personales": ser objetivo equivale a ser imparcial.'},
    {"id": "V10", "q": '"A pesar de las dificultades, el equipo se mantuvo persistente, trabajando constantemente hasta alcanzar sus objetivos." La palabra "persistente" significa:', "opts": ["Constante", "Terco", "Fuerte", "Paciente"], "ans": 0, "explanation": 'El texto refuerza el significado con "trabajando constantemente": persistente implica continuidad ante las dificultades.'},
]

LYR_IDEAS = [
    {"id": "I11", "q": '"El autor critica el uso excesivo de dispositivos electrónicos en niños, argumentando que limita su desarrollo social." ¿Cuál es la tesis del texto?', "opts": ["Los niños usan tecnología", "La tecnología es necesaria", "El uso excesivo de dispositivos es perjudicial", "Los niños deben estudiar más"], "ans": 2, "explanation": "La tesis es la idea central que el autor defiende. El verbo \"critica\" y el argumento de que \"limita su desarrollo\" indican que el uso excesivo es perjudicial."},
    {"id": "I12", "q": '"Aunque el plan parecía prometedor al inicio, con el tiempo se evidenciaron fallas que afectaron su desarrollo." ¿Qué se puede inferir del texto?', "opts": ["El plan fue perfecto", "El plan fracasó parcialmente", "El plan fue inmediato", "El plan no existió"], "ans": 1, "explanation": '"Se evidenciaron fallas que afectaron su desarrollo" indica que no fue exitoso en su totalidad, pero al inicio "parecía prometedor": fracaso parcial.'},
    {"id": "I13", "q": '"El avance de la tecnología ha facilitado muchas tareas cotidianas, reduciendo el tiempo necesario para realizarlas." ¿Cuál es el tema del texto?', "opts": ["El tiempo libre", "La tecnología", "Las tareas domésticas", "La eficiencia laboral"], "ans": 1, "explanation": "El tema es el asunto sobre el que trata el texto. El sujeto gramatical y conceptual es \"el avance de la tecnología\"."},
    {"id": "I14", "q": '"El uso excesivo de redes sociales ha generado preocupación... Sin embargo, también reconocen que, bien utilizadas, pueden ser herramientas educativas." ¿Cuál es la idea principal?', "opts": ["Las redes sociales son perjudiciales", "Las redes sociales tienen efectos negativos y positivos", "Los estudiantes usan mucho redes sociales", "Las redes sociales mejoran la educación"], "ans": 1, "explanation": "El texto presenta dos perspectivas: efectos negativos y positivos. La idea principal integra ambas posturas."},
    {"id": "I15", "q": '"Diversos estudios indican que la calidad del estudio es más importante que la cantidad de tiempo invertido." ¿Qué se puede inferir del texto?', "opts": ["Estudiar mucho siempre es mejor", "Estudiar poco es suficiente", "Estudiar bien es más importante que estudiar mucho", "Los estudiantes no estudian"], "ans": 2, "explanation": "La calidad supera a la cantidad. La opción B exagera; el texto no dice que estudiar poco sea suficiente."},
    {"id": "I16", "q": '"A pesar de la implementación de diversas medidas, como restricciones vehiculares y promoción del transporte público, los niveles de polución continúan siendo altos." ¿Qué está explícito en el texto?', "opts": ["Las medidas han sido totalmente efectivas", "La contaminación ha disminuido", "Existen medidas para reducir la contaminación", "El problema ya fue solucionado"], "ans": 2, "explanation": "El texto menciona explícitamente \"restricciones vehiculares y promoción del transporte público\" como medidas implementadas."},
    {"id": "I17", "q": '"La lectura fomenta la imaginación y el pensamiento crítico. A pesar de esto, muchas personas han reducido su hábito de lectura debido al uso excesivo de dispositivos." ¿Cuál es el propósito del texto?', "opts": ["Criticar la tecnología", "Promover la lectura destacando su importancia", "Explicar cómo usar dispositivos", "Describir libros"], "ans": 1, "explanation": "El texto enumera los beneficios de la lectura y lamenta su declive. El propósito es promover la lectura."},
    {"id": "I18", "q": '"El trabajo en equipo permite combinar habilidades diversas. Sin embargo, también presenta dificultades como falta de coordinación o conflictos." ¿Cuál es el mejor resumen?', "opts": ["El trabajo en equipo es bueno", "El trabajo en equipo tiene ventajas y dificultades", "Las personas trabajan juntas", "El trabajo es importante"], "ans": 1, "explanation": "El texto expone tanto los beneficios como las dificultades. El mejor resumen recoge ambas dimensiones."},
    {"id": "I19", "q": '"El desarrollo sostenible busca equilibrar el crecimiento económico con la protección del medio ambiente... el progreso no debe comprometer los recursos de las futuras generaciones." ¿Cuál es el tema?', "opts": ["La economía", "El medio ambiente", "El desarrollo sostenible", "Las generaciones futuras"], "ans": 2, "explanation": "El tema es el concepto que articula todo el texto: el desarrollo sostenible."},
    {"id": "I20", "q": '"El autor sostiene que el aprendizaje no debe limitarse al aula, sino que debe extenderse a la vida cotidiana." ¿Cuál es el propósito del texto?', "opts": ["Describir la escuela", "Limitar el aprendizaje", "Ampliar la idea de aprendizaje", "Criticar a los estudiantes"], "ans": 2, "explanation": "El autor propone extender el concepto de aprendizaje más allá del aula. El propósito es ampliar esa noción."},
]

LYR_ANALISIS = [
    {"id": "A21", "q": '"El aumento del parque automotriz ha generado congestión. Como respuesta, algunas autoridades implementaron restricciones vehiculares, lo que redujo parcialmente el problema." ¿Cuál es la relación principal?', "opts": ["Problema – solución parcial", "Comparación de ciudades", "Descripción de vehículos", "Opinión personal"], "ans": 0, "explanation": "El texto presenta un problema (congestión) y una respuesta que lo mitiga pero no lo resuelve completamente."},
    {"id": "A22", "q": '"El autor afirma que la educación debe centrarse en habilidades prácticas. Para apoyar esta idea, menciona ejemplos de sistemas educativos con resultados positivos." ¿Qué función cumplen los ejemplos?', "opts": ["Introducir un tema", "Contradecir la idea", "Apoyar la tesis", "Concluir el texto"], "ans": 2, "explanation": "Los ejemplos funcionan como evidencia que respalda la tesis del autor."},
    {"id": "A23", "q": '"Debido al uso de dispositivos electrónicos antes de dormir, muchas personas experimentan dificultades para conciliar el sueño, lo que afecta su rendimiento." ¿Cuál es la relación principal?', "opts": ["Comparación", "Causa - efecto", "Descripción", "Opinión"], "ans": 1, "explanation": "El conector \"debido a\" establece una causa (uso de dispositivos) que genera un efecto (dificultades para dormir)."},
    {"id": "A24", "q": '"En el primer párrafo se presenta el problema de contaminación. En el segundo, sus causas. En el tercero, posibles soluciones." ¿Cuál es la organización del texto?', "opts": ["Narrativa", "Problema - causas - soluciones", "Comparación", "Definición"], "ans": 1, "explanation": "La descripción corresponde a una estructura expositiva clásica: problema, causas, soluciones."},
    {"id": "A25", "q": '"El teletrabajo ha ganado popularidad gracias a avances tecnológicos. Sin embargo, también han surgido críticas: dificulta la comunicación entre equipos." ¿Qué tipo de relación predomina?', "opts": ["Causa - efecto", "Problema - solución", "Contraste", "Enumeración"], "ans": 2, "explanation": "El texto presenta dos visiones opuestas del teletrabajo. El conector \"sin embargo\" marca el contraste."},
    {"id": "A26", "q": '"A lo largo de la historia, distintas civilizaciones han desarrollado sistemas de organización social con características propias. Algunas priorizaron la igualdad; otras establecieron jerarquías marcadas." ¿Cuál es la idea principal?', "opts": ["Todas las sociedades son iguales", "Las sociedades tienen distintas formas de organización", "La historia no influye en las sociedades", "Las jerarquías son necesarias"], "ans": 1, "explanation": "El texto presenta la diversidad de sistemas de organización social como su idea central."},
    {"id": "A27", "q": '"El avance de la medicina ha mejorado la calidad de vida. Sin embargo, también ha generado nuevos desafíos como el acceso desigual a los tratamientos." ¿Qué tipo de relación presenta el texto?', "opts": ["Comparación", "Contraste", "Narración", "Definición"], "ans": 1, "explanation": "El texto contrapone los logros de la medicina con sus consecuencias problemáticas. \"Sin embargo\" introduce el contraste."},
    {"id": "A28", "q": '"Muchos consideran que el éxito depende de la suerte. Otros sostienen que es resultado del esfuerzo. Esta diferencia refleja la complejidad del concepto." ¿Qué tipo de relación predomina?', "opts": ["Causa - efecto", "Comparación de posturas", "Enumeración", "Definición"], "ans": 1, "explanation": "El texto presenta dos posturas distintas sobre el éxito. La relación es comparativa entre dos perspectivas."},
    {"id": "A29", "q": '"Aunque muchas veces se perciben como fracasos, estos retrocesos forman parte esencial del progreso." ¿Cuál es la función de la frase "aunque muchas veces se perciben como fracasos"?', "opts": ["Introducir una causa", "Establecer una comparación", "Presentar un contraste", "Dar un ejemplo"], "ans": 2, "explanation": "La conjunción \"aunque\" introduce una idea que se opone a lo que se afirma: contraste."},
    {"id": "A30", "q": '"Si bien el crecimiento económico mejora la calidad de vida, en algunos casos ha generado desigualdades. Esto ha llevado a cuestionar modelos que priorizan la producción por sobre la equidad social." ¿Cuál es la tesis implícita?', "opts": ["El crecimiento económico siempre mejora la calidad de vida", "El crecimiento económico no tiene efectos negativos", "El desarrollo económico debe considerar la equidad", "La producción es lo más importante"], "ans": 2, "explanation": "El texto implica que el crecimiento puede generar desigualdades y se cuestionan modelos que ignoran la equidad."},
]

LYR_DATOS = [
    {"id": "D31", "q": "Un estudio muestra: Estudio en línea = 4h, Redes sociales = 3h, Videojuegos = 2h, Videos y streaming = 5h. ¿Cuántas horas diarias dedican al entretenimiento (videojuegos + videos)?", "opts": ["5", "6", "7", "8"], "ans": 2, "explanation": "Videojuegos = 2 horas + Videos y streaming = 5 horas. Total = 2 + 5 = 7 horas."},
    {"id": "D32", "q": "Con la misma tabla de actividades digitales, ¿cuál afirmación está respaldada?", "opts": ["El estudio en línea es la actividad menos frecuente", "Los videojuegos ocupan más tiempo que las redes sociales", "El consumo de vídeos ocupa más tiempo que cualquier otra actividad", "Las redes sociales y videojuegos consumen el mismo tiempo"], "ans": 2, "explanation": "Vídeos y streaming = 5 horas, el valor más alto de la tabla."},
    {"id": "D33", "q": 'El texto dice: "el uso académico continúa creciendo; sin embargo, también aumentó el tiempo invertido en entretenimiento." ¿Qué se puede inferir?', "opts": ["El entretenimiento digital ha disminuido", "El uso académico es inexistente", "El tiempo de entretenimiento también ha aumentado", "Los estudiantes ya no usan redes sociales"], "ans": 2, "explanation": "El texto afirma explícitamente que \"también aumentó el tiempo invertido en entretenimiento\"."},
    {"id": "D34", "q": "Una gráfica circular muestra que la novela representa el 35% de las preferencias literarias. ¿Qué porcentaje prefiere géneros distintos a la novela?", "opts": ["35%", "45%", "55%", "65%"], "ans": 3, "explanation": "La novela representa el 35%. Los géneros distintos suman: 100% − 35% = 65%."},
    {"id": "D35", "q": "Producción en Oriente: Maíz = 2,800t, Frijol = 1,800t, Café = 3,200t. ¿En cuál región la producción de café supera a la de maíz?", "opts": ["Norte", "Sur", "Oriente", "Occidente"], "ans": 2, "explanation": "En Oriente: Café = 3,200t y Maíz = 2,800t. Es la única región donde el café supera al maíz."},
    {"id": "D36", "q": "En una gráfica de temperaturas: en marzo, Ciudad A = 22°C y Ciudad B = 21°C (diferencia 1°C). ¿En qué mes las temperaturas son más cercanas entre sí?", "opts": ["Enero", "Febrero", "Marzo", "Abril"], "ans": 2, "explanation": "En marzo la diferencia es de apenas 1°C, la menor de todos los meses."},
    {"id": "D37", "q": "País X creció de 32% a 63% en acceso a internet (2019-2023). País Y de 18% a 30%. País Z de 50% a 64%. ¿Cuál mostró el mayor crecimiento absoluto?", "opts": ["País X con 31 puntos porcentuales", "País Y con 12 puntos porcentuales", "País Z con 14 puntos porcentuales", "Países X y Z con igual crecimiento"], "ans": 0, "explanation": "País X: 63 − 32 = 31 pp. País Y: 30 − 18 = 12 pp. País Z: 64 − 50 = 14 pp. País X tiene el mayor crecimiento."},
    {"id": "D38", "q": "Diferencias entre Lenguaje y Matemáticas por departamento: A = 4pp, B = 8pp, C = 5pp, D = 6pp. ¿En cuál la diferencia es menor?", "opts": ["Departamento A", "Departamento B", "Departamento C", "Departamento D"], "ans": 0, "explanation": "El Departamento A presenta la menor diferencia: 4 puntos porcentuales."},
    {"id": "D39", "q": "Datos de emisiones: agricultura registra los valores más bajos en los tres períodos (180, 200, 175). ¿Cuál inferencia está mejor respaldada?", "opts": ["La agricultura ha sido siempre el sector con menores emisiones", "El transporte redujo sus emisiones a cero en la última década", "La industria duplicó sus emisiones entre 2000 y 2020", "Todos los sectores aumentaron sus emisiones de forma continua"], "ans": 0, "explanation": "La agricultura registra los valores más bajos en los tres períodos, lo que respalda la opción A."},
    {"id": "D40", "q": "Guatemala: el sector agrícola consume el 74% del agua y el uso doméstico el 10%. ¿Cuánto más consume el sector agrícola en comparación con el uso doméstico?", "opts": ["5 veces más", "7.4 veces más", "El doble", "64 puntos porcentuales más"], "ans": 1, "explanation": "Para calcular cuántas veces más: 74 ÷ 10 = 7.4 veces."},
]

LYR_LITERARIO = [
    {"id": "L41", "q": "El texto narra la historia de Basilio, un anciano que vive solo y recibe a un niño perdido. ¿A qué género literario pertenece?", "opts": ["Poesía lírica", "Cuento", "Crónica", "Ensayo"], "ans": 1, "explanation": "La lectura tiene características del género narrativo (cuento): narrador en tercera persona, personajes, trama con inicio, desarrollo y desenlace."},
    {"id": "L42", "q": 'En el texto sobre Basilio, el narrador conoce el futuro del niño ("Años después... aquellas palabras regresaron a él"). ¿Qué tipo de narrador predomina?', "opts": ["Narrador protagonista en primera persona", "Narrador testigo en segunda persona", "Narrador omnisciente en tercera persona", "Narrador intradiegético en primera persona"], "ans": 2, "explanation": "El narrador habla en tercera persona y conoce el futuro del niño, característica del narrador omnisciente."},
    {"id": "L43", "q": 'La expresión "el niño llegó temblando como una hoja en tormenta" es un ejemplo de:', "opts": ["Metáfora", "Personificación", "Símil", "Hipérbole"], "ans": 2, "explanation": "Un símil establece una comparación explícita mediante conectores como \"como\". La metáfora no usa conector."},
    {"id": "L44", "q": 'La expresión "en sus ojos habitaba el fuego de cien años" es un ejemplo de:', "opts": ["Símil", "Metáfora", "Onomatopeya", "Paradoja"], "ans": 1, "explanation": "Una metáfora identifica directamente dos elementos sin usar conector comparativo."},
    {"id": "L45", "q": "¿En cuál espacio se desarrolla la acción principal del texto sobre Basilio?", "opts": ["En la milpa del anciano", "En la choza de Basilio al borde del barranco", "En el pueblo donde vivían los vecinos", "En el camino por donde llegó el niño"], "ans": 1, "explanation": "La lectura sitúa la acción en \"una choza al borde del barranco\" desde la primera línea."},
    {"id": "L46", "q": "¿Qué tipo de discurso predomina en el texto sobre Basilio y el niño?", "opts": ["Argumentación", "Exposición", "Descripción", "Narración"], "ans": 3, "explanation": "El discurso narrativo cuenta una secuencia de hechos en el tiempo protagonizados por personajes."},
    {"id": "L47", "q": 'El poema "Lluvia sobre el volcán" tiene versos divididos en grupos de 4, 4 y 3. ¿Cuál es su estructura estrófica?', "opts": ["Tres estrofas de cuatro versos cada una (cuartetos)", "Dos estrofas de seis versos cada una (sextetos)", "Cuatro estrofas de tres versos cada una (tercetos)", "Una sola estrofa de once versos"], "ans": 0, "explanation": "El poema está dividido en tres grupos: 4-4-3 versos. La estructura dominante es la de tres cuartetos."},
    {"id": "L48", "q": 'En el verso "el cráter, mudo, aprende a resignarse", ¿qué figura retórica se utiliza?', "opts": ["Hipérbole", "Personificación", "Metonimia", "Símil"], "ans": 1, "explanation": '"Aprender a resignarse" es una acción exclusivamente humana que se le atribuye al cráter, un objeto inanimado: personificación.'},
    {"id": "L49", "q": 'La expresión "Duermo yo también bajo esta agua fría" apela principalmente a:', "opts": ["Una imagen visual", "Una imagen auditiva", "Una imagen táctil", "Una imagen gustativa"], "ans": 2, "explanation": "La sensación de \"agua fría\" activa el sentido del tacto."},
    {"id": "L50", "q": 'En el poema "Lluvia sobre el volcán", la voz poética dice "esperando que vuelva la alegría, / como el volcán espera el nuevo día". ¿Cuál es el tema central?', "opts": ["La descripción geográfica de un volcán en Guatemala", "La espera y la esperanza frente a la tristeza", "La crítica al ser humano por ignorar la naturaleza", "La celebración de la lluvia como fuente de vida"], "ans": 1, "explanation": "La voz poética se identifica con el volcán que espera bajo la lluvia. El tema es emocional: la esperanza sostenida en medio de la tristeza."},
]

# Mapeo código → subtema
CODIGO_SUBTEMA = {
    **{q["id"]: "Aritmética" for q in MATE_ARITMETICA},
    **{q["id"]: "Álgebra" for q in MATE_ALGEBRA},
    **{q["id"]: "Geometría" for q in MATE_GEOMETRIA},
    **{q["id"]: "Análisis de Datos y Probabilidad" for q in MATE_DATOS},
    **{q["id"]: "Vocabulario en contexto" for q in LYR_VOCABULARIO},
    **{q["id"]: "Ideas explícitas e implícitas" for q in LYR_IDEAS},
    **{q["id"]: "Análisis e inferencias" for q in LYR_ANALISIS},
    **{q["id"]: "Información cuantitativa" for q in LYR_DATOS},
    **{q["id"]: "Análisis literario" for q in LYR_LITERARIO},
}

ALL_QUESTIONS = (
    MATE_ARITMETICA + MATE_ALGEBRA + MATE_GEOMETRIA + MATE_DATOS +
    LYR_VOCABULARIO + LYR_IDEAS + LYR_ANALISIS + LYR_DATOS + LYR_LITERARIO
)


def run_seed(db):
    """Ejecuta el seed si la DB está vacía."""
    if db.query(Rol).count() > 0:
        return

    print("🌱 Ejecutando seed de datos iniciales...")

    # Roles
    rol_est = Rol(nombre="estudiante")
    rol_adm = Rol(nombre="admin")
    db.add_all([rol_est, rol_adm])
    db.flush()

    # TiposDiagnostico
    tipos = {}
    for nombre, desc in [
        ("PAA", "Prueba de Aptitud Académica — Universidad Rafael Landívar"),
        ("USAC", "Examen de Admisión — Universidad de San Carlos de Guatemala"),
        ("URL", "Examen específico — Universidad Rafael Landívar"),
        ("Mariano Gálvez", "Examen de Admisión — Universidad Mariano Gálvez"),
    ]:
        t = TipoDiagnostico(nombre=nombre, descripcion=desc)
        db.add(t)
        db.flush()
        tipos[nombre] = t

    # Componentes y Subtemas PAA
    comp_mate = Componente(tipo_diagnostico_id=tipos["PAA"].id, nombre="Matemática", orden=1)
    comp_lyr = Componente(tipo_diagnostico_id=tipos["PAA"].id, nombre="Lectura y Redacción", orden=2)
    db.add_all([comp_mate, comp_lyr])
    db.flush()

    subtemas_mate_names = [
        ("Aritmética", 1),
        ("Álgebra", 2),
        ("Geometría", 3),
        ("Análisis de Datos y Probabilidad", 4),
    ]
    subtemas_lyr_names = [
        ("Vocabulario en contexto", 1),
        ("Ideas explícitas e implícitas", 2),
        ("Análisis e inferencias", 3),
        ("Información cuantitativa", 4),
        ("Análisis literario", 5),
    ]

    subtema_map = {}
    for nombre, orden in subtemas_mate_names:
        s = Subtema(componente_id=comp_mate.id, nombre=nombre, orden=orden)
        db.add(s)
        db.flush()
        subtema_map[nombre] = s

    for nombre, orden in subtemas_lyr_names:
        s = Subtema(componente_id=comp_lyr.id, nombre=nombre, orden=orden)
        db.add(s)
        db.flush()
        subtema_map[nombre] = s

    # TipoPregunta
    tipo_preg = TipoPregunta(nombre="opcion_multiple")
    db.add(tipo_preg)
    db.flush()

    # Planes
    for nombre, precio_mensual, precio_anual, nivel, desc in [
        ("Integral",    90, 800, "bajo",  "Construye tu base desde cero con nivelación completa"),
        ("Estratégico", 70, 600, "medio", "Entrena para resolver como la PAA exige"),
        ("Dominio",     45, 400, "alto",  "Simula, ajusta y domina tu rendimiento"),
    ]:
        db.add(Plan(
            nombre=nombre,
            precio_mensual=precio_mensual,
            precio_anual=precio_anual,
            nivel_recomendado=nivel,
            descripcion=desc,
        ))

    # Las 90 preguntas reales
    pregunta_map = {}
    for qdata in ALL_QUESTIONS:
        subtema_nombre = CODIGO_SUBTEMA[qdata["id"]]
        subtema = subtema_map[subtema_nombre]
        p = Pregunta(
            subtema_id=subtema.id,
            tipo_pregunta_id=tipo_preg.id,
            codigo=qdata["id"],
            enunciado=qdata["q"],
            nivel="medio",
            activo=True,
        )
        db.add(p)
        db.flush()
        pregunta_map[qdata["id"]] = p

        for i, texto in enumerate(qdata["opts"]):
            es_correcta = (i == qdata["ans"])
            r = Respuesta(
                pregunta_id=p.id,
                texto=texto,
                es_correcta=es_correcta,
                orden=i,
                explicacion=qdata["explanation"] if es_correcta else None,
            )
            db.add(r)

    db.flush()

    # Diagnósticos PAA
    def get_preguntas(codigos):
        return [pregunta_map[c] for c in codigos if c in pregunta_map]

    codigos_mate = [q["id"] for q in MATE_ARITMETICA + MATE_ALGEBRA + MATE_GEOMETRIA + MATE_DATOS]
    codigos_lyr = [q["id"] for q in LYR_VOCABULARIO + LYR_IDEAS + LYR_ANALISIS + LYR_DATOS + LYR_LITERARIO]

    diag_mate = Diagnostico(tipo_diagnostico_id=tipos["PAA"].id, nombre="Diagnóstico PAA — Matemática v1.0", version="1.0")
    diag_lyr = Diagnostico(tipo_diagnostico_id=tipos["PAA"].id, nombre="Diagnóstico PAA — Lectura y Redacción v1.0", version="1.0")
    diag_completo = Diagnostico(tipo_diagnostico_id=tipos["PAA"].id, nombre="Diagnóstico PAA Completo v1.0", version="1.0")
    db.add_all([diag_mate, diag_lyr, diag_completo])
    db.flush()

    for i, codigo in enumerate(codigos_mate):
        db.add(DiagPregunta(diagnostico_id=diag_mate.id, pregunta_id=pregunta_map[codigo].id, orden=i))

    for i, codigo in enumerate(codigos_lyr):
        db.add(DiagPregunta(diagnostico_id=diag_lyr.id, pregunta_id=pregunta_map[codigo].id, orden=i))

    for i, codigo in enumerate(codigos_mate + codigos_lyr):
        db.add(DiagPregunta(diagnostico_id=diag_completo.id, pregunta_id=pregunta_map[codigo].id, orden=i))

    # Usuario admin
    db.flush()
    admin_user = Usuario(
        nombre="Administrador LUMMO",
        email="admin@lummo.gt",
        password_hash=hash_password("LummoAdmin2025!"),
        password_cambiado=True,
        rol_id=rol_adm.id,
        activo=True,
    )
    db.add(admin_user)

    db.commit()
    print("✅ Seed completado: 90 preguntas, 3 diagnósticos PAA, 3 planes, 1 admin cargados.")
