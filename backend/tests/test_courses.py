"""Catálogo de cursos: el contenido (JSON) es válido y el código calcula bien.

Estas pruebas son la «verificación matemática» automática del estándar de lección:
cada ejercicio generado tiene la respuesta correcta según un cálculo independiente,
ninguna pista revela el resultado y todos los errores detectables tienen su texto.
"""
import random
import string
from math import isqrt

import pytest
from conftest import correct_answer, exam_answer, pass_check, register, start

from app.courses import all_courses
from app.courses.generic import TIPOS, GenericCourse, parse

GENERIC = [c for c in all_courses() if isinstance(c, GenericCourse)]


def _fields(template: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(template) if f}


def test_catalog_goes_from_basic_to_advanced():
    ids = [c.id for c in all_courses()]
    assert ids == ["MAT-SUMA", "MAT-RESTA", "MAT-MULT", "MAT-DIV", "MAT-FRAC", "MAT-ALG", "MAT-RAIZ"]
    for c in all_courses():
        s = c.summary()
        # Verificado por código y contra la SEP, pero SIN revisión pedagógica todavía
        assert s["meta"]["estado"] == "verificacion_matematica" and not s["meta"]["revisado_por"]
        assert "SEP" in s["meta"]["fuente_curricular"] and s["meta"]["referencias"]
        assert s["meta"]["licencia"] and s["meta"]["autor"] and s["meta"]["fuente_curricular"]
        assert all(sk["goal"] for sk in s["skills"])
        assert all(p in ids for p in s["prerequisites"])


# Respuesta calculada de forma independiente a partir de las variables
ORACLE = {
    "suma_basica": lambda v: v["a"] + v["b"],
    "suma_llevando": lambda v: v["a"] + v["b"],
    "resta_basica": lambda v: v["a"] - v["b"],
    "resta_prestando": lambda v: v["a"] - v["b"],
    "mult_tablas": lambda v: v["a"] * v["b"],
    "mult_una_cifra": lambda v: v["n"] * v["m"],
    "div_exacta": lambda v: v["n"] // v["d"],
    "div_residuo": lambda v: divmod(v["n"], v["d"]),
    "cuadrado": lambda v: v["n"] ** 2,
    "raiz_exacta": lambda v: isqrt(v["s"]),
    "raiz_estimar": lambda v: (isqrt(v["m"]), isqrt(v["m"]) + 1),
    "alg_sustituir": lambda v: v["a"] * v["v"] + v["b"],
    "alg_ec_suma": lambda v: v["b"] - v["a"],
    "alg_ec_dos_pasos": lambda v: (v["c"] - v["b"]) // v["a"],
}


@pytest.mark.parametrize("course", GENERIC, ids=lambda c: c.id)
def test_generated_exercises_are_valid(course):
    rng = random.Random(7)
    for skill in course.skills:
        tipo_name = course._sk[skill]["tipo"]
        tipo = TIPOS[tipo_name]
        for _ in range(150):
            ex = course.generate(skill, rng)
            v = ex.vars
            expected = ORACLE[tipo_name](v)
            assert course.answer(ex) == expected
            # Sanidad del nivel: nada negativo, divisiones y raíces exactas cuando deben serlo
            if tipo_name == "div_exacta":
                assert v["n"] % v["d"] == 0
            if tipo_name == "raiz_exacta":
                assert isqrt(v["s"]) ** 2 == v["s"]
            if tipo_name == "raiz_estimar":
                assert isqrt(v["m"]) ** 2 != v["m"]
            if tipo_name == "alg_ec_dos_pasos":
                assert (v["c"] - v["b"]) % v["a"] == 0
            if isinstance(expected, int):
                assert expected >= 0
            # La respuesta escrita como la pide el ejercicio se califica como correcta
            assert course.evaluate(ex, course.answer_text(ex)).correct
            if tipo.kind == "x":
                assert course.evaluate(ex, f"x = {expected}").correct
            # Cada error detectado tiene retroalimentación propia (no la genérica)
            for key in tipo.misconceptions:
                assert key in course._sk[skill]["errores"], (skill, key)


