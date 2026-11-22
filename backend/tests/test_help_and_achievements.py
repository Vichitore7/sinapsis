"""Ayuda extra (solo cuando ya no sirvieron las pistas) y logros de razonamiento."""
from conftest import current, pass_check, register, solve_step, start, state_of

from app import tutor
from app.achievements import ACHIEVEMENTS
from app.ai.base import AIReply
from app.courses import leaks_answer


def _practice(client, course="MAT-ALG", fails=3):
    register(client, "Ayuda")
    v = start(client, course)
    s = v["session_id"]
    for _ in range(fails):
        v = client.post(f"/api/sessions/{s}/answer", json={"dont_know": True}).json()
    v = pass_check(client, s)
    assert v["phase"] == "practica"
    return s, v


def _use_all_hints(client, s):
    v = None
    while True:
        v = client.get(f"/api/sessions/{s}").json()
        if v["step"]:
            v = solve_step(client, s)
        if not v["hints"]["can_hint"]:
            return v
        v = client.post(f"/api/sessions/{s}/hint").json()


def test_extra_help_unlocks_only_after_all_hints(client):
    s, v = _practice(client)
    assert not v["help"]["ai"] and "example" not in v["actions"]
    assert client.post(f"/api/sessions/{s}/example").status_code == 400
    assert client.post(f"/api/sessions/{s}/skip").status_code == 400
    v = _use_all_hints(client, s)
    assert v["hints"]["shown"] == v["hints"]["total"]
    v = client.post(f"/api/sessions/{s}/answer", json={"answer": "999"}).json()
    assert v["help"]["stuck"] and {"message", "example", "skip"} <= set(v["actions"])

    # Ejemplo parecido: SIEMPRE con otros números
    c, ex = current(s)
    v = client.post(f"/api/sessions/{s}/example").json()
    msg = v["messages"][-1]
    assert msg["kind"] == "example" and c.prompt(ex) not in msg["text"]

    # Pregunta a Loop: el mock responde con la explicación verificada «de otra forma»
    v = client.post(f"/api/sessions/{s}/message", json={"text": "no entiendo por qué se resta"}).json()
    assert v["messages"][-1]["kind"] == "ai" and "otra forma" in v["messages"][-1]["text"]

    # Cambiar de ejercicio no penaliza y vuelve a bloquear la ayuda
    old = state_of(s)["current"]["id"]
    v = client.post(f"/api/sessions/{s}/skip").json()
    assert state_of(s)["current"]["id"] != old and not v["help"]["stuck"]


def test_ai_reply_that_leaks_the_answer_is_replaced(client, monkeypatch):
    s, v = _practice(client)
    v = _use_all_hints(client, s)
    client.post(f"/api/sessions/{s}/answer", json={"answer": "999"})
    c, ex = current(s)
    leak = f"Fácil: x = {c.answer(ex)}"

    class Leaky:
        name = "leaky"

        def reply(self, ctx, text):
            assert ctx.extra_level and ctx.alt_explanation and ctx.wrong_answers == ["999"]
            return AIReply(leak, "leaky", "test")

    monkeypatch.setattr(tutor, "get_provider", lambda: Leaky())
    v = client.post(f"/api/sessions/{s}/message", json={"text": "ayúdame"}).json()
    text = v["messages"][-1]["text"]
    assert text != leak and "otra forma" in text
    assert not leaks_answer(text, c.answer_forms(ex))


def test_leak_detector():
    assert leaks_answer("El resultado es 12.", ["12"])
    assert leaks_answer("entonces x = 7", ["7"])
    assert leaks_answer("queda 5/6", ["5/6"])
    assert not leaks_answer("Tienes 12 manzanas y 7 peras", ["5"])
    assert not leaks_answer("Piensa en 3 grupos de 4", ["12"])


def test_achievements_reward_reasoning_not_quantity(client):
    ids = {a["id"] for a in ACHIEVEMENTS}
    assert "detective" in ids and not any(w in " ".join(a["desc"] for a in ACHIEVEMENTS)
                                          for w in ("10 ejercicios", "100", "racha"))
    s, v = _practice(client, "MAT-SUMA", fails=2)
    got = {a["id"]: a["earned"] for a in client.get("/api/me/achievements").json()}
    assert got["valiente"] and not got["detective"]
    # Se equivoca y corrige el MISMO ejercicio sin pedir pista -> detective
    client.post(f"/api/sessions/{s}/answer", json={"answer": "1"})
    c, ex = current(s)
    client.post(f"/api/sessions/{s}/answer", json={"answer": c.answer_text(ex)})
    got = {a["id"]: a["earned"] for a in client.get("/api/me/achievements").json()}
    assert got["detective"]
    # Pausa y regresa a resolver -> pausa sabia
    client.post(f"/api/sessions/{s}/pause")
    v = start(client, "MAT-SUMA")
    c, ex = current(s)
    client.post(f"/api/sessions/{s}/answer", json={"answer": c.answer_text(ex)})
    got = {a["id"]: a["earned"] for a in client.get("/api/me/achievements").json()}
    assert got["descanso"]
