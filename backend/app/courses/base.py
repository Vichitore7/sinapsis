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

    # ---------- teoría del curso ----------
    def theory(self, with_answer: bool = False) -> Optional[dict]:
        """Fundamentos: qué es y por qué funciona, antes de practicar. Sin la respuesta
        correcta de la pregunta final, salvo que se pida (`with_answer`)."""
        t = getattr(self, "data", {}).get("fundamentos")
        if not t:
            return None
        q = t["pregunta"]
        out = {"title": t["titulo"], "intro": t["intro"],
               "cards": [{"title": c["titulo"], "text": c["texto"], "visual": c.get("visual")}
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
