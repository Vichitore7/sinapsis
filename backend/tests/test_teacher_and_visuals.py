"""Panel docente (errores agrupados por grupo) y barras pictóricas (CPA)."""
from conftest import current, pass_check, register, start

from app.fractions_engine import Exercise, hint_visual, hints, misconception_visual

PIN = {"X-Teacher-Pin": "1234"}


def _current(view) -> Exercise:
    return current(view["session_id"])[1]


def test_teacher_requires_pin(client):
    assert client.get("/api/teacher/groups").status_code == 401
    assert client.get("/api/teacher/groups", headers={"X-Teacher-Pin": "0000"}).status_code == 401


def test_group_report_counts_distinct_students(client):
    heads = []
    for name in ("Ana", "Luis", "Sofia"):
        r, h = register(client, name, group=" 1b-test ")
        assert r["group_code"] == "1B-TEST" and "password_hash" not in r
        heads.append(h)
    # Ana y Luis cometen el error 2/5 en el diagnóstico de suma con distinto denominador
    for h in heads[:2]:
        client.headers.update(h)
        v = start(client)
        s = v["session_id"]
        v = client.post(f"/api/sessions/{s}/answer", json={"dont_know": True}).json()
        v = client.post(f"/api/sessions/{s}/answer", json={"dont_know": True}).json()
        ex = _current(v)
        for _ in range(2):  # dos veces el mismo alumno: cuenta como 1
            client.post(f"/api/sessions/{s}/answer", json={"answer": f"{ex.a + ex.c}/{ex.b + ex.d}"})
            v = client.get(f"/api/sessions/{s}").json()
            ex = _current(v) if v["exercise"] else ex

    rep = client.get("/api/teacher/groups/1b-test", headers=PIN).json()
    assert rep["students_total"] == 3
    top = rep["misconceptions"][0]
    assert top["id"] == "suma_num_y_den" and top["students"] == 2 and top["pct"] == 67
    assert "67%" in rep["headline"] and top["action"]
    assert any(g["group_code"] == "1B-TEST" for g in client.get("/api/teacher/groups", headers=PIN).json())


def test_demo_group_is_simulated(client):
    rep = client.post("/api/teacher/demo-group", headers=PIN).json()
    assert rep["simulated"] and rep["students_total"] == 20
    assert rep["misconceptions"][0]["id"] == "suma_num_y_den"
    assert rep["attention"]
    # Recrearlo no duplica alumnos
    assert client.post("/api/teacher/demo-group", headers=PIN).json()["students_total"] == 20


def test_misconception_visual_shows_2_5_is_smaller():
    ex = Exercise("suma_distinto_den", 1, 2, 1, 3)
    v = misconception_visual(ex, "2/5", "suma_num_y_den")
    assert v["kind"] == "barras" and len(v["bars"]) == 3
    assert "2/5" in v["caption"] and "1/2" in v["caption"]


def test_hint_visual_splits_bars_into_common_pieces():
    ex = Exercise("suma_distinto_den", 1, 2, 1, 3)
    v = hint_visual(ex, 2)
    assert [(b["num"], b["den"], b["group"]) for b in v["bars"]] == [(3, 6, 3), (2, 6, 2)]
    # En problemas verbales no hay dibujos antes de la resolución acompañada
    story = Exercise("suma_distinto_den", 1, 2, 1, 3, story="Pizza…")
    assert hint_visual(story, 1) is None
    assert hint_visual(story, len(hints(story)) - 1) is not None


def test_wrong_answer_message_carries_visual(client):
    register(client, "Diego")
    v = start(client)
    s = v["session_id"]
    client.post(f"/api/sessions/{s}/answer", json={"dont_know": True})
    client.post(f"/api/sessions/{s}/answer", json={"dont_know": True})
    v = client.post(f"/api/sessions/{s}/answer", json={"dont_know": True}).json()
    # empieza en equivalencia → práctica
    v = pass_check(client, s)
    ex = _current(v)
    v = client.post(f"/api/sessions/{s}/answer", json={"answer": str(ex.a + ex.target_den - ex.b)}).json()
    wrong = [m for m in v["messages"] if m["kind"] == "feedback_wrong"][0]
    assert wrong["visual"]["kind"] == "barras"


def test_group_report_per_course(client):
    """El panel docente también reporta los cursos nuevos, con sus propios errores."""
    _, h = register(client, "Iker", group="2C-TEST")
    v = start(client, "MAT-RESTA")
    s = v["session_id"]
    v = client.post(f"/api/sessions/{s}/answer", json={"dont_know": True}).json()  # resta básica
    c, ex = current(s)
    vv = ex.vars
    wrong = (vv["d1"] - vv["d2"]) * 10 + (vv["u2"] - vv["u1"])   # resta el menor del mayor
    client.post(f"/api/sessions/{s}/answer", json={"answer": str(wrong)})
    rep = client.get("/api/teacher/groups/2C-TEST?course=MAT-RESTA", headers=PIN).json()
    assert rep["course"]["id"] == "MAT-RESTA"
    assert rep["misconceptions"][0]["id"] == "menor_del_mayor"
    assert [k["id"] for k in rep["skills"]] == ["resta.basica", "resta.prestando"]
    # El reporte de fracciones de ese grupo no mezcla errores de restas
    assert client.get("/api/teacher/groups/2C-TEST", headers=PIN).json()["misconceptions"] == []