@pytest.mark.parametrize("course", GENERIC, ids=lambda c: c.id)
def test_content_follows_the_lesson_standard(course):
    for h in course.data["habilidades"]:
        for key in ("id", "tipo", "nombre", "objetivo", "explicacion", "comprobacion", "otra_forma",
                    "enunciado", "ayuda_respuesta", "pistas", "resolucion", "errores"):
            assert key in h, (h["id"], key)
        assert len(h["explicacion"]["ideas"]) <= 3                      # ideas cortas
        c = h["comprobacion"]
        assert c["correcta"] in c["opciones"] and len(c["opciones"]) == 3
        assert set(c["retro"]) == set(c["opciones"]) - {c["correcta"]}  # cada distractor explicado
        pistas = h["pistas"]
        assert len(pistas) >= 2
        assert all(p.get("paso") for p in pistas[:-1]), h["id"]       # progresivas: se responden
        for err in h["errores"].values():
            assert err["retro"] and err["docente"] and err["accion"]


@pytest.mark.parametrize("course", GENERIC, ids=lambda c: c.id)
def test_hints_and_prompts_never_reveal_the_answer(course):
    """Las variables que contienen la respuesta solo pueden usarse en la resolución
    del ejemplo parecido (que siempre es OTRO ejercicio)."""
    for h in course.data["habilidades"]:
        secrets = set(TIPOS[h["tipo"]].secrets) | {"res"}
        visible = [h["enunciado"]] + [p["texto"] for p in h["pistas"]]
        visible += [c["etiqueta"] for p in h["pistas"] if p.get("paso") for c in p["paso"]["campos"]]
        visible += [o for p in h["pistas"] if p.get("paso") for c in p["paso"]["campos"]
                    for o in c.get("opciones", [])]
        visible += [e["retro"] for e in h["errores"].values()]
        if course.transfer_skill == h["id"]:
            visible += course._stories
        for t in visible:
            assert not (_fields(t) & secrets), (h["id"], t)


@pytest.mark.parametrize("course", GENERIC, ids=lambda c: c.id)
def test_templates_render_for_every_exercise(course):
    rng = random.Random(3)
    for skill in course.skills:
        for _ in range(60):
            ex = course.generate(skill, rng)
            course.prompt(ex)
            for i, _h in enumerate(course.hints(ex)):
                course.hint_step(ex, i)
            w = course.worked_example(ex, rng)
            assert course.answer_text(ex) != "" and w["text"]
            for key in course._sk[skill]["errores"]:
                assert "{" not in course.feedback_for(ex, key)
        t = course.transfer(rng)
        assert t is None or "{" not in course.prompt(t)


@pytest.mark.parametrize("kind,raw,expected", [
    ("entero", " 1 234 ", 1234), ("entero", "12a", None),
    ("x", "x = 7", 7), ("x", "X=7", 7), ("x", "7", 7),
    ("cociente_residuo", "7 r 2", (7, 2)), ("cociente_residuo", "7 residuo 2", (7, 2)),
    ("cociente_residuo", "7", None),
    ("intervalo", "6 y 7", (6, 7)), ("intervalo", "entre 7 y 6", (6, 7)), ("intervalo", "6", None),
])
def test_parse_answers(kind, raw, expected):
    assert parse(kind, raw) == expected


