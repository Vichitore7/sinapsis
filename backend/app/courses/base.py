"""Interfaz común de un curso.

El tutor (tutor.py) no sabe de fracciones ni de sumas: solo habla con un `Course`.
Cada curso decide cómo se generan y califican sus ejercicios (código determinista)
y de dónde salen sus textos (contenido revisable por docentes).
"""
from __future__ import annotations

import random
import re
from abc import ABC, abstractmethod
from typing import Any, Optional

STEP_PROMPT = "Responde este paso para seguir:"

VALIDATION_STATES = {
    "borrador": "Borrador",
    "verificacion_matematica": "Verificación matemática",
    "revision_pedagogica": "Revisión pedagógica",
    "publicada": "Publicada",
}


class Course(ABC):
    id: str
    title: str
    level: str
    description: str
    order: int
    skills: list[str]
    skill_names: dict[str, str]
    skill_goals: dict[str, str]
    cover: dict
    meta: dict
    evaluation: str
    prerequisites: list[str]
    transfer_skill: Optional[str] = None

    # ---------- ejercicios ----------
    @abstractmethod
    def generate(self, skill: str, rng: Optional[random.Random] = None,
                 avoid: Optional[set[str]] = None) -> Any: ...

    @abstractmethod
    def load(self, data: dict) -> Any: ...

    @abstractmethod
    def signature(self, ex: Any) -> str: ...

    @abstractmethod
    def public(self, ex: Any) -> dict:
        """Lo que se manda al navegador: NUNCA incluye la respuesta."""

    @abstractmethod
    def prompt(self, ex: Any) -> str: ...

    @abstractmethod
    def evaluate(self, ex: Any, raw: str): ...

    @abstractmethod
    def answer_forms(self, ex: Any) -> list[str]:
        """Formas escritas de la respuesta final (para impedir que la IA la revele)."""

    # ---------- contenido ----------
    @abstractmethod
    def explanation(self, skill: str) -> dict: ...

    @abstractmethod
    def check_question(self, skill: str) -> dict: ...

    @abstractmethod
    def alt_explanation(self, skill: str) -> str:
        """Explicación verificada «de otra forma»: base para la ayuda extra de la IA."""

    @abstractmethod
    def hints(self, ex: Any) -> list[str]:
        """Pistas progresivas. No incluyen el resultado final."""

    @abstractmethod
    def hint_step(self, ex: Any, i: int) -> Optional[dict]: ...

    def hint_visual(self, ex: Any, i: int) -> Optional[dict]:
        return None

    @abstractmethod
    def worked_example(self, ex: Any, rng: Optional[random.Random] = None) -> dict:
        """Ejemplo resuelto con OTROS números (nunca el ejercicio actual)."""

    @abstractmethod
    def feedback(self, skill: str, misconception: Optional[str]) -> str: ...

    def feedback_for(self, ex: Any, misconception: Optional[str]) -> str:
        return self.feedback(ex.skill, misconception)

    def misconception_visual(self, ex: Any, raw: str, misconception: Optional[str]) -> Optional[dict]:
        return None

    @abstractmethod
    def teacher_labels(self) -> dict[str, dict]:
        """{error: {"label", "action"}} para el panel docente."""

    # ---------- opcionales ----------
    def wants_prediction(self, ex: Any) -> bool:
        return False

    def prediction_for(self, ex: Any) -> dict:
        raise NotImplementedError

    def prediction_question(self, ex: Any, pred: dict) -> str:
        raise NotImplementedError

    def prediction_feedback(self, ex: Any, pred: dict, choice: str):
        raise NotImplementedError

    def transfer(self, rng: Optional[random.Random] = None, avoid: Optional[set[str]] = None) -> Any:
        return None

    # ---------- evaluación final ----------
    def exam_questions(self) -> list[dict]:
        """Preguntas de «por qué» de la evaluación final (con su respuesta: solo para el servidor)."""
        ev = getattr(self, "data", {}).get("evaluacion_final") or {}
        return [{"question": q["pregunta"], "options": q["opciones"], "correct": q["correcta"],
                 "feedback": q["retro"]} for q in ev.get("preguntas", [])]

    # ---------- teoría del curso ----------
    def theory(self, with_answer: bool = False) -> Optional[dict]:
        """Fundamentos: qué es y por qué funciona, antes de practicar. Sin la respuesta
        correcta de la pregunta final, salvo que se pida (`with_answer`)."""
        t = getattr(self, "data", {}).get("fundamentos")
        if not t:
            return None
        q = t["pregunta"]
        out = {"title": t["titulo"], "intro": t["intro"],
               "cards": [{"title": c["titulo"], "text": c["texto"], "visual": render_visual(c.get("visual"))}
                         for c in t["tarjetas"]],
               "question": {"question": q["pregunta"],
                            "options": [{"id": k, "text": v} for k, v in q["opciones"].items()]},
               "sources": t.get("fuentes", [])}
        if with_answer:
            out["question"].update(correct=q["correcta"], feedback=q["retro"])
        return out

    # ---------- catálogo ----------
    def summary(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "level": self.level,
            "description": self.description,
            "order": self.order,
            "cover": self.cover,
            "prerequisites": self.prerequisites,
            "skills": [{"id": s, "name": self.skill_names[s], "goal": self.skill_goals.get(s, "")}
                       for s in self.skills],
            "evaluation": self.evaluation,
            "has_theory": bool(getattr(self, "data", {}).get("fundamentos")),
            "meta": {**self.meta,
                     "estado_label": VALIDATION_STATES.get(self.meta.get("estado", ""), "Borrador")},
        }


