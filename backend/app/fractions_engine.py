"""Motor determinista de fracciones.

Aquí vive TODO lo que decide si una respuesta es correcta. La IA nunca califica:
solo conversa. Así evitamos que el modelo "alucine" una corrección y además
ahorramos llamadas.

Responsabilidades:
- Interpretar lo que escribe el alumno ("3/4", "1 1/2", "0.5", "  5 / 6 ").
- Generar ejercicios por habilidad y VALIDARLOS antes de mostrarlos.
- Detectar errores de razonamiento típicos (misconceptions) y errores de dedo.
- Producir pistas progresivas y una resolución acompañada.
"""
from __future__ import annotations

import random
import re
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from math import gcd, lcm
from typing import Optional

# --------------------------------------------------------------------------
# Habilidades de la lección (orden = prerrequisitos)
# --------------------------------------------------------------------------
SKILLS = ["equivalencia", "suma_mismo_den", "suma_distinto_den"]

SKILL_NAMES = {
    "equivalencia": "Fracciones equivalentes",
    "suma_mismo_den": "Suma con el mismo denominador",
    "suma_distinto_den": "Suma con distinto denominador",
}

MAX_DEN = 12          # denominadores pequeños: nivel secundaria inicial
MAX_COMMON_DEN = 36   # que el denominador común no se dispare


# --------------------------------------------------------------------------
# Parseo de respuestas
# --------------------------------------------------------------------------
@dataclass
class ParsedAnswer:
    value: Fraction
    num: int   # numerador tal como lo escribió (antes de simplificar)
    den: int   # denominador tal como lo escribió

    @property
    def is_lowest_terms(self) -> bool:
        return gcd(self.num, self.den) == 1


_FRACTION = re.compile(r"^(-?\d+)\s*/\s*(-?\d+)$")
_MIXED = re.compile(r"^(-?\d+)\s+(\d+)\s*/\s*(\d+)$")
_INT = re.compile(r"^-?\d+$")
_DECIMAL = re.compile(r"^-?\d*[.,]\d+$")


def parse_answer(text: str) -> Optional[ParsedAnswer]:
    """Devuelve None si no se puede interpretar (posible error de dedo)."""
    if text is None:
        return None
    t = text.strip().replace("÷", "/").replace("\\", "/")
    t = re.sub(r"\s+", " ", t)
    if m := _FRACTION.match(t):
        n, d = int(m.group(1)), int(m.group(2))
        if d == 0:
            return None
        return ParsedAnswer(Fraction(n, d), n, d)
    if m := _MIXED.match(t):
        w, n, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if d == 0:
            return None
        sign = -1 if w < 0 else 1
        total_num = abs(w) * d + n
        return ParsedAnswer(Fraction(sign * total_num, d), sign * total_num, d)
    if _INT.match(t):
        n = int(t)
        return ParsedAnswer(Fraction(n, 1), n, 1)
    if _DECIMAL.match(t):
        f = Fraction(t.replace(",", ".")).limit_denominator(1000)
        return ParsedAnswer(f, f.numerator, f.denominator)
    return None


# --------------------------------------------------------------------------
# Ejercicios
# --------------------------------------------------------------------------
@dataclass
class Exercise:
    skill: str
    a: int
    b: int
    c: int = 0
    d: int = 0
    target_den: int = 0         # solo para equivalencia: a/b = ?/target_den
    story: Optional[str] = None  # problema en contexto (transferencia)
    id: str = field(default_factory=lambda: f"ex{random.randrange(10**8):08d}")

    # ----- datos derivados -----
    @property
    def answer(self) -> Fraction:
        if self.skill == "equivalencia":
            return Fraction(self.a, self.b)
        return Fraction(self.a, self.b) + Fraction(self.c, self.d)

    @property
    def common_den(self) -> int:
        return lcm(self.b, self.d) if self.d else self.b

    def prompt(self) -> str:
        if self.story:
            return self.story
        if self.skill == "equivalencia":
            return f"Completa la fracción equivalente: {self.a}/{self.b} = ?/{self.target_den}"
        return f"Resuelve: {self.a}/{self.b} + {self.c}/{self.d}"

    def to_public(self) -> dict:
        """Lo que se envía al navegador (sin la respuesta)."""
        data = {
            "id": self.id,
            "skill": self.skill,
            "prompt": self.prompt(),
            # En problemas verbales no mostramos barras: el alumno debe modelarlo solo.
            "visual": None if self.story else {
                "kind": "equivalencia" if self.skill == "equivalencia" else "suma",
                "a": self.a, "b": self.b, "c": self.c, "d": self.d,
                "target_den": self.target_den},
            "input_hint": "Escribe solo el numerador o la fracción completa"
            if self.skill == "equivalencia" else "Escribe una fracción, por ejemplo 3/4",
        }
        return data

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Exercise":
        return cls(**d)


