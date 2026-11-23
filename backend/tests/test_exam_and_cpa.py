"""Evaluación final de cada curso y método Singapur (CPA: Concreto → Pictórico → Abstracto)."""
import json
import random
import re
import string

import pytest
from conftest import (correct_answer, current, exam_answer, pass_check, register, start, state_of,
                      take_exam)

from app import db
from app.courses import all_courses, get_course, leaks_answer
from app.courses.base import BAR_STEPS, CPA_STAGES, bar_model
from app.courses.generic import TIPOS, GenericCourse
from app.lesson import EXAM_PASS, EXAM_SIZE

GENERIC = [c for c in all_courses() if isinstance(c, GenericCourse)]
PIN = {"X-Teacher-PIN": "1234"}


def _fields(template: str) -> set[str]:
    return {f for _, f, _, _ in string.Formatter().parse(template or "") if f}


def _to_exam(client, course_id):
    """Diagnóstico perfecto: el alumno va directo a la evaluación final."""
    v = start(client, course_id)
    s = v["session_id"]
    while v["phase"] == "diagnostico":
        v = client.post(f"/api/sessions/{s}/answer", json={"answer": correct_answer(v)}).json()
    assert v["phase"] == "evaluacion"
    return s, v


def _master_current_skill(client, s):
    v = pass_check(client, s)
    for _ in range(2):
        v = client.post(f"/api/sessions/{s}/answer", json={"answer": correct_answer(v)}).json()
    return v


# --------------------------------------------------------------------------
# Evaluación final
# --------------------------------------------------------------------------
@pytest.mark.parametrize("course_id", [c.id for c in all_courses()])
def test_every_course_ends_with_a_five_question_exam(client, course_id):
    register(client, "Eva")
    s, v = _to_exam(client, course_id)
    course = get_course(course_id)
    items = state_of(s)["exam"]["items"]
    assert len(items) == EXAM_SIZE
    assert [i["kind"] for i in items][-2:] == ["problema", "concepto"]
    assert {i["skill"] for i in items if i["kind"] == "ejercicio"} == set(course.skills)
    assert v["exam"]["index"] == 1 and v["exam"]["total"] == EXAM_SIZE and v["exam"]["pass_mark"] == EXAM_PASS
    # Sin pistas ni IA
    assert "hint" not in v["actions"] and not v["help"]["ai"]
    assert client.post(f"/api/sessions/{s}/hint").status_code == 400
    assert client.post(f"/api/sessions/{s}/message", json={"text": "¿cómo se hace?"}).status_code == 400
    while v["phase"] == "evaluacion":
        if v["exam"]["kind"] == "concepto":
            q = v["exam"]["question"]
            assert len(q["options"]) == 3 and "correct" not in json.dumps(q)
            assert v["actions"][:1] == ["exam_option"] and v["exercise"] is None
        else:
            assert v["exercise"] and "answer" not in v["exercise"] and "dont_know" in v["actions"]
        v = exam_answer(client, s, v)
    assert v["phase"] == "cierre" and v["progress"]["completed"]


def test_passing_gives_certificate_and_achievement(client):
    register(client, "Iker")
    s, v = _to_exam(client, "MAT-MULT")
    certs = {c["course_id"]: c for c in client.get("/api/me/certificates").json()}
    assert not certs["MAT-MULT"]["earned"]           # habilidades dominadas, pero sin evaluación
    v = take_exam(client, s, v, wrong=(5,))         # 4 de 5: aprueba
    assert v["phase"] == "cierre"
    result = next(m for m in v["history"] if m["kind"] == "exam_result")
    assert result["exam"]["score"] == 4 and result["exam"]["passed"]
    wrong = [i for i in result["exam"]["items"] if not i["ok"]]
    assert len(wrong) == 1 and wrong[0]["note"] and wrong[0]["label"] == "Pregunta de por qué"
    assert "4 de 5" in v["messages"][-1]["text"]     # el resumen menciona la calificación
    certs = {c["course_id"]: c for c in client.get("/api/me/certificates").json()}
    assert certs["MAT-MULT"]["earned"] and certs["MAT-MULT"]["exam"]["score"] == 4
    assert certs["MAT-MULT"]["earned_at"]
    ach = {a["id"]: a for a in client.get("/api/me/achievements").json()}
    assert ach["por_tu_cuenta"]["earned"]
    prog = {p["course"]["id"]: p for p in client.get("/api/me/progress").json()}
    assert prog["MAT-MULT"]["exam"]["passed"] and prog["MAT-MULT"]["pct"] == 100