# --------------------------------------------------------------------------
# Método Singapur (CPA): Concreto → Pictórico → Abstracto
# --------------------------------------------------------------------------
CPA_STAGES = {
    "concreto": "Con objetos",
    "pictorico": "Con un dibujo",
    "abstracto": "Con números",
}


def cpa_stages(ideas: list) -> list[dict]:
    """Las ideas de una explicación como etapas CPA. Acepta texto simple (sin etapa)
    o {"etapa", "texto", "visual"}."""
    out = []
    for idea in ideas:
        if isinstance(idea, str):
            out.append({"stage": None, "label": None, "text": idea, "visual": None})
        else:
            st = idea.get("etapa")
            out.append({"stage": st, "label": CPA_STAGES.get(st), "text": idea["texto"],
                        "visual": render_visual(idea.get("visual"))})
    return out


_INT_KEYS = {"n", "total", "repetir", "lado", "numero", "filas", "columnas", "grupos",
             "num", "den", "a", "b", "c", "d", "target_den", "group"}
BAR_STEPS = 20  # resolución del modelo de barras: 1/20 de la barra


def fill_template(spec: Any, values: Optional[dict] = None) -> Any:
    """Llena las variables {x} de un dibujo del contenido con los números del ejercicio."""
    if values is None:
        return spec
    if isinstance(spec, str):
        return spec.format(**values)
    if isinstance(spec, list):
        return [fill_template(x, values) for x in spec]
    if isinstance(spec, dict):
        out = {}
        for k, v in spec.items():
            v = fill_template(v, values)
            if k in _INT_KEYS and isinstance(v, str) and re.fullmatch(r"-?\d+", v.strip()):
                v = int(v)
            out[k] = v
        return out
    return spec


def _step5(pct: float) -> int:
    return max(10, min(100, int(round(pct / 5) * 5)))


def bar_model(spec: dict) -> dict:
    """Modelo de barras de Singapur. En el contenido cada segmento lleva su tamaño real
    (`n`), `repetir` (grupos iguales) o `resto` (lo que falta para llegar a `total`).
    Al navegador solo llegan proporciones aproximadas (`peso`, en veinteavos de la fila),
    nunca los tamaños exactos: así el dibujo no puede filtrar la respuesta."""
    rows = []
    for r in spec["filas"]:
        segs = []
        for s in r["segmentos"]:
            segs += [dict(s) for _ in range(int(s.get("repetir", 1)))]
        known = sum(int(s["n"]) for s in segs if not s.get("resto"))
        total = int(r["total"]) if r.get("total") is not None else known
        for s in segs:
            if s.get("resto"):
                s["n"] = max(total - known, 0)
        rows.append((r, segs, total))
    widest = max((t for _, _, t in rows), default=1) or 1
    out = []
    for r, segs, total in rows:
        out.append({
            "etiqueta": r.get("etiqueta"),
            "llave": r.get("llave"),
            "ancho": _step5(100 * total / widest),
            "segmentos": [{"peso": max(1, round(BAR_STEPS * int(s["n"]) / total)) if total else 1,
                           "texto": str(s.get("texto", "")), "tono": s.get("tono", "a"),
                           "hueco": bool(s.get("hueco"))} for s in segs],
        })
    return {"kind": "modelo", "filas": out, "caption": spec.get("caption")}


def render_visual(spec: Optional[dict], values: Optional[dict] = None) -> Optional[dict]:
    """Dibujo listo para el navegador: llena variables y convierte el modelo de barras."""
    if not spec:
        return None
    v = fill_template(spec, values)
    return bar_model(v) if v.get("kind") == "modelo" else v


_INT_CONTEXT = r"(?:=|\bes\b|\bson\b|\bda\b|\bdan\b|\bvale\b|\bqueda\b|\bquedan\b|resultado[^0-9]{0,15})\s*"


def leaks_answer(text: str, forms: list[str]) -> bool:
    """¿El texto revela la respuesta final? Para enteros solo cuenta si aparece como
    resultado («= 12», «es 12»), para no confundir cualquier número del texto."""
    t = (text or "").lower()
    compact = re.sub(r"\s+", "", t)
    for f in forms:
        fc = re.sub(r"\s+", "", f.lower())
        if not fc:
            continue
        if re.fullmatch(r"-?\d+", fc):
            if re.search(_INT_CONTEXT + re.escape(fc) + r"(?!\d)", t):
                return True
        elif fc in compact:
            return True
    return False
