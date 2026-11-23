"""Curso de fracciones: adapta el motor de fracciones (fractions_engine.py) y el
contenido de lesson.py a la interfaz común de cursos. Es el curso más completo:
barras pictóricas (CPA), predicción antes de calcular y errores con dibujo."""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Optional

from .. import fractions_engine as fe
from .. import lesson as L
from .base import Course, cpa_stages


class FractionsCourse(Course):
    transfer_skill = "suma_distinto_den"

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
        self.skills = list(fe.SKILLS)
        self.skill_names = dict(fe.SKILL_NAMES)
        self.skill_goals = {h["id"]: h.get("objetivo", "") for h in data.get("habilidades", [])}

    # ---------- ejercicios ----------
    def generate(self, skill, rng=None, avoid=None):
        return fe.generate_exercise(skill, rng or random.Random(), avoid or set())

    def load(self, data):
        return fe.Exercise.from_dict(data)

    def signature(self, ex):
        return fe.signature(ex)

    def public(self, ex):
        return ex.to_public()

    def prompt(self, ex):
        return ex.prompt()

    def evaluate(self, ex, raw):
        return fe.evaluate(ex, raw)

    def answer_forms(self, ex):
        if ex.skill == "equivalencia":
            n = ex.a * ex.target_den // ex.b
            return [str(n), f"{n}/{ex.target_den}"]
        v: Fraction = ex.answer
        forms = [f"{v.numerator}/{v.denominator}"]
        L_ = ex.common_den
        if (v * L_).denominator == 1:
            forms.append(f"{int(v * L_)}/{L_}")
        return forms

    # ---------- contenido ----------
    def explanation(self, skill):
        e = L.EXPLANATIONS[skill]
        stages = cpa_stages(e["ideas"])
        return {"title": e["title"], "body": [st["text"] for st in stages], "stages": stages,
                "why": e["why"], "visual": e.get("visual")}

    def check_question(self, skill):
        return L.CHECK_QUESTIONS[skill]

    def alt_explanation(self, skill):
        return L.OTHER_WAY[skill]

    def hints(self, ex):
        # La última pista del motor es la resolución completa: ya no se muestra
        # para el ejercicio actual (solo como ejemplo con otros números).
        return fe.hints(ex)[:-1]

    def hint_step(self, ex, i):
        return fe.hint_step(ex, i)

    def hint_visual(self, ex, i):
        return fe.hint_visual(ex, i)

    def worked_example(self, ex, rng=None):
        rng = rng or random.Random()
        other = fe.generate_exercise(ex.skill, rng, {fe.signature(ex)})
        full = fe.hints(other)
        text = full[-1].replace("Resolvamos juntos: ", "")
        return {"prompt": other.prompt(), "text": text, "visual": fe.hint_visual(other, len(full) - 1)}

    def feedback(self, skill, misconception):
        return fe.MISCONCEPTION_FEEDBACK.get(misconception or "desconocido",
                                             fe.MISCONCEPTION_FEEDBACK["desconocido"])

    def misconception_visual(self, ex, raw, misconception):
        return fe.misconception_visual(ex, raw, misconception)

    def teacher_labels(self):
        from ..teacher import MISCONCEPTIONS
        return MISCONCEPTIONS

    # ---------- predicción y reto ----------
    def wants_prediction(self, ex):
        return ex.skill == "suma_distinto_den" and not ex.story

    def prediction_for(self, ex):
        return fe.prediction_for(ex)

    def prediction_question(self, ex, pred):
        return fe.prediction_question(ex, pred)

    def prediction_feedback(self, ex, pred, choice):
        return fe.prediction_feedback(ex, pred, choice)

    def transfer(self, rng: Optional[random.Random] = None, avoid: Optional[set[str]] = None):
        return fe.generate_transfer(rng or random.Random(), avoid or set())