class InvalidExercise(ValueError):
    pass


def validate_exercise(ex: Exercise) -> Exercise:
    """Comprueba que un ejercicio (generado por código o por IA) sea válido,
    resoluble y de nivel adecuado antes de mostrárselo a un alumno."""
    if ex.skill not in SKILLS:
        raise InvalidExercise(f"habilidad desconocida: {ex.skill}")
    if ex.b <= 0 or ex.b > MAX_DEN or ex.a <= 0:
        raise InvalidExercise("primera fracción fuera de rango")
    if ex.skill == "equivalencia":
        if ex.target_den <= ex.b or ex.target_den % ex.b != 0:
            raise InvalidExercise("el denominador objetivo debe ser múltiplo mayor que b")
        if ex.a >= ex.b:
            raise InvalidExercise("usar fracciones propias en equivalencia")
        return ex
    if ex.d <= 0 or ex.d > MAX_DEN or ex.c <= 0:
        raise InvalidExercise("segunda fracción fuera de rango")
    if ex.skill == "suma_mismo_den" and ex.b != ex.d:
        raise InvalidExercise("suma_mismo_den requiere el mismo denominador")
    if ex.skill == "suma_distinto_den" and ex.b == ex.d:
        raise InvalidExercise("suma_distinto_den requiere denominadores distintos")
    if ex.common_den > MAX_COMMON_DEN:
        raise InvalidExercise("denominador común demasiado grande para el nivel")
    if ex.a >= ex.b or ex.c >= ex.d:
        raise InvalidExercise("usar fracciones propias")
    if Fraction(ex.a, ex.b) == Fraction(ex.c, ex.d) and ex.skill == "suma_distinto_den":
        # 1/2 + 2/4 es válido pero confuso como primer ejercicio
        raise InvalidExercise("fracciones equivalentes entre sí, poco informativo")
    return ex


def generate_exercise(skill: str, rng: Optional[random.Random] = None,
                      avoid: Optional[set[str]] = None) -> Exercise:
    """Genera un ejercicio válido. `avoid` = firmas ya usadas para no repetir."""
    rng = rng or random.Random()
    avoid = avoid or set()
    for _ in range(200):
        try:
            if skill == "equivalencia":
                b = rng.randint(2, 6)
                a = rng.randint(1, b - 1)
                k = rng.randint(2, 4)
                ex = Exercise(skill, a, b, target_den=b * k)
            elif skill == "suma_mismo_den":
                b = rng.randint(3, 10)
                a = rng.randint(1, b - 2)
                c = rng.randint(1, b - 1 - a) if b - 1 - a >= 1 else 1
                ex = Exercise(skill, a, b, c, b)
            else:
                b, d = rng.sample(range(2, 9), 2)
                a = rng.randint(1, b - 1)
                c = rng.randint(1, d - 1)
                ex = Exercise(skill, a, b, c, d)
            validate_exercise(ex)
        except InvalidExercise:
            continue
        if signature(ex) not in avoid:
            return ex
    raise RuntimeError(f"no se pudo generar ejercicio para {skill}")


def signature(ex: Exercise) -> str:
    return f"{ex.skill}:{ex.a}/{ex.b}+{ex.c}/{ex.d}={ex.target_den}"