def test_failing_reinforces_only_what_failed_and_never_shows_answers(client):
    student, _ = register(client, "Ximena")
    s, v = _to_exam(client, "MAT-ALG")
    # Preguntas 2 (alg.ec_suma) y 3 (alg.ec_dos_pasos) mal, con números equivocados
    forms = []
    while v["phase"] == "evaluacion":
        i = v["exam"]["index"]
        if i in (2, 3):
            c, ex = current(s)
            forms += c.answer_forms(ex)
            wrong = str(c.answer(ex) + 1)
            v = client.post(f"/api/sessions/{s}/answer", json={"answer": wrong}).json()
        else:
            v = exam_answer(client, s, v)
    result = next(m for m in v["history"] if m["kind"] == "exam_result")
    assert result["exam"]["score"] == 3 and not result["exam"]["passed"]
    for item in result["exam"]["items"]:
        assert not leaks_answer(item["note"] or "", forms)
    # Refuerzo solo de lo que falló; lo demás sigue dominado
    assert v["phase"] == "explicacion" and v["skill"] == "alg.ec_suma"
    m = db.get_mastery(student["id"])
    assert m["alg.sustituir"]["mastered"] and not m["alg.ec_suma"]["mastered"]
    assert not m["alg.ec_dos_pasos"]["mastered"]
    certs = {c["course_id"]: c for c in client.get("/api/me/certificates").json()}
    assert not certs["MAT-ALG"]["earned"] and certs["MAT-ALG"]["exam"]["taken"] == 1
    # Al volver a dominar ambas, se presenta otra vez
    v = _master_current_skill(client, s)
    assert v["phase"] == "explicacion" and v["skill"] == "alg.ec_dos_pasos"
    v = _master_current_skill(client, s)
    assert v["phase"] == "evaluacion" and v["exam"]["index"] == 1
    v = take_exam(client, s, v)
    assert v["phase"] == "cierre" and v["progress"]["exam"]["taken"] == 2


def test_exam_is_not_interrupted_by_review_and_resumes_in_place(client):
    register(client, "Renata")
    s, v = _to_exam(client, "MAT-SUMA")
    v = exam_answer(client, s, v)
    client.post(f"/api/sessions/{s}/pause")
    v = start(client, "MAT-SUMA", days_away=60)   # aunque pasen 2 meses, no se corta la evaluación
    assert v["session_id"] == s and v["phase"] == "evaluacion" and v["exam"]["index"] == 2


def test_old_challenge_sessions_move_to_the_exam(client):
    register(client, "Gael")
    v = start(client, "MAT-RESTA")
    s = v["session_id"]
    course = get_course("MAT-RESTA")
    st = state_of(s)
    st.update(phase="transferencia", skill=course.transfer_skill,
              current=course.transfer(random.Random(1)).to_dict())
    db.save_session(s, st)
    v = start(client, "MAT-RESTA")
    assert v["phase"] == "evaluacion" and v["exam"]["index"] == 1
    assert any("evaluación final" in m["text"] for m in v["messages"])


def test_teacher_panel_shows_exam_results(client):
    register(client, "Camila", group="EVAL-1")
    s, v = _to_exam(client, "MAT-SUMA")
    take_exam(client, s, v)
    r = client.get("/api/teacher/groups/EVAL-1?course=MAT-SUMA", headers=PIN).json()
    assert r["exam_passed"] == 1 and r["completed"] == 1
    assert r["students"][0]["exam"]["passed"] and r["students"][0]["exam"]["score"] == 5


# --------------------------------------------------------------------------
# Método Singapur (CPA)
# --------------------------------------------------------------------------
@pytest.mark.parametrize("course", all_courses(), ids=lambda c: c.id)
def test_explanations_go_concrete_pictorial_abstract(course):
    for skill in course.skills:
        exp = course.explanation(skill)
        assert [st["stage"] for st in exp["stages"]] == list(CPA_STAGES), skill
        assert all(st["label"] and st["text"] for st in exp["stages"])
        assert exp["stages"][1]["visual"], f"{skill}: la etapa pictórica necesita su dibujo"
        assert exp["body"] == [st["text"] for st in exp["stages"]]


