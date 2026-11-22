"""Proveedor Claude (SDK oficial de Anthropic)."""
from __future__ import annotations

import logging

import anthropic

from .base import (STYLE_DESCRIPTIONS, SYSTEM_PROMPT, AIProvider, AIReply, TutorContext,
                   render_context)

log = logging.getLogger(__name__)

FALLBACK_TEXT = ("Ahorita no pude conectarme con el tutor de IA. Mientras tanto, puedes pedir "
                 "una pista o intentar el siguiente paso; ¡el sistema sigue revisando tus respuestas!")


class ClaudeProvider(AIProvider):
    name = "claude"

    def __init__(self, model: str = "claude-opus-5-5"):
        self.model = model
        # Lee ANTHROPIC_API_KEY del entorno. La clave nunca llega al navegador.
        self.client = anthropic.Anthropic(timeout=30.0, max_retries=2)

    def reply(self, ctx: TutorContext, student_message: str) -> AIReply:
        system = SYSTEM_PROMPT.format(style=STYLE_DESCRIPTIONS.get(ctx.tutor_style, ctx.tutor_style))
        messages = [m for m in ctx.recent_turns[-4:] if m.get("role") in ("user", "assistant")]
        messages.append({
            "role": "user",
            "content": f"<contexto>\n{render_context(ctx)}\n</contexto>\n\nMensaje del alumno: {student_message}",
        })
        try:
            kwargs = dict(
                model=self.model,
                max_tokens=2000,
                system=system,
                messages=messages,
                # Respuestas cortas de chat: esfuerzo bajo = menos tokens y menos latencia.
                output_config={"effort": "low"},
            )
            if self.model in ("claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-2"):
                # Si un filtro de seguridad rechaza la petición, la API reintenta
                # automáticamente con un modelo alterno.
                response = self.client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
            else:
                response = self.client.messages.create(**kwargs)
        except anthropic.AuthenticationError:
            log.error("ANTHROPIC_API_KEY inválida o ausente")
            return AIReply(FALLBACK_TEXT, self.name, self.model)
        except anthropic.RateLimitError:
            log.warning("Límite de peticiones alcanzado")
            return AIReply(FALLBACK_TEXT, self.name, self.model)
        except anthropic.APIStatusError as e:
            log.error("Error de la API de Claude: %s %s", e.status_code, e.message)
            return AIReply(FALLBACK_TEXT, self.name, self.model)
        except anthropic.APIConnectionError:
            log.warning("Sin conexión con la API de Claude")
            return AIReply(FALLBACK_TEXT, self.name, self.model)

        if response.stop_reason == "refusal":
            text = "Mejor enfoquémonos en la lección. ¿En qué paso del ejercicio te quedaste?"
        else:
            text = "".join(b.text for b in response.content if b.type == "text").strip() or FALLBACK_TEXT
        return AIReply(text=text, provider=self.name, model=response.model,
                       input_tokens=response.usage.input_tokens,
                       output_tokens=response.usage.output_tokens)
