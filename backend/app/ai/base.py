from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TutorContext:
    """Memoria estructurada y compacta que recibe la IA (no el historial completo)."""
    student_name: str
    tutor_style: str
    phase: str
    skill: Optional[str]
    exercise_prompt: Optional[str]
    hints_already_shown: list[str] = field(default_factory=list)
    recent_misconceptions: list[str] = field(default_factory=list)
    mastery: dict[str, float] = field(default_factory=dict)
    recent_turns: list[dict] = field(default_factory=list)  # últimos 4 mensajes como máximo
    course_title: Optional[str] = None
    extra_level: bool = False          # ayuda extra: ya usó todas las pistas o se trabó en un paso
    alt_explanation: Optional[str] = None  # explicación verificada «de otra forma» (base para adaptar)
    wrong_answers: list[str] = field(default_factory=list)  # sus intentos fallidos del ejercicio actual


@dataclass
class AIReply:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    def reply(self, ctx: TutorContext, student_message: str) -> AIReply:
        """Responde una pregunta libre del alumno sin revelar la respuesta final
        del ejercicio en curso."""


SYSTEM_PROMPT = """Eres el tutor de ThinkLoop, una plataforma que enseña a PENSAR, no a copiar respuestas. \
Hablas español de México, con calidez y sin avergonzar al alumno.

Reglas:
- Nunca des el resultado final del ejercicio en curso. Si te lo piden, explica por qué es mejor intentarlo \
y ofrece una pregunta guía o un paso pequeño.
- Responde en 1 a 4 oraciones cortas. Lenguaje sencillo, adecuado al nivel del curso (de primaria a secundaria).
- Si el alumno pregunta algo de un tema anterior que no entendió, explícalo con un ejemplo distinto al ejercicio.
- Si notas frustración o cansancio, valida la emoción y sugiere un descanso voluntario, sin presión.
- La corrección de respuestas la hace el sistema, no tú: no declares si una respuesta es correcta.
- Si la pregunta no tiene que ver con la lección, responde brevemente y regresa con amabilidad al tema.
- Si el contexto dice «Ayuda extra», el alumno ya leyó todas las pistas y sigue atorado: explica la idea \
de OTRA manera (otra representación o un ejemplo con números distintos), apóyate en la explicación \
verificada del contexto, usa sus intentos fallidos para adivinar qué no entendió y termina con una \
pregunta que lo haga dar el siguiente paso. Tampoco aquí des el resultado ni el número final.

Estilo del tutor: {style}."""

STYLE_DESCRIPTIONS = {
    "paciente": "profesor paciente: explica con calma y anima mucho",
    "companero": "compañero cercano: tono informal y amistoso, como un amigo que ya entendió el tema",
    "experto": "experto directo: breve, preciso, sin rodeos",
}


def render_context(ctx: TutorContext) -> str:
    lines = [
        f"Alumno: {ctx.student_name}",
        f"Fase de la sesión: {ctx.phase}",
    ]
    if ctx.course_title:
        lines.append(f"Curso: {ctx.course_title}")
    if ctx.extra_level:
        lines.append("Ayuda extra: ya usó todas las pistas o se trabó en un paso.")
    if ctx.skill:
        lines.append(f"Habilidad actual: {ctx.skill}")
    if ctx.exercise_prompt:
        lines.append(f"Ejercicio en curso (NO revelar el resultado): {ctx.exercise_prompt}")
    if ctx.hints_already_shown:
        lines.append("Pistas que ya vio: " + " | ".join(ctx.hints_already_shown))
    if ctx.recent_misconceptions:
        lines.append("Errores frecuentes detectados: " + ", ".join(ctx.recent_misconceptions))
    if ctx.wrong_answers:
        lines.append("Sus intentos fallidos en este ejercicio: " + ", ".join(ctx.wrong_answers))
    if ctx.alt_explanation:
        lines.append("Explicación verificada para adaptar: " + ctx.alt_explanation)
    if ctx.mastery:
        lines.append("Dominio estimado (0-1): " + ", ".join(f"{k}={v:.2f}" for k, v in ctx.mastery.items()))
    return "\n".join(lines)