def test_explanation_view_carries_the_stages(client):
    register(client, "Andres")
    v = start(client, "MAT-DIV")
    s = v["session_id"]
    v = client.post(f"/api/sessions/{s}/answer", json={"dont_know": True}).json()
    v = client.post(f"/api/sessions/{s}/answer", json={"dont_know": True}).json()
    stages = v["explanation"]["stages"]
    assert [x["stage"] for x in stages] == ["concreto", "pictorico", "abstracto"]
    assert stages[1]["visual"]["kind"] == "modelo"


@pytest.mark.parametrize("course", GENERIC, ids=lambda c: c.id)
def test_bar_models_in_explanations_add_up(course):
    for h in course.data["habilidades"]:
        for idea in h["explicacion"]["ideas"]:
            v = idea.get("visual") or {}
            if v.get("kind") != "modelo":
                continue
            for f in v["filas"]:
                known = sum(s["n"] * s.get("repetir", 1) for s in f["segmentos"] if not s.get("resto"))
                if any(s.get("resto") for s in f["segmentos"]):
                    assert f["total"] > known and f["llave"] == str(f["total"]), (h["id"], f)
                elif re.fullmatch(r"\d+", f.get("llave") or ""):
                    assert known == int(f["llave"]), (h["id"], f)


@pytest.mark.parametrize("course", GENERIC, ids=lambda c: c.id)
def test_hint_bar_model_never_reveals_the_answer(course):
    for h in course.data["habilidades"]:
        spec = h.get("visual_pista")
        if not spec:
            continue
        secrets = set(TIPOS[h["tipo"]].secrets) | {"res"}
        visible = [spec.get("caption")]
        for f in spec.get("filas", []):
            visible += [f.get("llave"), f.get("etiqueta")] + [s["texto"] for s in f["segmentos"]]
        for t in visible:
            assert not (_fields(t) & secrets), (h["id"], t)   # los tamaños (n) sí: llegan aproximados
    rng = random.Random(5)
    for skill in course.skills:
        for _ in range(80):
            ex = course.generate(skill, rng)
            vis = course.hint_visual(ex, 0)
            assert course.hint_visual(ex, 1) is None
            if not vis:
                continue
            assert not re.search(r"\{\w+\}", json.dumps(vis, ensure_ascii=False))
            ans, prompt_nums = course.answer_text(ex), re.findall(r"\d+", course.prompt(ex))
            labels = re.findall(r"\d+", json.dumps(
                {k: v for k, v in vis.items() if k in ("caption", "filas")}, ensure_ascii=False))
            if vis["kind"] == "modelo":
                segs = [s for f in vis["filas"] for s in f["segmentos"]]
                assert all("n" not in s and 1 <= s["peso"] <= BAR_STEPS for s in segs)
                labels = re.findall(r"\d+", " ".join([vis["caption"] or ""] + [s["texto"] for s in segs]
                                                     + [f["llave"] or "" for f in vis["filas"]]))
            assert ans not in labels or ans in prompt_nums, (skill, ex.vars, vis)


def test_first_hint_draws_the_bar_model(client):
    register(client, "Paula")
    v = start(client, "MAT-MULT")
    s = v["session_id"]
    v = client.post(f"/api/sessions/{s}/answer", json={"dont_know": True}).json()
    v = client.post(f"/api/sessions/{s}/answer", json={"dont_know": True}).json()
    pass_check(client, s)
    v = client.post(f"/api/sessions/{s}/hint").json()
    assert v["messages"][-1]["kind"] == "hint" and v["messages"][-1]["visual"]["kind"] == "modelo"


def test_bar_model_sends_only_approximate_sizes():
    m = bar_model({"filas": [{"total": 12, "llave": "12",
                              "segmentos": [{"resto": True, "texto": "x", "hueco": True},
                                            {"n": 5, "texto": "5"}]}]})
    segs = m["filas"][0]["segmentos"]
    assert [s["peso"] for s in segs] == [12, 8] and segs[0]["hueco"] and "n" not in segs[0]
    m = bar_model({"filas": [{"segmentos": [{"n": 7, "texto": "?", "repetir": 15}]}]})
    assert len({s["peso"] for s in m["filas"][0]["segmentos"]}) == 1   # grupos iguales, barras iguales


@pytest.mark.parametrize("course", all_courses(), ids=lambda c: c.id)
def test_exam_questions_follow_the_standard(course):
    qs = course.exam_questions()
    assert len(qs) >= 2   # para que cambie la pregunta si se vuelve a presentar
    for q in qs:
        assert q["correct"] in q["options"] and len(q["options"]) == 3
        assert set(q["feedback"]) == set(q["options"]) - {q["correct"]}
