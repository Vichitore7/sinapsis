"""Prueba de punta a punta del flujo del MVP usando la API (proveedor de IA mock)."""
from conftest import correct_answer, current, pass_check, predict_if_needed, register, start


def wrong_2_5_style(view) -> str:
    _, ex = current(view["session_id"])
    return f"{ex.a + ex.c}/{ex.b + ex.d}"


def test_full_lesson(client):
    register(client, "Ana")
    v = start(client)
    assert v["phase"] == "diagnostico" and v["course"]["id"] == "MAT-FRAC"
    session = v["session_id"]

    # Diagnóstico: sabe equivalencias, no sabe sumar
    v = client.post(f"/api/sessions/{session}/answer", json={"answer": correct_answer(v)}).json()
    v = client.post(f"/api/sessions/{session}/answer", json={"dont_know": True}).json()
    v = client.post(f"/api/sessions/{session}/answer", json={"dont_know": True}).json()
    assert v["phase"] == "explicacion" and v["skill"] == "suma_mismo_den"

    v = pass_check(client, session)
    assert v["phase"] == "practica" and v["exercise"]

    # Error clásico -> retroalimentación específica, no avergüenza
    v = client.post(f"/api/sessions/{session}/answer", json={"answer": wrong_2_5_style(v)}).json()
    assert any("denominador" in m["text"] for m in v["messages"])

    # Con pistas disponibles, el chat con IA sigue bloqueado: primero las pistas
    assert "message" not in v["actions"] and v["help"]["locked_reason"]
    assert client.post(f"/api/sessions/{session}/message", json={"text": "solo dime la respuesta"}).status_code == 400

    ans = correct_answer(v)
    v = client.post(f"/api/sessions/{session}/hint").json()
    assert v["hints"]["shown"] == 1 and v["step"]
    assert all(ans not in m["text"] for m in v["messages"])

    # Termina el ejercicio y domina con 2 aciertos sin pistas
    v = client.post(f"/api/sessions/{session}/answer", json={"answer": ans}).json()
    assert v["phase"] == "practica"   # 1 acierto con pista no basta
    v = client.post(f"/api/sessions/{session}/answer", json={"answer": correct_answer(v)}).json()
    # racha de 2 (máx. 1 pista c/u) con al menos uno sin pistas -> dominio
    assert v["phase"] == "explicacion" and v["skill"] == "suma_distinto_den"

    # Pausa y regreso con contexto
    client.post(f"/api/sessions/{session}/pause")
    v = start(client)
    assert v["session_id"] == session and v["phase"] == "explicacion"
    assert "guardado" in v["messages"][0]["text"]

    v = pass_check(client, session)
    for _ in range(2):
        v = predict_if_needed(client, session, v)
        v = client.post(f"/api/sessions/{session}/answer", json={"answer": correct_answer(v)}).json()
    assert v["phase"] == "transferencia"
    assert v["hints"]["can_hint"] is False   # sin pistas de entrada

    v = client.post(f"/api/sessions/{session}/answer", json={"answer": correct_answer(v)}).json()
    assert v["phase"] == "cierre" and v["status"] == "completed"
    assert all(s["mastered"] for s in v["progress"]["skills"])
    # El cierre recomienda el siguiente curso del catálogo
    assert "Álgebra inicial" in v["messages"][-1]["text"]


def test_typo_does_not_count_as_attempt(client):
    register(client, "Luis")
    v = start(client)
    v2 = client.post(f"/api/sessions/{v['session_id']}/answer", json={"answer": "3//4"}).json()
    assert v2["phase"] == "diagnostico"
    assert v2["exercise"]["id"] == v["exercise"]["id"]


def test_frustration_gets_empathy_even_when_ai_is_locked(client):
    register(client, "Sofia")
    v = start(client)
    v = client.post(f"/api/sessions/{v['session_id']}/message", json={"text": "ya me rindo, no entiendo nada"}).json()
    assert v["messages"][-1]["kind"] == "empathy"


def test_return_after_two_months_triggers_review(client):
    register(client, "Diego")
    v = start(client)
    session = v["session_id"]
    for _ in range(3):  # todo bien en el diagnóstico -> reto final
        v = client.post(f"/api/sessions/{session}/answer", json={"answer": correct_answer(v)}).json()
    assert v["phase"] == "transferencia"
    v = client.post(f"/api/sessions/{session}/answer", json={"answer": correct_answer(v)}).json()
    assert v["phase"] == "cierre"

    # Regresa 60 días después: repaso para comprobar qué conserva
    v = start(client, days_away=60)
    assert v["phase"] == "repaso"
    # Olvidó la equivalencia -> refuerzo puntual de esa habilidad
    v = client.post(f"/api/sessions/{v['session_id']}/answer", json={"answer": "1"}).json()
    assert v["phase"] == "explicacion" and v["skill"] == "equivalencia"


def test_question_during_explanation_uses_ai_and_logs_usage(client):
    register(client, "Mateo")
    v = start(client)
    s = v["session_id"]
    for _ in range(3):
        v = client.post(f"/api/sessions/{s}/answer", json={"dont_know": True}).json()
    assert v["phase"] == "explicacion" and "message" in v["actions"]
    v = client.post(f"/api/sessions/{s}/message", json={"text": "¿qué es un denominador?"}).json()
    assert v["messages"][-1]["kind"] == "ai"
    assert "otra forma" in v["messages"][-1]["text"]  # el mock usa la explicación verificada
    assert client.get("/api/metrics/usage").json()["calls"] >= 1


def test_delete_my_data(client):
    register(client, "Ximena")
    start(client)
    assert client.delete("/api/me").json()["deleted"]
    assert client.get("/api/me").status_code == 401