@pytest.mark.parametrize("skill,vars_,raw,misc", [
    ("suma.llevando", dict(a=47, b=38, d1=4, d2=3, u1=7, u2=8, us=15, ur=5, ds=8), "75", "no_llevo"),
    ("suma.llevando", dict(a=47, b=38, d1=4, d2=3, u1=7, u2=8, us=15, ur=5, ds=8), "715", "escribio_todo"),
    ("resta.prestando", dict(a=61, b=27, d1=6, d2=2, u1=1, u2=7, d1m=5, u1p=11, ur=4, dr=3), "46", "menor_del_mayor"),
    ("resta.prestando", dict(a=61, b=27, d1=6, d2=2, u1=1, u2=7, d1m=5, u1p=11, ur=4, dr=3), "44", "no_resto_prestamo"),
    ("mult.una_cifra", dict(n=23, d=2, u=3, m=4, um=12, dm=8, dm0=80), "20", "olvido_decena"),
    ("mult.una_cifra", dict(n=23, d=2, u=3, m=4, um=12, dm=8, dm0=80), "812", "escribio_todo"),
    ("div.residuo", dict(n=17, d=5, q=3, r=2, dq=15, dq1=20), "2 r 3", "invertidos"),
    ("div.residuo", dict(n=17, d=5, q=3, r=2, dq=15, dq1=20), "3", "sin_residuo"),
    ("raiz.exacta", dict(n=6, s=36, p=5, p2=25, cmp="Menos", dir="más grandes"), "18", "mitad"),
    ("alg.sustituir", dict(a=3, v=4, b=5, av=12), "39", "concateno"),
    ("alg.ec_dos_pasos", dict(a=3, b=4, c=19, cb=15, sol=5), "12", "resto_a"),
    ("alg.ec_dos_pasos", dict(a=3, b=4, c=19, cb=15, sol=5), "15", "falto_dividir"),
])
def test_misconceptions_are_detected(skill, vars_, raw, misc):
    from app.courses import course_of_skill
    from app.courses.generic import GenExercise
    c = course_of_skill(skill)
    ev = c.evaluate(GenExercise(skill, vars_), raw)
    assert not ev.correct and ev.misconception == misc


def test_whole_generic_course_via_api(client):
    """Un curso nuevo completo de punta a punta: diagnóstico → práctica → evaluación final → constancia."""
    register(client, "Regina")
    v = start(client, "MAT-SUMA")
    s = v["session_id"]
    assert v["phase"] == "diagnostico" and "2 preguntas" in v["messages"][-1]["text"]
    v = client.post(f"/api/sessions/{s}/answer", json={"answer": correct_answer(v)}).json()
    v = client.post(f"/api/sessions/{s}/answer", json={"dont_know": True}).json()
    assert v["phase"] == "explicacion" and v["skill"] == "suma.llevando"
    assert v["explanation"]["check"]["options"]
    v = pass_check(client, s)
    for _ in range(2):
        v = client.post(f"/api/sessions/{s}/answer", json={"answer": correct_answer(v)}).json()
    assert v["phase"] == "evaluacion" and v["exam"]["total"] == 5
    certs = {c["course_id"]: c for c in client.get("/api/me/certificates").json()}
    assert not certs["MAT-SUMA"]["earned"]   # dominar las habilidades no basta: falta la evaluación
    prompts = []
    while v["phase"] == "evaluacion":
        if v["exercise"]:
            prompts.append(v["exercise"]["prompt"])
        v = exam_answer(client, s, v)
    assert any(w in p for p in prompts for w in ("libros", "tapitas", "cajas"))  # problema en contexto
    assert v["phase"] == "cierre" and v["progress"]["completed"]
    assert "Restas" in v["messages"][-1]["text"]
    certs = {c["course_id"]: c for c in client.get("/api/me/certificates").json()}
    assert certs["MAT-SUMA"]["earned"] and "valor curricular" in certs["MAT-SUMA"]["note"]
    assert not certs["MAT-RESTA"]["earned"]
    courses = {c["id"]: c for c in client.get("/api/courses").json()}
    assert courses["MAT-SUMA"]["status"] == "completado" and courses["MAT-SUMA"]["progress"] == 100
    assert courses["MAT-ALG"]["status"] == "nuevo"


def test_public_exercise_has_no_answer(client):
    register(client, "Paula")
    for course in ("MAT-DIV", "MAT-RAIZ", "MAT-ALG"):
        v = start(client, course)
        assert set(v["exercise"]) == {"id", "skill", "prompt", "visual", "input_hint"}
        assert "vars" not in str(v["exercise"])


@pytest.mark.parametrize("course", GENERIC, ids=lambda c: c.id)
def test_no_hint_step_gives_away_the_final_answer(course):
    """Por coincidencia, un paso podía pedir justo el número de la respuesta (√16: 2 × 2 = 4)."""
    rng = random.Random(5)
    for skill in course.skills:
        for _ in range(400):
            ex = course.generate(skill, rng)
            for i in range(len(course.hints(ex))):
                st = course.hint_step(ex, i)
                for f in (st or {}).get("fields", []):
                    if not f.get("options"):
                        assert f["accept"] != [course.answer_text(ex)], (skill, ex.vars, f["label"])