# Problemas en contexto para la comprobación de transferencia
_STORIES = [
    ("{n1} se comió {a}/{b} de una pizza y {n2} se comió {c}/{d} de la misma pizza. "
     "¿Qué fracción de la pizza se comieron entre los dos?"),
    ("Para un pastel se usan {a}/{b} de taza de azúcar y {c}/{d} de taza de leche. "
     "¿Cuántas tazas son en total?"),
    ("{n1} caminó {a}/{b} de kilómetro en la mañana y {c}/{d} de kilómetro en la tarde. "
     "¿Cuánto caminó en total?"),
    ("En una jarra hay {a}/{b} de litro de agua y {n1} agrega {c}/{d} de litro más. "
     "¿Cuánta agua hay ahora?"),
]
_NAMES = ["Ana", "Luis", "Sofía", "Diego", "Valeria", "Mateo", "Ximena", "Emiliano"]


def generate_transfer(rng: Optional[random.Random] = None,
                      avoid: Optional[set[str]] = None) -> Exercise:
    """Ejercicio de suma con distinto denominador pero en formato distinto
    (problema verbal) para comprobar comprensión independiente."""
    rng = rng or random.Random()
    ex = generate_exercise("suma_distinto_den", rng, avoid)
    n1, n2 = rng.sample(_NAMES, 2)
    ex.story = rng.choice(_STORIES).format(n1=n1, n2=n2, a=ex.a, b=ex.b, c=ex.c, d=ex.d)
    return ex


# --------------------------------------------------------------------------
# Evaluación de respuestas y detección de errores
# --------------------------------------------------------------------------
@dataclass
class Evaluation:
    correct: bool
    misconception: Optional[str]   # clave del error detectado (o None)
    unparsable: bool = False       # posible error de dedo: no cuenta como intento
    not_simplified: bool = False   # correcto pero se puede simplificar

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate(ex: Exercise, raw: str) -> Evaluation:
    if ex.skill == "equivalencia":
        return _evaluate_equivalence(ex, raw)

    parsed = parse_answer(raw)
    if parsed is None:
        return Evaluation(False, "no_interpretable", unparsable=True)

    correct = ex.answer
    if parsed.value == correct:
        return Evaluation(True, None, not_simplified=not parsed.is_lowest_terms)

    a, b, c, d = ex.a, ex.b, ex.c, ex.d
    L = ex.common_den
    v, n, den = parsed.value, parsed.num, parsed.den

    # 1) El clásico: 1/2 + 1/3 = 2/5 (suma numeradores y denominadores)
    if (n == a + c and den == b + d) or v == Fraction(a + c, b + d):
        return Evaluation(False, "suma_num_y_den")
    # 2) Multiplicó en lugar de sumar
    if v == Fraction(a * c, b * d):
        return Evaluation(False, "multiplico")
    # 3) Puso denominador común pero no convirtió los numeradores
    if n == a + c and den in (L, b * d) and b != d:
        return Evaluation(False, "no_convirtio_numeradores")
    # 4) Respuesta invertida (escribió den/num)
    if correct != 0 and v == 1 / correct:
        return Evaluation(False, "invertida")
    # 5) Usó un denominador común válido pero el numerador no cuadra: error de cálculo
    if den in (L, b * d):
        return Evaluation(False, "error_calculo")
    # 6) Solo sumó una parte / dejó una fracción sin cambiar
    if v in (Fraction(a, b), Fraction(c, d)):
        return Evaluation(False, "solo_una_fraccion")
    # 7) Posible dígito equivocado al teclear (cerca del resultado correcto)
    if _looks_like_typo(raw, correct):
        return Evaluation(False, "posible_dedo")
    return Evaluation(False, "desconocido")


