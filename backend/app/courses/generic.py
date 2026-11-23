"""Motor genérico de cursos (aritmética, raíces y álgebra inicial).

Separación entre contenido y lógica (estándar de lección ThinkLoop):
- Los TEXTOS (explicaciones, comprobación, pistas, pasos, errores frecuentes,
  retos y metadatos) viven en `content/*.json`, para que una docente los revise
  sin tocar código.
- Los NÚMEROS (generar ejercicios válidos, calcular la respuesta y detectar
  errores de razonamiento) viven aquí, en código determinista. La IA nunca califica.

Cada «tipo» declara:
- `gen(rng)`      -> variables del ejercicio (o None para volver a intentar)
- `answer(v)`     -> respuesta correcta (int o tupla)
- `detect(v, g)`  -> error de razonamiento reconocido en la respuesta g
- `secrets`       -> variables que revelan la respuesta: prohibidas en pistas y enunciados
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Optional

from ..fractions_engine import Evaluation, check_step  # noqa: F401  (check_step se reexporta)
from .base import STEP_PROMPT, Course, cpa_stages, render_visual

NAMES = ["Ana", "Luis", "Sofía", "Diego", "Valeria", "Mateo", "Ximena", "Emiliano", "Regina", "Iker"]


# --------------------------------------------------------------------------
# Ejercicio genérico
# --------------------------------------------------------------------------
@dataclass
class GenExercise:
    skill: str
    vars: dict
    story: Optional[str] = None
    id: str = field(default_factory=lambda: f"ex{random.randrange(10**8):08d}")

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------
# Interpretar respuestas
# --------------------------------------------------------------------------
def parse(kind: str, raw: str) -> Any:
    t = (raw or "").strip().lower().replace("−", "-").replace("–", "-")
    if kind == "x":
        t = re.sub(r"^x\s*=\s*", "", t)
    if kind in ("entero", "x"):
        t2 = t.replace(" ", "")
        return int(t2) if re.fullmatch(r"-?\d{1,6}", t2) else None
    if kind == "cociente_residuo":
        m = re.fullmatch(r"(\d+)\s*(?:r|res|residuo|sobra|sobran|,|y)\s*(\d+)", t)
        return (int(m[1]), int(m[2])) if m else None
    if kind == "intervalo":
        m = re.fullmatch(r"(?:entre\s*)?(\d+)\s*(?:y|a|-|,|e)\s*(\d+)", t)
        if not m:
            return None
        x, y = sorted((int(m[1]), int(m[2])))
        return (x, y)
    raise ValueError(kind)


def display(kind: str, value: Any) -> str:
    if kind == "cociente_residuo":
        return f"{value[0]} r {value[1]}"
    if kind == "intervalo":
        return f"{value[0]} y {value[1]}"
    return str(value)


def _single_int(raw: str) -> Optional[int]:
    t = (raw or "").strip().replace(" ", "")
    return int(t) if re.fullmatch(r"\d{1,6}", t) else None


def _near(g: int, ans: int, steps=(1, 10)) -> bool:
    return abs(g - ans) in steps


# --------------------------------------------------------------------------
# Tipos de ejercicio
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Tipo:
    kind: str
    gen: Callable[[random.Random], Optional[dict]]
    answer: Callable[[dict], Any]
    detect: Callable[[dict, Any], Optional[str]]
    misconceptions: tuple[str, ...]
    secrets: tuple[str, ...] = ()
    raw_detect: Optional[Callable[[dict, str], Optional[str]]] = None


# ----- sumas -----
def _suma_basica(r):
    d1, d2, u1, u2 = r.randint(1, 8), r.randint(1, 8), r.randint(0, 9), r.randint(0, 9)
    if d1 + d2 > 9 or u1 + u2 > 9 or u1 + u2 == 0:
        return None
    return dict(a=10 * d1 + u1, b=10 * d2 + u2, d1=d1, d2=d2, u1=u1, u2=u2, us=u1 + u2, ds=d1 + d2)


def _det_suma_basica(v, g):
    if g == v["u1"] + v["u2"] + v["d1"] + v["d2"]:
        return "sumo_todos"
    if _near(g, v["a"] + v["b"]):
        return "error_calculo"
    return None


def _suma_llevando(r):
    d1, d2, u1, u2 = r.randint(1, 8), r.randint(1, 8), r.randint(1, 9), r.randint(1, 9)
    if u1 + u2 < 10 or d1 + d2 + 1 > 9:
        return None
    return dict(a=10 * d1 + u1, b=10 * d2 + u2, d1=d1, d2=d2, u1=u1, u2=u2,
                us=u1 + u2, ur=u1 + u2 - 10, ds=d1 + d2 + 1)


def _det_suma_llevando(v, g):
    if g == (v["d1"] + v["d2"]) * 10 + v["ur"]:
        return "no_llevo"
    if g == int(f"{v['d1'] + v['d2']}{v['us']}"):
        return "escribio_todo"
    if _near(g, v["a"] + v["b"]):
        return "error_calculo"
    return None


# ----- restas -----
def _resta_basica(r):
    d1 = r.randint(2, 9)
    d2 = r.randint(1, d1 - 1)
    u1 = r.randint(1, 9)
    u2 = r.randint(0, u1)
    return dict(a=10 * d1 + u1, b=10 * d2 + u2, d1=d1, d2=d2, u1=u1, u2=u2, ur=u1 - u2, dr=d1 - d2)


def _det_resta_basica(v, g):
    if g == v["a"] + v["b"]:
        return "sumo"
    if _near(g, v["a"] - v["b"]):
        return "error_calculo"
    return None


def _resta_prestando(r):
    d1 = r.randint(3, 9)
    d2 = r.randint(1, d1 - 2)
    u1 = r.randint(0, 8)
    u2 = r.randint(u1 + 1, 9)
    return dict(a=10 * d1 + u1, b=10 * d2 + u2, d1=d1, d2=d2, u1=u1, u2=u2,
                d1m=d1 - 1, u1p=u1 + 10, ur=u1 + 10 - u2, dr=d1 - 1 - d2)


def _det_resta_prestando(v, g):
    if g == (v["d1"] - v["d2"]) * 10 + (v["u2"] - v["u1"]):
        return "menor_del_mayor"
    if g == (v["d1"] - v["d2"]) * 10 + v["ur"]:
        return "no_resto_prestamo"
    if g == v["a"] + v["b"]:
        return "sumo"
    if _near(g, v["a"] - v["b"]):
        return "error_calculo"
    return None


# ----- multiplicación -----
def _mult_tablas(r):
    a, b = r.randint(2, 9), r.randint(4, 9)
    return dict(a=a, b=b, a2=2 * a, a3=3 * a, cuenta=", ".join(str(a * i) for i in range(1, b + 1)))


def _det_mult_tablas(v, g):
    a, b = v["a"], v["b"]
    if g == a + b:
        return "sumo"
    if g in (a * (b - 1), a * (b + 1), (a - 1) * b, (a + 1) * b):
        return "tabla_vecina"
    if _near(g, a * b, (1, 2)):
        return "error_calculo"
    return None


def _mult_una_cifra(r):
    d, u, m = r.randint(1, 9), r.randint(1, 9), r.randint(2, 9)
    return dict(n=10 * d + u, d=d, u=u, m=m, um=u * m, dm=d * m, dm0=d * m * 10)


def _det_mult_una_cifra(v, g):
    d, u, m, n = v["d"], v["u"], v["m"], v["n"]
    if g == d * m + u * m:
        return "olvido_decena"
    if g == d * 10 + u * m:
        return "solo_unidades"
    if u * m >= 10 and g == int(f"{d * m}{u * m}"):
        return "escribio_todo"
    if g == n + m:
        return "sumo"
    if _near(g, n * m):
        return "error_calculo"
    return None


# ----- división -----
def _div_exacta(r):
    d, q = r.randint(2, 9), r.randint(2, 9)
    n = d * q
    p = 5 if q != 5 else 4
    return dict(n=n, d=d, q=q, p=p, dp=d * p, cmp="Más" if d * p > n else "Menos")


def _det_div_exacta(v, g):
    if g == v["n"] * v["d"]:
        return "multiplico"
    if g == v["n"] - v["d"]:
        return "resto"
    if _near(g, v["q"], (1,)):
        return "error_calculo"
    return None


def _div_residuo(r):
    d, q = r.randint(3, 9), r.randint(2, 9)
    rr = r.randint(1, d - 1)
    return dict(n=d * q + rr, d=d, q=q, r=rr, dq=d * q, dq1=d * (q + 1))


def _det_div_residuo(v, g):
    q, rr, d = v["q"], v["r"], v["d"]
    if g == (rr, q) and rr != q:
        return "invertidos"
    if g[1] >= d:
        return "residuo_grande"
    if g[0] == q or g[1] == rr or _near(g[0], q, (1,)):
        return "error_calculo"
    return None


def _raw_div_residuo(v, raw):
    n = _single_int(raw)
    return "sin_residuo" if n is not None and n == v["q"] else None


# ----- potencias y raíces -----
def _cuadrado(r):
    return dict(n=r.randint(3, 15))  # con 2, «2 × 2» y «2²» coinciden y el paso no distingue


def _det_cuadrado(v, g):
    n = v["n"]
    if g == 2 * n:
        return "por_dos"
    if g == n + 2:
        return "mas_dos"
    if _near(g, n * n, (1, 10, n)):
        return "error_calculo"
    return None


def _raiz_exacta(r):
    n = r.randint(2, 12)
    # El número de prueba no puede ser la respuesta, ni su cuadrado coincidir con ella (√16: 2 × 2 = 4)
    p = r.choice([x for x in range(2, 13) if 1 <= abs(x - n) <= 3 and x * x != n])
    return dict(n=n, s=n * n, p=p, p2=p * p, cmp="Más" if p * p > n * n else "Menos",
                dir="más chicos" if p > n else "más grandes")


def _det_raiz_exacta(v, g):
    if g * 2 == v["s"]:
        return "mitad"
    if _near(g, v["n"], (1,)):
        return "error_calculo"
    return None


def _raiz_estimar(r):
    k = r.randint(2, 11)
    m = r.randint(k * k + 1, (k + 1) ** 2 - 1)
    return dict(m=m, k=k, k1=k + 1, k2=k * k, k12=(k + 1) ** 2)


def _det_raiz_estimar(v, g):
    k = v["k"]
    if g in ((k - 1, k), (k + 1, k + 2)):
        return "intervalo_vecino"
    if abs(g[0] * 2 - v["m"]) <= 1 or abs(g[1] * 2 - v["m"]) <= 1:
        return "mitad"
    return None


def _raw_raiz_estimar(v, raw):
    n = _single_int(raw)
    return "solo_un_numero" if n is not None and n in (v["k"], v["k1"]) else None


# ----- álgebra -----
def _alg_sustituir(r):
    a, x, b = r.randint(2, 9), r.randint(2, 9), r.randint(1, 20)
    return dict(a=a, v=x, b=b, av=a * x)


def _det_alg_sustituir(v, g):
    a, x, b = v["a"], v["v"], v["b"]
    if g == int(f"{a}{x}") + b:
        return "concateno"
    if g == a + x + b:
        return "sumo_coef"
    if g == a * x:
        return "falto_b"
    if _near(g, a * x + b, (1,)):
        return "error_calculo"
    return None


def _alg_ec_suma(r):
    a, sol = r.randint(2, 30), r.randint(1, 30)
    if sol == a:  # el paso «¿qué número quitas?» daría justo la respuesta
        return None
    return dict(a=a, b=sol + a, sol=sol)


def _det_alg_ec_suma(v, g):
    if g == v["b"] + v["a"]:
        return "sumo"
    if _near(g, v["sol"], (1, 10)):
        return "error_calculo"
    return None


def _alg_ec_dos_pasos(r):
    a, sol, b = r.randint(2, 9), r.randint(1, 12), r.randint(1, 20)
    c = a * sol + b
    return dict(a=a, b=b, c=c, cb=c - b, sol=sol)


def _det_alg_ec_dos_pasos(v, g):
    a, b, c, cb = v["a"], v["b"], v["c"], v["cb"]
    if c % a == 0 and g == c // a:
        return "solo_divide"
    if (c + b) % a == 0 and g == (c + b) // a:
        return "suma_b"
    if g == cb - a:
        return "resto_a"
    if g == cb:
        return "falto_dividir"
    if _near(g, v["sol"], (1,)):
        return "error_calculo"
    return None


TIPOS: dict[str, Tipo] = {
    "suma_basica": Tipo("entero", _suma_basica, lambda v: v["a"] + v["b"], _det_suma_basica,
                        ("sumo_todos", "error_calculo")),
    "suma_llevando": Tipo("entero", _suma_llevando, lambda v: v["a"] + v["b"], _det_suma_llevando,
                          ("no_llevo", "escribio_todo", "error_calculo")),
    "resta_basica": Tipo("entero", _resta_basica, lambda v: v["a"] - v["b"], _det_resta_basica,
                         ("sumo", "error_calculo")),
    "resta_prestando": Tipo("entero", _resta_prestando, lambda v: v["a"] - v["b"], _det_resta_prestando,
                            ("menor_del_mayor", "no_resto_prestamo", "sumo", "error_calculo")),
    "mult_tablas": Tipo("entero", _mult_tablas, lambda v: v["a"] * v["b"], _det_mult_tablas,
                        ("sumo", "tabla_vecina", "error_calculo"), secrets=("cuenta",)),
    "mult_una_cifra": Tipo("entero", _mult_una_cifra, lambda v: v["n"] * v["m"], _det_mult_una_cifra,
                           ("olvido_decena", "solo_unidades", "escribio_todo", "sumo", "error_calculo")),
    "div_exacta": Tipo("entero", _div_exacta, lambda v: v["q"], _det_div_exacta,
                       ("multiplico", "resto", "error_calculo"), secrets=("q",)),
    "div_residuo": Tipo("cociente_residuo", _div_residuo, lambda v: (v["q"], v["r"]), _det_div_residuo,
                        ("invertidos", "residuo_grande", "sin_residuo", "error_calculo"),
                        secrets=("q", "r"), raw_detect=_raw_div_residuo),
    "cuadrado": Tipo("entero", _cuadrado, lambda v: v["n"] * v["n"], _det_cuadrado,
                     ("por_dos", "mas_dos", "error_calculo")),
    "raiz_exacta": Tipo("entero", _raiz_exacta, lambda v: v["n"], _det_raiz_exacta,
                        ("mitad", "error_calculo"), secrets=("n",)),
    "raiz_estimar": Tipo("intervalo", _raiz_estimar, lambda v: (v["k"], v["k1"]), _det_raiz_estimar,
                         ("intervalo_vecino", "mitad", "solo_un_numero"),
                         secrets=("k", "k1", "k2"), raw_detect=_raw_raiz_estimar),
    "alg_sustituir": Tipo("entero", _alg_sustituir, lambda v: v["a"] * v["v"] + v["b"], _det_alg_sustituir,
                          ("concateno", "sumo_coef", "falto_b", "error_calculo")),
    "alg_ec_suma": Tipo("x", _alg_ec_suma, lambda v: v["sol"], _det_alg_ec_suma,
                        ("sumo", "error_calculo"), secrets=("sol",)),
    "alg_ec_dos_pasos": Tipo("x", _alg_ec_dos_pasos, lambda v: v["sol"], _det_alg_ec_dos_pasos,
                             ("solo_divide", "suma_b", "resto_a", "falto_dividir", "error_calculo"),
                             secrets=("sol",)),
}

DEFAULT_FEEDBACK = {
    "error_calculo": "Vas bien encaminado; parece un error de cuentas. Revísalas con calma.",
    "posible_dedo": "Estás muy cerca. ¿Se te fue un dedo al escribir? Revísalo.",
    "desconocido": "Todavía no es el resultado. Vamos paso a paso.",
}


def _typo(raw: str, canonical: str) -> bool:
    got = re.sub(r"\s+", "", (raw or "").lower())
    target = re.sub(r"\s+", "", canonical.lower())
    return len(got) == len(target) and sum(1 for x, y in zip(got, target) if x != y) == 1


# --------------------------------------------------------------------------
# Curso genérico (lee su contenido de un JSON)
# --------------------------------------------------------------------------
class GenericCourse(Course):
    def __init__(self, data: dict):
        self.data = data
        self.id = data["id"]
        self.title = data["titulo"]
        self.level = data["nivel"]
        self.description = data["descripcion"]
        self.order = data["orden"]
        self.cover = data.get("portada", {})
        self.meta = data.get("metadatos", {})
        self.evaluation = data.get("evaluacion", "")
        self.prerequisites = data.get("prerrequisitos", [])
        self._sk = {h["id"]: h for h in data["habilidades"]}
        self.skills = [h["id"] for h in data["habilidades"]]
        self.skill_names = {h["id"]: h["nombre"] for h in data["habilidades"]}
        self.skill_goals = {h["id"]: h.get("objetivo", "") for h in data["habilidades"]}
        reto = data.get("reto_final") or {}
        self.transfer_skill = reto.get("habilidad")
        self._stories = reto.get("historias", [])

    def tipo(self, skill: str) -> Tipo:
        return TIPOS[self._sk[skill]["tipo"]]

    def _fmt(self, template: str, ex: GenExercise, extra: Optional[dict] = None) -> str:
        return template.format(**ex.vars, **(extra or {}))

    # ---------- ejercicios ----------
    def generate(self, skill, rng=None, avoid=None):
        rng = rng or random.Random()
        avoid = avoid or set()
        tipo = self.tipo(skill)
        for _ in range(500):
            v = tipo.gen(rng)
            if v is None:
                continue
            ex = GenExercise(skill, v)
            if self.signature(ex) not in avoid:
                return ex
        raise RuntimeError(f"no se pudo generar ejercicio para {skill}")

    def load(self, data):
        return GenExercise(**data)

    def signature(self, ex):
        return f"{ex.skill}:{json.dumps(ex.vars, sort_keys=True)}"

    def answer(self, ex):
        return self.tipo(ex.skill).answer(ex.vars)

    def answer_text(self, ex) -> str:
        return display(self.tipo(ex.skill).kind, self.answer(ex))

    def prompt(self, ex):
        return ex.story or self._fmt(self._sk[ex.skill]["enunciado"], ex)

    def public(self, ex):
        return {"id": ex.id, "skill": ex.skill, "prompt": self.prompt(ex), "visual": None,
                "input_hint": self._sk[ex.skill].get("ayuda_respuesta", "Escribe tu respuesta")}

    def evaluate(self, ex, raw):
        tipo = self.tipo(ex.skill)
        got = parse(tipo.kind, raw)
        if got is None:
            m = tipo.raw_detect(ex.vars, raw) if tipo.raw_detect else None
            if m:
                return Evaluation(False, m)
            return Evaluation(False, "no_interpretable", unparsable=True)
        if got == tipo.answer(ex.vars):
            return Evaluation(True, None)
        m = tipo.detect(ex.vars, got)
        if m:
            return Evaluation(False, m)
        if _typo(raw, self.answer_text(ex)):
            return Evaluation(False, "posible_dedo")
        return Evaluation(False, "desconocido")

    def answer_forms(self, ex):
        kind = self.tipo(ex.skill).kind
        ans = self.answer(ex)
        if kind == "cociente_residuo":
            return [f"{ans[0]}r{ans[1]}", f"{ans[0]}residuo{ans[1]}", f"cociente{ans[0]}",
                    f"cocientees{ans[0]}"]
        if kind == "intervalo":
            return [f"{ans[0]}y{ans[1]}", f"entre{ans[0]}y{ans[1]}"]
        return [str(ans)]

    # ---------- contenido ----------
    def explanation(self, skill):
        e = self._sk[skill]["explicacion"]
        stages = cpa_stages(e["ideas"])
        return {"title": e["titulo"], "body": [st["text"] for st in stages], "stages": stages,
                "why": e["por_que"], "visual": None}

    def check_question(self, skill):
        c = self._sk[skill]["comprobacion"]
        return {"question": c["pregunta"], "options": c["opciones"], "correct": c["correcta"],
                "feedback": c["retro"]}

    def alt_explanation(self, skill):
        return self._sk[skill]["otra_forma"]

    def hints(self, ex):
        return [self._fmt(p["texto"], ex) for p in self._sk[ex.skill]["pistas"]]

    def hint_step(self, ex, i):
        pistas = self._sk[ex.skill]["pistas"]
        if i >= len(pistas) or not pistas[i].get("paso"):
            return None
        paso = pistas[i]["paso"]
        fields = []
        for c in paso["campos"]:
            f = {"label": self._fmt(c["etiqueta"], ex), "accept": [self._fmt(a, ex) for a in c["acepta"]]}
            if c.get("opciones"):
                f["options"] = [self._fmt(o, ex) for o in c["opciones"]]
            fields.append(f)
        return {"prompt": self._fmt(paso.get("indicacion", STEP_PROMPT), ex), "fields": fields}

    def hint_visual(self, ex, i):
        """Modelo de barras (pictórico) con los números del ejercicio y «?» en lo que se busca."""
        spec = self._sk[ex.skill].get("visual_pista")
        if not spec or i != spec.get("pista", 0):
            return None
        return render_visual({k: v for k, v in spec.items() if k != "pista"}, ex.vars)

    def worked_example(self, ex, rng=None):
        rng = rng or random.Random()
        other = self.generate(ex.skill, rng, {self.signature(ex)})
        text = self._fmt(self._sk[ex.skill]["resolucion"], other, {"res": self.answer_text(other)})
        return {"prompt": self._fmt(self._sk[ex.skill]["enunciado"], other), "text": text, "visual": None}

    def feedback(self, skill, misconception):
        key = misconception or "desconocido"
        if key == "no_interpretable":
            return "No logré leer tu respuesta. " + self._sk[skill].get("ayuda_respuesta", "") + "."
        err = self._sk[skill].get("errores", {}).get(key)
        if err:
            return err["retro"]
        return DEFAULT_FEEDBACK.get(key, DEFAULT_FEEDBACK["desconocido"])

    def feedback_for(self, ex, misconception) -> str:
        """Retroalimentación con los números del ejercicio actual (sin revelar la respuesta)."""
        text = self.feedback(ex.skill, misconception)
        try:
            return text.format(**ex.vars)
        except (KeyError, IndexError):
            return text

    def teacher_labels(self):
        out = {}
        for h in self.data["habilidades"]:
            for key, err in h.get("errores", {}).items():
                if "docente" in err:
                    out[key] = {"label": err["docente"], "action": err.get("accion", "")}
        return out

    # ---------- reto final ----------
    def transfer(self, rng=None, avoid=None):
        if not self.transfer_skill or not self._stories:
            return None
        rng = rng or random.Random()
        ex = self.generate(self.transfer_skill, rng, avoid)
        n1, n2 = rng.sample(NAMES, 2)
        ex.story = rng.choice(self._stories).format(n1=n1, n2=n2, **ex.vars)
        return ex
