"""Proveedor sin IA real: costo $0, funciona sin internet y sin clave.
Útil para desarrollar el frontend y para la demo si no hay créditos. Responde con
el contenido verificado del curso («explicación de otra forma»)."""
from __future__ import annotations

from .base import AIProvider, AIReply, TutorContext


class MockProvider(AIProvider):
    name = "mock"

    def reply(self, ctx: TutorContext, student_message: str) -> AIReply:
        if ctx.alt_explanation and (ctx.extra_level or not ctx.exercise_prompt):
            text = (f"Veámoslo de otra forma: {ctx.alt_explanation} "
                    "¿Qué parte de esto se parece a lo que estás intentando?")
        elif ctx.exercise_prompt:
            text = ("Buena pregunta. Antes de seguir, ¿qué parte del ejercicio te está costando? "
                    "Cuéntamela con tus palabras.")
        else:
            text = ("¡Gracias por preguntar! Puedo explicarte cualquier parte de la lección. "
                    "¿Qué parte te gustaría repasar?")
        return AIReply(text=f"{text} (modo demo sin IA)", provider=self.name, model="mock")
