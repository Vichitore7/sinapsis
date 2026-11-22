"""Teoría al inicio de cada curso: entender POR QUÉ funciona antes de practicar."""
import re

import pytest
from conftest import register, start

from app.courses import all_courses, get_course

VISUAL_KINDS = {"base10", "columnas", "arreglo", "reparto", "cuadricula", "balanza", "barras"}


def test_course_starts_with_theory_and_requires_understanding(client):
    register(client, "Teo")
    v = start(client, "MAT-SUMA", theory=False)
    s = v["session_id"]
    assert v["phase"] == "fundamentos" and v["actions"] == ["theory", "message", "pause"]
    th = v["theory"]
    assert len(th["cards"]) >= 4 and th["sources"] and "correct" not in th["question"]
    assert v["exercise"] is None
    q = get_course("MAT-SUMA").theory(with_answer=True)["question"]
    wrong = next(o["id"] for o in th["question"]["options"] if o["id"] != q["correct"])
    v = client.post(f"/api/sessions/{s}/theory", json={"option": wrong}).json()
    assert v["phase"] == "fundamentos" and v["messages"][-1]["kind"] == "feedback_wrong"
    v = client.post(f"/api/sessions/{s}/theory", json={"option": q["correct"]}).json()
    assert v["phase"] == "diagnostico" and v["exercise"]
    assert client.post(f"/api/sessions/{s}/theory", json={"option": q["correct"]}).status_code == 400
    # Puede preguntarle a Loop mientras lee la teoría (otra sesión)
    v2 = start(client, "MAT-RESTA", theory=False)
    r = client.post(f"/api/sessions/{v2['session_id']}/message", json={"text": "¿qué es una decena?"})
    assert r.status_code == 200 and r.json()["messages"][-1]["kind"] == "ai"


def test_theory_is_available_anytime_from_the_course(client):
    register(client, "Teo2")
    d = client.get("/api/courses/MAT-DIV").json()
    assert d["has_theory"] and d["theory"]["cards"] and "correct" not in d["theory"]["question"]


@pytest.mark.parametrize("course", all_courses(), ids=lambda c: c.id)
def test_theory_content_standard(course):
    t = course.data["fundamentos"]
    assert 4 <= len(t["tarjetas"]) <= 6
    assert any("bien" in c["titulo"].lower() or "por qué" in c["titulo"].lower() for c in t["tarjetas"])
    q = t["pregunta"]
    assert q["correcta"] in q["opciones"] and set(q["retro"]) == set(q["opciones"]) - {q["correcta"]}
    sep = [f for f in t["fuentes"] if "SEP" in f["titulo"]]
    assert sep and all(f["cita"] and f["url"].startswith("https://educacionbasica.sep.gob.mx/") for f in sep)
    for f in t["fuentes"]:
        assert f["uso"]  # cada fuente dice para qué se usa y con qué licencia
    for c in t["tarjetas"]:
        if c.get("visual"):
            assert c["visual"]["kind"] in VISUAL_KINDS


def _num(cells):
    return int("".join(x for x in cells if x)) if any(cells) else 0


@pytest.mark.parametrize("course", all_courses(), ids=lambda c: c.id)
def test_numbers_inside_the_drawings_are_right(course):
    """Las cuentas que muestran los dibujos de la teoría también se comprueban."""
    for c in course.data["fundamentos"]["tarjetas"]:
        v = c.get("visual") or {}
        if v.get("kind") == "base10":
            n = v["numero"]
            parts = [int(x) for x in re.findall(r"\d+", v["caption"].split("=", 1)[-1])] if "=" in v["caption"] else []
            if "+" in v["caption"]:
                assert sum(parts) == n, v
        if v.get("kind") == "columnas":
            rows = [r for r in v["filas"] if r.get("tipo") != "lleva"]  # la fila tachada es el número original
            res = _num(next(r for r in rows if r.get("tipo") == "resultado")["celdas"])
            ops = [r for r in rows if r.get("tipo") != "resultado"]
            if any(r["etiqueta"] == "−" for r in ops):
                assert _num(ops[0]["celdas"]) - _num(ops[1]["celdas"]) == res, v
            else:
                assert sum(_num(r["celdas"]) for r in ops) == res, v
                for r in ops:  # filas tipo «20 × 4»: el producto parcial es correcto
                    m = re.fullmatch(r"(\d+) × (\d+)", r["etiqueta"])
                    if m:
                        assert int(m[1]) * int(m[2]) == _num(r["celdas"]), r
        if v.get("kind") == "reparto":
            q, rr = divmod(v["total"], v["grupos"])
            assert f"le tocan {q}" in v["caption"] and f"sobran {rr}" in v["caption"]
        if v.get("kind") == "arreglo":
            assert str(v["filas"] * v["columnas"]) in v["caption"]
        if v.get("kind") == "cuadricula":
            assert str(v["lado"] ** 2) in v["caption"]
