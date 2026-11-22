"""Contenido curado de la lección «Suma de fracciones».

Este archivo es el que la docente colaboradora debería revisar: explicaciones,
criterios de dominio y textos del tutor. Los ejercicios se generan y validan en
fractions_engine.py.
"""

LESSON_ID = "fracciones-suma-v1"
LESSON_TITLE = "Suma de fracciones"

# Criterio de dominio (provisional, pendiente de revisión docente):
# - 2 aciertos seguidos usando como máximo 1 pista en cada uno, y
# - al menos uno de ellos sin ninguna pista.
MASTERY_STREAK = 2
MAX_HINTS_FOR_MASTERY = 1
MAX_EXERCISES_PER_SKILL = 6  # al llegar aquí sin dominio: sugerir pausa / repaso

# Días sin practicar a partir de los cuales se propone un repaso al regresar
REVIEW_AFTER_DAYS = 14

# Respuestas incorrectas rápidas seguidas: a partir de aquí Loop pide ir con calma
FAST_SECONDS = 5
FAST_WRONG_LIMIT = 2
# Con 2 o más intentos fallidos en el mismo ejercicio, el acierto no cuenta para el dominio
GUESS_ATTEMPTS = 2

# Explicaciones cortas: una idea por pantalla (el alumno avanza con «Siguiente»)
EXPLANATIONS = {
    "equivalencia": {
        "title": "Fracciones equivalentes",
        "body": [
            "El denominador dice en cuántos pedazos partes. El numerador, cuántos tomas.",
            "Si partes cada pedazo en 2, tienes el doble de pedazos, pero más chicos.",
            "La cantidad no cambia: 1/2 = 2/4 = 3/6.",
        ],
        "why": "Es la llave para sumar fracciones con distinto denominador.",
        "visual": {"kind": "equivalencia", "a": 1, "b": 2, "target_den": 4},
    },
    "suma_mismo_den": {
        "title": "Sumar con pedazos iguales",
        "body": [
            "Mismo denominador = pedazos del mismo tamaño.",
            "Solo cuentas pedazos: 2/7 + 3/7 = 5/7.",
            "El 7 no se suma: es el tamaño del pedazo.",
        ],
        "why": "Juntar séptimos no los convierte en catorceavos.",
        "visual": {"kind": "suma", "a": 2, "b": 7, "c": 3, "d": 7},
    },
    "suma_distinto_den": {
        "title": "Sumar con pedazos distintos",
        "body": [
            "Medios y tercios son pedazos de distinto tamaño: no se juntan así nomás.",
            "Busca un tamaño común: un número en la tabla del 2 y del 3 → el 6.",
            "1/2 = 3/6 y 1/3 = 2/6. Ahora sí: 3/6 + 2/6 = 5/6.",
        ],
        "why": "Primero igualas el tamaño de los pedazos, luego cuentas.",
        "visual": {"kind": "suma", "a": 1, "b": 2, "c": 1, "d": 3},
    },
}

# Pregunta de comprobación al final de cada explicación (reemplaza a «Entendido»).
# Las opciones incorrectas son errores típicos; cada una tiene su retroalimentación.
CHECK_QUESTIONS = {
    "equivalencia": {
        "question": "Si partes cada pedazo de 1/2 en dos, ¿qué pasa con la cantidad pintada?",
        "options": {
            "igual": "Es la misma, solo en pedazos más chicos",
            "doble": "Se hace el doble",
            "mitad": "Se hace la mitad",
        },
        "correct": "igual",
        "feedback": {
            "doble": "Hay el doble de pedazos, pero cada uno mide la mitad. ¿Cambió lo pintado?",
            "mitad": "Los pedazos son más chicos, pero ahora tienes más. Mira la barra otra vez.",
        },
    },
    "suma_mismo_den": {
        "question": "En 2/7 + 3/7, ¿qué pasa con el 7?",
        "options": {
            "igual": "Se queda igual: es el tamaño del pedazo",
            "suma": "Se suma: 7 + 7 = 14",
            "multiplica": "Se multiplica: 7 × 7 = 49",
        },
        "correct": "igual",
        "feedback": {
            "suma": "Si fueran catorceavos, los pedazos serían más chicos. ¿Cambiaron de tamaño al juntarlos?",
            "multiplica": "Al juntar pedazos no cambias su tamaño. ¿Qué indica el 7?",
        },
    },
    "suma_distinto_den": {
        "question": "¿Por qué no se pueden sumar 1/2 y 1/3 tal como están?",
        "options": {
            "tamano": "Porque los pedazos son de distinto tamaño",
            "impar": "Porque el 3 es impar",
            "si_se_puede": "Sí se puede: da 2/5",
        },
        "correct": "tamano",
        "feedback": {
            "impar": "No depende de pares o impares, sino del tamaño de cada pedazo.",
            "si_se_puede": "2/5 es menos que 1/2. ¿Juntar dos cantidades puede dar menos que una de ellas?",
        },
    },
}

