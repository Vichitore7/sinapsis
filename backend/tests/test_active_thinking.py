"""Que leer no sea opcional: comprobación, predicción, pasos en las pistas y prisa."""
from conftest import current, register, solve_step, start, state_of

from app import db
from app.fractions_engine import Exercise, check_step, hint_step, prediction_for
from app.lesson import CHECK_QUESTIONS


def _to_explanation(client, skill_failures=3):
    register(client, "Val")
    v = start(client)
    s = v["session_id"]
    for _ in range(skill_failures):
        v = client.post(f"/api/sessions/{s}/answer", json={"dont_know": True}).json()
    return s, v


def test_explanation_requires_check_question(client):
    s, v = _to_explanation(client)
    assert v["phase"] == "explicacion" and v["actions"] == ["check", "message", "pause"]
    chk = v["explanation"]["check"]
    assert len(chk["options"]) == 3 and "correct" not in chk
    wrong = next(o["id"] for o in chk["options"] if o["id"] != CHECK_QUESTIONS["equivalencia"]["correct"])
    v = client.post(f"/api/sessions/{s}/check", json={"option": wrong}).json()
    assert v["phase"] == "explicacion" and v["messages"][-1]["kind"] == "feedback_wrong"
    v = client.post(f"/api/sessions/{s}/check", json={"option": CHECK_QUESTIONS["equivalencia"]["correct"]}).json()
    assert v["phase"] == "practica"
    # El viejo atajo «Entendido» ya no existe
    assert client.post(f"/api/sessions/{s}/continue").status_code in (404, 405)


def test_prediction_blocks_answer_until_made():
    ex = Exercise("suma_distinto_den", 1, 2, 1, 3)
    for _ in range(20):
        p = prediction_for(ex)
        assert p["correct"] == ("mayor" if ex.answer > eval(p["ref"]) else "menor")


def test_prediction_flow(client):
    s, v = _to_explanation(client)
    st = state_of(s)
    # Forzamos la habilidad de distinto denominador para probar la predicción
    st["skill"] = "suma_distinto_den"
    db.save_session(s, st)
    v = client.post(f"/api/sessions/{s}/check", json={"option": "tamano"}).json()
    assert v["prediction"] and v["actions"][0] == "predict"
    assert client.post(f"/api/sessions/{s}/answer", json={"answer": "1/2"}).status_code == 400
    pred = state_of(s)["prediction"]
    wrong = "menor" if pred["correct"] == "mayor" else "mayor"
    v = client.post(f"/api/sessions/{s}/predict", json={"choice": wrong}).json()
    assert v["prediction"] is None and "answer" in v["actions"]
    assert v["messages"][-1]["kind"] == "feedback_wrong"


def test_every_hint_but_the_last_must_be_answered(client):
    s, v = _to_explanation(client)
    v = client.post(f"/api/sessions/{s}/check", json={"option": "igual"}).json()
    v = client.post(f"/api/sessions/{s}/hint").json()   # pista 1: ¿los pedazos son más chicos?
    assert v["step"] and v["step"]["fields"][0]["options"] and not v["hints"]["can_hint"]
    assert client.post(f"/api/sessions/{s}/hint").status_code == 400
    v = client.post(f"/api/sessions/{s}/step", json={"values": ["Más grandes"]}).json()
    assert v["step"]  # un error: sigue pendiente
    v = solve_step(client, s)
    assert v["step"] is None and v["hints"]["can_hint"]
    v = client.post(f"/api/sessions/{s}/hint").json()   # pista 2: «¿por qué número multiplicas?»
    _, ex = current(s)
    v = client.post(f"/api/sessions/{s}/step", json={"values": [str(ex.target_den // ex.b)]}).json()
    v = client.post(f"/api/sessions/{s}/hint").json()   # pista 3: la última, sin paso
    assert v["hints"]["shown"] == v["hints"]["total"] == 3 and v["step"] is None
    # Ninguna pista revela el resultado del ejercicio
    hist = " ".join(m["text"] for m in v["history"])
    assert "Resolvamos juntos" not in hist


def test_step_is_never_revealed_two_misses_unlock_extra_help(client):
    s, v = _to_explanation(client)
    client.post(f"/api/sessions/{s}/check", json={"option": "igual"})
    client.post(f"/api/sessions/{s}/hint")
    solve_step(client, s)
    client.post(f"/api/sessions/{s}/hint")
    client.post(f"/api/sessions/{s}/step", json={"values": ["0"]})
    v = client.post(f"/api/sessions/{s}/step", json={"values": ["0"]}).json()
    _, ex = current(s)
    assert v["step"] is not None                      # el paso sigue pendiente…
    assert v["help"]["stuck"] and v["help"]["ai"]     # …pero se activó la ayuda extra
    assert {"message", "example", "skip"} <= set(v["actions"])
    assert "Te ayudo con este paso" not in v["messages"][-1]["text"]
    assert str(ex.target_den // ex.b) not in v["messages"][-1]["text"]


def test_check_step_common_multiple_and_choice():
    ex = Exercise("suma_distinto_den", 1, 2, 1, 3)
    assert check_step(hint_step(ex, 1), ["12"]) == [True]
    assert check_step(hint_step(ex, 1), ["5"]) == [False]
    assert check_step(hint_step(ex, 0), ["No"]) == [True]
    assert check_step(hint_step(ex, 2), ["3", "2"]) == [True, True]
    assert hint_step(ex, 3) is None


def test_fast_wrong_answers_trigger_slowdown_and_guess_does_not_count(client):
    s, v = _to_explanation(client)
    client.post(f"/api/sessions/{s}/check", json={"option": "igual"})
    v1 = client.post(f"/api/sessions/{s}/answer", json={"answer": "99"}).json()
    assert not any(m["kind"] == "slowdown" for m in v1["messages"])
    v2 = client.post(f"/api/sessions/{s}/answer", json={"answer": "98"}).json()
    assert any(m["kind"] == "slowdown" for m in v2["messages"])
    _, ex = current(s)
    v3 = client.post(f"/api/sessions/{s}/answer", json={"answer": str(ex.a * ex.target_den // ex.b)}).json()
    assert state_of(s)["streak"] == 0
    assert any("varios intentos" in m["text"] for m in v3["messages"])