def _evaluate_equivalence(ex: Exercise, raw: str) -> Evaluation:
    t = (raw or "").strip()
    expected_num = ex.a * (ex.target_den // ex.b)
    if _INT.match(t):
        n = int(t)
    else:
        parsed = parse_answer(t)
        if parsed is None:
            return Evaluation(False, "no_interpretable", unparsable=True)
        if parsed.den != ex.target_den:
            if parsed.value == Fraction(ex.a, ex.b):
                # equivalente, pero no con el denominador pedido
                return Evaluation(False, "denominador_distinto")
            return Evaluation(False, "desconocido")
        n = parsed.num
    if n == expected_num:
        return Evaluation(True, None)
    # Pensamiento aditivo: 2/3 = ?/12 -> "le sumo 9 arriba también" -> 11
    if n == ex.a + (ex.target_den - ex.b):
        return Evaluation(False, "pensamiento_aditivo")
    if n == ex.target_den // ex.b:
        return Evaluation(False, "solo_factor")
    if abs(n - expected_num) <= 1 or _looks_like_typo(t, Fraction(expected_num)):
        return Evaluation(False, "error_calculo")
    return Evaluation(False, "desconocido")


def _looks_like_typo(raw: str, correct: Fraction) -> bool:
    """Diferencia de un solo carácter respecto a la respuesta correcta escrita."""
    target = f"{correct.numerator}/{correct.denominator}" if correct.denominator != 1 \
        else str(correct.numerator)
    got = re.sub(r"\s+", "", raw or "")
    if len(got) != len(target):
        return False
    return sum(1 for x, y in zip(got, target) if x != y) == 1


# --------------------------------------------------------------------------
# Pistas progresivas. La última es la resolución completa: el tutor NO la muestra
# para el ejercicio actual, solo como «ejemplo parecido» con otros números.
# --------------------------------------------------------------------------
def hints(ex: Exercise) -> list[str]:
    a, b, c, d = ex.a, ex.b, ex.c, ex.d
    if ex.skill == "equivalencia":
        T = ex.target_den
        k = T // b
        return [
            f"Piensa en {a}/{b} como una barra partida en {b} partes. Para tener {T} partes, "
            f"cada parte se vuelve a partir. ¿Qué pasa con el tamaño de cada pedazo?",
            f"¿Por qué número multiplicas {b} para obtener {T}?",
            f"Pasaste de {b} a {T} multiplicando por {k}. Para que la fracción no cambie, "
            f"haz lo mismo con el numerador: {a} × {k} = ?",
            f"Resolvamos juntos: {b} × {k} = {T}. Lo que haces abajo, lo haces arriba: "
            f"{a} × {k} = {a * k}. Entonces {a}/{b} = {a * k}/{T}. Es la misma cantidad, "
            f"solo que en pedazos más pequeños.",
        ]
    if ex.skill == "suma_mismo_den":
        return [
            f"Las dos fracciones están en pedazos del mismo tamaño (cuartos, quintos…). "
            f"¿De qué tamaño son aquí?",
            f"Si los pedazos son iguales, solo cuentas cuántos pedazos hay en total. "
            f"¿Cuánto es {a} + {c}?",
            f"El denominador dice el TAMAÑO del pedazo y no cambia al juntarlos. "
            f"Tienes {a} + {c} pedazos de tamaño 1/{b}.",
            f"Resolvamos juntos: {a}/{b} + {c}/{b} = ({a} + {c})/{b} = {a + c}/{b}"
            + _simplify_note(Fraction(a + c, b), a + c, b),
        ]
    L = ex.common_den
    ka, kc = L // b, L // d
    return [
        f"Mira el tamaño de los pedazos: unos son de 1/{b} y otros de 1/{d}. "
        f"¿Se pueden juntar directamente pedazos de tamaños distintos?",
        f"Necesitamos un tamaño de pedazo común. Busca un número que esté en la tabla "
        f"del {b} y también en la del {d}.",
        f"Un denominador común es {L}. Convierte cada fracción: {a}/{b} = ?/{L} y "
        f"{c}/{d} = ?/{L}. (Lo que multiplicas abajo, lo multiplicas arriba.)",
        f"Resolvamos juntos: {a}/{b} = {a * ka}/{L} (multiplicamos por {ka}) y "
        f"{c}/{d} = {c * kc}/{L} (multiplicamos por {kc}). Ahora los pedazos son iguales: "
        f"{a * ka}/{L} + {c * kc}/{L} = {a * ka + c * kc}/{L}"
        + _simplify_note(Fraction(a * ka + c * kc, L), a * ka + c * kc, L),
    ]


# --------------------------------------------------------------------------
# Representación pictórica (método CPA: Concreto → Pictórico → Abstracto)
# --------------------------------------------------------------------------
# Las pistas y la retroalimentación pueden traer barras de fracciones para que el
# alumno VEA la idea antes de hacer la cuenta. Formato que pinta el frontend:
#   {"kind": "barras", "caption": str,
#    "bars": [{"num", "den", "label", "tone", "group"?}]}
# `group` = cada cuántas celdas se dibuja una línea gruesa: así se ve que
# 1/2 partida en sextos sigue siendo media barra.
MAX_VISUAL_DEN = 36


def _bar(num: int, den: int, label: str, tone: str = "a", group: int = 1) -> dict:
    return {"num": num, "den": den, "label": label, "tone": tone, "group": group}


def hint_visual(ex: Exercise, i: int) -> Optional[dict]:
    """Dibujo que acompaña la pista i (0 = primera). None si esa pista no lleva dibujo."""
    total = len(hints(ex))
    last = i == total - 1
    if ex.story and not last:
        return None  # en problemas verbales el alumno modela solo hasta la resolución acompañada
    a, b, c, d = ex.a, ex.b, ex.c, ex.d
    if ex.skill == "equivalencia":
        T, k = ex.target_den, ex.target_den // b
        if i == 2 or last:
            return {"kind": "barras",
                    "caption": f"Es la misma barra: cada pedazo de {b} se partió en {k}.",
                    "bars": [_bar(a, b, f"{a}/{b}"),
                             _bar(a * k, T, f"{a}/{b} en {T} pedazos", "a", k) if last
                             else _bar(0, T, f"La barra en {T} pedazos", "a", k)]}
        return None
    if ex.skill == "suma_mismo_den":
        if last:
            return {"kind": "barras", "caption": "Pedazos del mismo tamaño: solo se cuentan.",
                    "bars": [_bar(a, b, f"{a}/{b}"), _bar(c, b, f"{c}/{b}", "b"),
                             _bar(a + c, b, "Juntos", "ok")]}
        return None
    L = ex.common_den
    ka, kc = L // b, L // d
    if L > MAX_VISUAL_DEN:
        return None
    if i == 1:
        return {"kind": "barras",
                "caption": f"Pedazos de 1/{b} y de 1/{d} no miden lo mismo. ¿Qué tamaño cabe en los dos?",
                "bars": [_bar(a, b, f"{a}/{b}"), _bar(c, d, f"{c}/{d}", "b")]}
    if i == 2:
        return {"kind": "barras",
                "caption": f"Las mismas barras partidas en {L} pedazos iguales. Cuenta los pedazos pintados.",
                "bars": [_bar(a * ka, L, f"{a}/{b} en {L} pedazos", "a", ka),
                         _bar(c * kc, L, f"{c}/{d} en {L} pedazos", "b", kc)]}
    if last:
        return {"kind": "barras", "caption": "Ya con pedazos iguales, solo se cuentan.",
                "bars": [_bar(a * ka, L, f"{a * ka}/{L}", "a", ka),
                         _bar(c * kc, L, f"{c * kc}/{L}", "b", kc),
                         _bar(a * ka + c * kc, L, "Juntos", "ok")]}
    return None


# --------------------------------------------------------------------------
# Pistas que se RESPONDEN: cada pista intermedia trae un mini paso con casilla
# --------------------------------------------------------------------------
# Formato interno (las respuestas nunca se envían al navegador):
#   {"prompt": str, "fields": [{"label", "accept": [str]} | {"label", "multiple_of": int}
#                              | {"label", "options": [str], "accept": [str]}]}
def hint_step(ex: Exercise, i: int) -> Optional[dict]:
    a, b, c, d = ex.a, ex.b, ex.c, ex.d
    if i >= len(hints(ex)) - 1:
        return None  # la resolución acompañada no lleva paso
    if ex.skill == "equivalencia":
        T, k = ex.target_den, ex.target_den // b
        if i == 0:
            return {"prompt": "Responde este paso para seguir:",
                    "fields": [{"label": "Al volver a partir cada pedazo, los pedazos nuevos son…",
                                "options": ["Más grandes", "Más chicos"], "accept": ["más chicos"]}]}
        if i == 1:
            return {"prompt": "Responde este paso para seguir:",
                    "fields": [{"label": f"{b} × ? = {T}", "accept": [str(k)]}]}
        return None
    if ex.skill == "suma_mismo_den":
        if i == 0:
            return {"prompt": "Responde este paso para seguir:",
                    "fields": [{"label": "Cada pedazo mide 1/?", "accept": [str(b), f"1/{b}"]}]}
        if i == 1:
            return {"prompt": "Responde este paso para seguir:",
                    "fields": [{"label": f"{a} + {c} =", "accept": [str(a + c)]}]}
        return None
    L = ex.common_den
    ka, kc = L // b, L // d
    if i == 0:
        return {"prompt": "Responde este paso para seguir:",
                "fields": [{"label": "¿Se pueden juntar directamente?", "options": ["Sí", "No"],
                            "accept": ["no"]}]}
    if i == 1:
        return {"prompt": "Responde este paso para seguir:",
                "fields": [{"label": f"Un número que esté en la tabla del {b} y en la del {d}",
                            "multiple_of": L}]}
    if i == 2:
        return {"prompt": "Convierte las dos fracciones:",
                "fields": [{"label": f"{a}/{b} = ?/{L}", "accept": [str(a * ka)]},
                           {"label": f"{c}/{d} = ?/{L}", "accept": [str(c * kc)]}]}
    return None


def _norm_value(v: str) -> str:
    t = (v or "").strip().lower().replace(" ", "")
    return t.replace("í", "i")


def check_step(step: dict, values: list[str]) -> list[bool]:
    out = []
    for f, v in zip(step["fields"], values + [""] * (len(step["fields"]) - len(values))):
        nv = _norm_value(v)
        if "multiple_of" in f:
            out.append(nv.isdigit() and int(nv) > 0 and int(nv) % f["multiple_of"] == 0)
        else:
            out.append(nv in {_norm_value(x) for x in f["accept"]})
    return out


def step_solution(step: dict) -> str:
    parts = []
    for f in step["fields"]:
        ans = str(f["multiple_of"]) if "multiple_of" in f else f["accept"][0]
        parts.append(f"{f['label']} → {ans.capitalize() if f.get('options') else ans}")
    return "; ".join(parts)


def public_step(step: Optional[dict]) -> Optional[dict]:
    if not step:
        return None
    return {"prompt": step["prompt"],
            "fields": [{"label": f["label"], **({"options": f["options"]} if f.get("options") else {})}
                       for f in step["fields"]]}


# --------------------------------------------------------------------------
# Predicción antes de calcular (estimación)
# --------------------------------------------------------------------------
def prediction_for(ex: Exercise, rng: Optional[random.Random] = None) -> dict:
    """«Sin hacer cuentas: ¿el resultado será mayor o menor que X?». Variamos X para que
    no siempre sea «mayor» y el alumno tenga que pensar en la cantidad."""
    rng = rng or random.Random()
    total = ex.answer
    bigger = max(Fraction(ex.a, ex.b), Fraction(ex.c, ex.d))
    refs = [r for r in (bigger, Fraction(1), Fraction(1, 2)) if r != total]
    ref = rng.choice(refs)
    return {"ref": f"{ref.numerator}/{ref.denominator}" if ref.denominator != 1 else str(ref.numerator),
            "ref_kind": "mayor_fraccion" if ref == bigger else ("uno" if ref == 1 else "mitad"),
            "correct": "mayor" if total > ref else "menor",
            "answered": None}


def prediction_question(ex: Exercise, pred: dict) -> str:
    return f"Sin hacer cuentas: ¿{ex.a}/{ex.b} + {ex.c}/{ex.d} será mayor o menor que {pred['ref']}?"


def prediction_feedback(ex: Exercise, pred: dict, choice: str) -> tuple[bool, str, Optional[dict]]:
    ok = choice == pred["correct"]
    if ok:
        return True, "¡Buena estimación! Ahora calcula y revisa que tu resultado cuadre con eso.", None
    a, b, c, d = ex.a, ex.b, ex.c, ex.d
    bars = [_bar(a, b, f"{a}/{b}"), _bar(c, d, f"{c}/{d}", "b")]
    if pred["ref_kind"] == "mayor_fraccion":
        text = "Al juntar dos cantidades, el total tiene que ser mayor que cada una."
    elif pred["ref_kind"] == "uno":
        text = "Imagina juntar lo pintado de las dos barras: ¿alcanza a llenar una barra entera?"
    else:
        text = "Compara cada barra con la mitad: si juntas lo pintado, ¿pasa de media barra?"
    return False, text + " Ahora calcula y compruébalo.", {"kind": "barras", "caption": "", "bars": bars}


def misconception_visual(ex: Exercise, raw: str, misconception: Optional[str]) -> Optional[dict]:
    """Dibujo que hace VISIBLE por qué el razonamiento no funciona (sin dar la respuesta)."""
    a, b, c, d = ex.a, ex.b, ex.c, ex.d
    if misconception == "suma_num_y_den" and ex.skill != "equivalencia":
        n, den = a + c, b + d
        bigger = max(Fraction(a, b), Fraction(c, d))
        return {"kind": "barras",
                "caption": f"Tu resultado ({n}/{den}) no es más grande que {bigger.numerator}/"
                           f"{bigger.denominator}. Al juntar dos cantidades, ¿puede quedar menos "
                           f"que una de ellas?",
                "bars": [_bar(a, b, f"{a}/{b}"), _bar(c, d, f"{c}/{d}", "b"),
                         _bar(n, den, f"Tu resultado: {n}/{den}", "warn")]}
    if misconception == "no_convirtio_numeradores" and ex.common_den <= MAX_VISUAL_DEN:
        L = ex.common_den
        return {"kind": "barras",
                "caption": f"{a}/{b} y {a}/{L} no ocupan lo mismo: al hacer los pedazos más chicos, "
                           "se necesitan más pedazos.",
                "bars": [_bar(a, b, f"{a}/{b}"), _bar(a, L, f"{a}/{L}", "warn")]}
    if misconception == "pensamiento_aditivo" and ex.skill == "equivalencia":
        T = ex.target_den
        n = a + (T - b)
        if 0 < n <= T:
            return {"kind": "barras",
                    "caption": f"Compara las barras: {a}/{b} y {n}/{T} no son la misma cantidad.",
                    "bars": [_bar(a, b, f"{a}/{b}"), _bar(n, T, f"Tu respuesta: {n}/{T}", "warn")]}
    return None


def _simplify_note(value: Fraction, n: int, d: int) -> str:
    if gcd(n, d) != 1:
        return f", que simplificado es {value.numerator}/{value.denominator}."
    return "."


# --------------------------------------------------------------------------
# Retroalimentación por tipo de error (sin avergonzar)
# --------------------------------------------------------------------------
MISCONCEPTION_FEEDBACK = {
    "suma_num_y_den": (
        "Sumaste arriba y abajo. Pero el denominador es el tamaño del pedazo: no se suma. "
        "Mira las barras."
    ),
    "multiplico": "Parece que multiplicaste las fracciones. Aquí estamos juntando cantidades, así que sumamos.",
    "no_convirtio_numeradores": (
        "¡Buen denominador común! Pero si los pedazos son más chicos, necesitas más pedazos: "
        "falta convertir los numeradores."
    ),
    "invertida": "Tienes los números correctos pero volteados: revisa cuál va arriba y cuál abajo.",
    "error_calculo": "Vas bien encaminado; parece un error de cuentas. Revísalas.",
    "solo_una_fraccion": "Tu resultado es igual a una de las fracciones: falta juntar la otra parte.",
    "posible_dedo": "Estás muy cerca. ¿Será que se te fue un dedo al escribir? Revísalo.",
    "pensamiento_aditivo": (
        "Sumaste lo mismo arriba y abajo. Para que no cambie, hay que MULTIPLICAR."
    ),
    "solo_factor": "Encontraste por cuánto se multiplica el denominador. ¡Ahora aplica ese número al numerador!",
    "denominador_distinto": "Tu fracción sí es equivalente, pero te pedí el denominador indicado. ¿Puedes ajustarla?",
    "no_interpretable": "No logré leer tu respuesta. Escríbela como fracción, por ejemplo 3/4.",
    "desconocido": "Todavía no es el resultado. Vamos paso a paso.",
}