# Explicación «de otra forma» (verificable por la docente). Es la base que usa la
# ayuda extra de la IA cuando ninguna pista funcionó: la IA la adapta, no inventa.
OTHER_WAY = {
    "equivalencia": (
        "Piensa en una pizza partida en 2 y otra igual partida en 4. Media pizza y dos cuartos "
        "de pizza son la misma cantidad de comida: solo cambian los cortes."
    ),
    "suma_mismo_den": (
        "Si tienes 2 rebanadas de un pastel partido en 7 y te dan 3 rebanadas más del mismo "
        "pastel, ahora tienes 5 rebanadas. Las rebanadas siguen siendo séptimos: no cambian de tamaño."
    ),
    "suma_distinto_den": (
        "Piensa en medidas: si juntas 1 metro y 30 centímetros, no tienes «31 de algo». Primero "
        "pasas todo a la misma unidad (130 centímetros) y luego sumas. Con fracciones pasa igual: "
        "primero pasas las dos a pedazos del mismo tamaño (el denominador común) y luego cuentas."
    ),
}

# ------------------------------------------------------------------------
# Estilos del tutor: mismas ideas, distinto tono. Sin llamadas a la IA.
# ------------------------------------------------------------------------
TUTOR_STYLES = {
    "paciente": {
        "label": "Profesor paciente",
        "correct": ["¡Muy bien! Lo resolviste tú.", "¡Exacto! Se nota que lo pensaste.",
                    "Correcto. Paso a paso, así se hace."],
        "wrong_intro": "No pasa nada, los errores nos enseñan dónde mirar.",
        "greeting": "Hola, {name}. Vamos a ir con calma; aquí equivocarse está permitido.",
    },
    "companero": {
        "label": "Compañero cercano",
        "correct": ["¡Eso! 🙌", "¡Lo sacaste! Bien ahí.", "¡Va! Te quedó perfecto."],
        "wrong_intro": "Uy, casi. A mí también me pasaba esto.",
        "greeting": "¡Qué onda, {name}! Échale ganas, yo te echo la mano.",
    },
    "experto": {
        "label": "Experto directo",
        "correct": ["Correcto.", "Bien.", "Correcto. Siguiente."],
        "wrong_intro": "Incorrecto.",
        "greeting": "Hola, {name}. Empecemos.",
    },
}
DEFAULT_STYLE = "paciente"

FRUSTRATION_WORDS = [
    "no entiendo nada", "me rindo", "estoy harto", "estoy harta", "odio", "no puedo",
    "es imposible", "ya no quiero", "cansad", "frustr", "aburr", "no sirvo", "soy malo",
    "soy mala", "tonto", "tonta",
]
ANSWER_REQUEST_WORDS = [
    "dame la respuesta", "dime la respuesta", "cual es la respuesta", "cuál es la respuesta",
    "solo dime", "sólo dime", "dímelo", "dimelo", "resuélvelo", "resuelvelo", "hazlo tú",
    "hazlo tu", "pásame el resultado", "pasame el resultado",
]
