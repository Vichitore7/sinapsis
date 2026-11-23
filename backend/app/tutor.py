"""Flujo pedagógico de la sesión (máquina de estados), igual para todos los cursos.

Fases:
  fundamentos   -> la teoría del curso (qué es y por qué funciona) + una pregunta; solo la primera vez
  diagnostico   -> 1 ejercicio por habilidad, sin pistas, para ubicar al alumno
  explicacion   -> ideas cortas + pregunta de comprobación (se puede preguntar a Loop)
  practica      -> ejercicios con pistas progresivas hasta alcanzar dominio
  evaluacion    -> evaluación final: un ejercicio por habilidad, un problema en contexto y una
                   pregunta de «por qué», sin pistas ni IA. Se aprueba con EXAM_PASS de EXAM_SIZE;
                   si no, se refuerzan las habilidades falladas y se vuelve a presentar.
  repaso        -> al regresar tras muchos días: comprobar qué se conserva
  cierre        -> resumen y recomendación del siguiente curso

(«transferencia», el antiguo reto final de un solo problema, ya no se usa: las sesiones
guardadas en esa fase pasan a la evaluación final al reanudarse.)

Método Singapur (CPA): cada explicación va de lo concreto (objetos) a lo pictórico
(modelo de barras) y a lo abstracto (números); la primera pista dibuja el modelo de
barras del ejercicio, con «?» en lo que se busca.

Ayuda en orden (nunca se entrega la respuesta final):
  1. Pistas progresivas: para ver la siguiente hay que responder el paso de la actual.
  2. Ayuda extra («?»): solo cuando ya se usaron todas las pistas o un paso se trabó.
     Loop (IA) explica de otra forma, se puede ver un ejemplo parecido resuelto con
     OTROS números o cambiar de ejercicio sin penalización.

Todo el estado vive en `state` (JSON en la tabla sessions) para reanudar en el
punto exacto. La IA solo se usa para preguntas libres del alumno.
"""
from __future__ import annotations

import random
import unicodedata
from datetime import datetime, timezone
from typing import Optional

from . import db
from .ai import TutorContext, get_provider
from .courses import Course, UnknownCourse, all_courses, get_course, leaks_answer
from .fractions_engine import check_step
from .lesson import (ANSWER_REQUEST_WORDS, DEFAULT_STYLE, EXAM_PASS, EXAM_SIZE, FAST_SECONDS,
                     FAST_WRONG_LIMIT,
                     FRUSTRATION_WORDS, GUESS_ATTEMPTS, MASTERY_STREAK, MAX_EXERCISES_PER_SKILL,
                     MAX_HINTS_FOR_MASTERY, REVIEW_AFTER_DAYS, TUTOR_STYLES)

PHASE_LABELS = {
    "fundamentos": "Fundamentos",
    "diagnostico": "Diagnóstico",
    "explicacion": "Explicación",
    "practica": "Práctica",
    "transferencia": "Reto final",   # fase antigua (sesiones guardadas antes de la evaluación)
    "evaluacion": "Evaluación final",
    "repaso": "Repaso",
    "cierre": "Cierre",
}
STEP_TRIES_BEFORE_HELP = 2
HELP_LOCKED_TEXT = "La ayuda extra se activa cuando ya usaste todas las pistas o si un paso se te traba."
HELP_OPTIONS_TEXT = ("No te daré la respuesta, pero ya se activó la ayuda extra (botón ?): "
                     "pregúntale a Loop con tus palabras, mira un ejemplo parecido resuelto "
                     "o prueba con otro ejercicio.")


class TutorError(ValueError):
    pass


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in t if unicodedata.category(ch) != "Mn")


def _contains_any(text: str, words: list[str]) -> bool:
    t = _norm(text)
    return any(_norm(w) in t for w in words)


def _style(student: dict) -> dict:
    return TUTOR_STYLES.get(student.get("tutor_style") or DEFAULT_STYLE, TUTOR_STYLES[DEFAULT_STYLE])


def _msg(text: str, kind: str = "info", visual: Optional[dict] = None) -> dict:
    m = {"role": "tutor", "kind": kind, "text": text}
    if visual:
        m["visual"] = visual  # barras de fracciones (método CPA)
    return m


def _course(state: dict) -> Course:
    return get_course(state.get("course"))


def _new_state(course: Course) -> dict:
    return {
        "course": course.id,
        "phase": "diagnostico",
        "skill": None,
        "diag_queue": list(course.skills),
        "diag_results": {},
        "practice_queue": [],
        "review_queue": [],
        "resume_after_review": None,
        "current": None,
        "hints_shown": 0,
        "attempts_on_current": 0,
        "streak": 0,
        "streak_nohint": False,
        "exercises_in_skill": 0,
        "transfer_failures": 0,
        "used": [],
        "turns": [],
        "history": [],   # últimos mensajes del tutor/alumno para repintar la pantalla al volver
        "check_order": None,   # orden de opciones de la pregunta de comprobación
        "prediction": None,    # predicción pendiente/contestada del ejercicio actual
        "step": None,          # mini paso de la pista actual
        "last_at": None,       # para detectar respuestas al azar muy rápidas
        "fast_wrong": 0,
        "predict_n": 0,
        "stuck": False,        # ayuda extra activada para el ejercicio actual
        "wrong_answers": [],   # respuestas equivocadas del ejercicio actual (contexto para la IA)
    }


def _days_since(iso: Optional[str]) -> float:
    if not iso:
        return 0.0
    then = datetime.fromisoformat(iso)
    return (datetime.now(timezone.utc) - then).total_seconds() / 86400


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seconds_since_last(state: dict) -> float:
    last = state.get("last_at")
    if not last:
        return 1e9
    return (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds()


def _set_exercise(state: dict, course: Course, ex) -> None:
    state["current"] = ex.to_dict()
    state["hints_shown"] = 0
    state["attempts_on_current"] = 0
    state["used"] = (state.get("used", []) + [course.signature(ex)])[-50:]
    state["step"] = None
    state["fast_wrong"] = 0
    state["last_at"] = _now_iso()
    state["prediction"] = None
    state["stuck"] = False
    state["wrong_answers"] = []
    # Predicción antes de calcular: un ejercicio sí y otro no, donde el curso la tenga
    if state.get("phase") == "practica" and course.wants_prediction(ex):
        state["predict_n"] = state.get("predict_n", 0) + 1
        if state["predict_n"] % 2 == 1:
            state["prediction"] = course.prediction_for(ex)


def _prediction_pending(state: dict) -> bool:
    p = state.get("prediction")
    return bool(p) and p.get("answered") is None


def _step_pending(state: dict) -> bool:
    st = state.get("step")
    return bool(st) and not st.get("done")


def _stuck(state: dict) -> bool:
    return bool(state.get("stuck")) and state.get("phase") == "practica" and bool(state.get("current"))


def _next_exercise_for(state: dict, course: Course, skill: str):
    ex = course.generate(skill, random.Random(), set(state.get("used", [])))
    _set_exercise(state, course, ex)
    return ex


def _remember(state: dict, messages: list[dict]) -> None:
    state["history"] = (state.get("history", []) + messages)[-30:]


# --------------------------------------------------------------------------
# Vista que se envía al frontend
# --------------------------------------------------------------------------
def progress_for(student_id: int, course: Course) -> dict:
    mastery = db.get_mastery(student_id)
    skills = []
    for s in course.skills:
        m = mastery.get(s, {})
        skills.append({
            "id": s, "name": course.skill_names[s],
            "mastery": round(m.get("mastery", 0.0), 2),
            "mastered": bool(m.get("mastered", 0)),
            "attempts": m.get("attempts", 0),
            "correct": m.get("correct", 0),
            "last_practiced": m.get("last_practiced"),
        })
    labels = course.teacher_labels()
    overcome = [o for o in db.overcome_misconceptions(student_id) if o["skill"] in course.skills]
    done = sum(1 for s in skills if s["mastered"])
    exam = db.exam_status(student_id, course.id)
    return {
        "course": {"id": course.id, "title": course.title},
        "skills": skills,
        # La evaluación final cuenta como un paso más del curso
        "pct": round(100 * (done + int(exam["passed"])) / (len(skills) + 1)) if skills else 0,
        "completed": done == len(skills) and exam["passed"],
        "exam": {**exam, "pass_mark": EXAM_PASS, "size": EXAM_SIZE},
        "errors_overcome": [labels.get(o["misconception"], {}).get("label", o["misconception"])
                            for o in overcome],
    }


def _view(session_id: int, student: dict, state: dict, messages: list[dict], status: str = "active") -> dict:
    course = _course(state)
    phase = state["phase"]
    ex = course.load(state["current"]) if state.get("current") else None
    hints_total = len(course.hints(ex)) if ex else 0
    stuck = _stuck(state)
    item = _exam_item(state)
    can_hint = bool(ex) and phase in ("practica", "repaso") \
        and state["hints_shown"] < hints_total \
        and (phase == "practica" or state["attempts_on_current"] >= 1) \
        and not _step_pending(state) and not _prediction_pending(state)
    can_ai = phase in ("explicacion", "fundamentos") or stuck
    if phase == "fundamentos":
        actions = ["theory"]
    elif phase == "diagnostico":
        actions = ["answer", "dont_know"]
    elif phase == "evaluacion":
        actions = ["exam_option"] if item and item["kind"] == "concepto" else ["answer", "dont_know"]
    elif phase == "explicacion":
        actions = ["check"]
    elif phase == "cierre":
        actions = ["restart"]
    elif _prediction_pending(state):
        actions = ["predict"]
    else:
        actions = ["answer"] + (["hint"] if can_hint else []) + (["step"] if _step_pending(state) else [])
        if stuck:
            actions += ["example", "skip"]
    actions += (["message"] if can_ai else []) + (["pause"] if phase != "cierre" else [])
    return {
        "session_id": session_id,
        "status": status,
        "course": {"id": course.id, "title": course.title},
        "lesson": {"id": course.id, "title": course.title},
        "phase": phase,
        "phase_label": PHASE_LABELS[phase],
        "skill": state.get("skill"),
        "skill_name": course.skill_names.get(state.get("skill") or "", None),
        "messages": messages,
        "exercise": course.public(ex) if ex and phase != "explicacion" else None,
        "explanation": _explanation_view(state, course) if phase == "explicacion" else None,
        "theory": _theory_view(state, course) if phase == "fundamentos" else None,
        "exam": _exam_view(state, course, item) if item else None,
        "prediction": {"question": course.prediction_question(ex, state["prediction"]),
                       "options": [{"id": "mayor", "text": "Mayor"}, {"id": "menor", "text": "Menor"}]}
        if ex and _prediction_pending(state) else None,
        "step": _public_step(state["step"]["data"]) if _step_pending(state) else None,
        "hints": {"shown": state.get("hints_shown", 0), "total": hints_total, "can_hint": can_hint},
        "help": {"ai": can_ai, "stuck": stuck,
                 "locked_reason": None if can_ai else HELP_LOCKED_TEXT},
        "actions": actions,
        "progress": progress_for(student["id"], course),
        "history": state.get("history", []),
    }


def _public_step(step: Optional[dict]) -> Optional[dict]:
    if not step:
        return None
    return {"prompt": step["prompt"],
            "fields": [{"label": f["label"], **({"options": f["options"]} if f.get("options") else {})}
                       for f in step["fields"]]}


def _explanation_view(state: dict, course: Course) -> Optional[dict]:
    skill = state.get("skill")
    if not skill:
        return None
    exp = course.explanation(skill)
    q = course.check_question(skill)
    order = state.get("check_order") or list(q["options"])
    return {**exp, "check": {"question": q["question"],
                             "options": [{"id": k, "text": q["options"][k]} for k in order]}}


def _exam_view(state: dict, course: Course, item: dict) -> dict:
    exam = state["exam"]
    out = {"index": exam["i"] + 1, "total": len(exam["items"]), "kind": item["kind"],
           "pass_mark": EXAM_PASS, "question": None}
    if item["kind"] == "concepto":
        q = course.exam_questions()[item["q"]]
        out["question"] = {"question": q["question"],
                           "options": [{"id": k, "text": q["options"][k]} for k in item["order"]]}
    return out


def _theory_view(state: dict, course: Course) -> Optional[dict]:
    th = course.theory()
    if not th:
        return None
    order = state.get("theory_order") or [o["id"] for o in th["question"]["options"]]
    by_id = {o["id"]: o for o in th["question"]["options"]}
    th["question"]["options"] = [by_id[k] for k in order if k in by_id]
    return th


def _load(session_id: int, student_id: Optional[int] = None) -> tuple[dict, dict, dict]:
    session = db.get_session(session_id)
    if not session or (student_id is not None and session["student_id"] != student_id):
        raise TutorError("sesión no encontrada")
    student = db.get_student(session["student_id"])
    return session, student, session["state"]


def _save_and_view(session_id: int, student: dict, state: dict, messages: list[dict],
                   status: str = "active") -> dict:
    _remember(state, messages)
    db.save_session(session_id, state, status)
    return _view(session_id, student, state, messages, status)


# --------------------------------------------------------------------------
# Inicio / reanudación
# --------------------------------------------------------------------------
def start_or_resume(student_id: int, course_id: Optional[str] = None,
                    days_away: Optional[float] = None) -> dict:
    """`days_away` solo sirve para la demo: simula que el alumno regresa tras N días."""
    student = db.get_student(student_id)
    if not student:
        raise TutorError("alumno no encontrado")
    try:
        course = get_course(course_id)
    except UnknownCourse:
        raise TutorError("curso no encontrado") from None
    style = _style(student)
    away = days_away if days_away is not None else _days_since(db.last_activity(student_id, course.id))
    mastery = {k: v for k, v in db.get_mastery(student_id).items() if k in course.skills}
    mastered = [s for s in course.skills if mastery.get(s, {}).get("mastered")]

    open_session = db.latest_open_session(student_id, course.id)
    if open_session:
        sid, state = open_session["id"], open_session["state"]
        state.setdefault("course", course.id)
        last = (state.get("history") or [{}])[-1]
        # Si solo recargó la página, no apilamos otro saludo idéntico en el historial
        messages = [] if last.get("kind") == "welcome" and away < 1 else \
            [_msg(_resume_summary(student, state, course, away), "welcome")]
        db.log_event("regreso", sid, student_id, {"days_away": round(away, 1), "course": course.id})
        if state["phase"] == "transferencia":
            # Sesión guardada con el antiguo reto final: ahora el curso cierra con la evaluación
            messages.append(_msg("El reto final ahora es parte de una evaluación final más completa.",
                                 "info"))
            messages += _begin_exam(state, course)
        elif away >= REVIEW_AFTER_DAYS and mastered and \
                state["phase"] not in ("diagnostico", "repaso", "evaluacion"):
            messages += _begin_review(state, course, mastered)
        status = "completed" if state["phase"] == "cierre" else "active"
        return _save_and_view(sid, student, state, messages, status)

    # Nueva sesión de este curso
    state = _new_state(course)
    sid = db.create_session(student_id, course.id, state)
    if not mastery:
        messages = [_msg(style["greeting"].format(name=student["name"]) + f" Hoy: {course.title}.", "welcome")]
        th = course.theory()
        if th and not db.has_course_event(student_id, "fundamentos", course.id):
            # Antes de hacer, entender: la teoría del curso va primero
            state["phase"] = "fundamentos"
            order = [o["id"] for o in th["question"]["options"]]
            random.shuffle(order)
            state["theory_order"] = order
            messages.append(_msg(f"Antes de practicar, veamos la teoría: {th['title'].lower()}. Son "
                                 f"{len(th['cards'])} tarjetas cortas y una pregunta. Así no solo sabrás "
                                 "hacerlo: sabrás por qué funciona.", "info"))
            return _save_and_view(sid, student, state, messages)
        messages += _begin_diagnostic(state, course)
        return _save_and_view(sid, student, state, messages)

    # Ya estudió este curso antes: sin diagnóstico, usamos su memoria
    messages = [_msg(f"¡Hola otra vez, {student['name']}! Ya te conozco en «{course.title}», así que "
                     "no repetiremos el diagnóstico.", "welcome")]
    pending = [s for s in course.skills if s not in mastered]
    if away >= REVIEW_AFTER_DAYS and mastered:
        messages += _begin_review(state, course, mastered)
        state["practice_queue"] = pending
    elif pending:
        state["practice_queue"] = pending[1:]
        messages += _begin_explanation(state, course, pending[0])
    else:
        messages += _begin_review(state, course, mastered)
    return _save_and_view(sid, student, state, messages)


def _begin_diagnostic(state: dict, course: Course) -> list[dict]:
    state["phase"] = "diagnostico"
    state["skill"] = state["diag_queue"][0]
    _next_exercise_for(state, course, state["skill"])
    return [_msg(f"Ahora, {len(course.skills)} preguntas rápidas para ver cómo piensas. Si no sabes, "
                 "presiona «No lo sé todavía».", "info")]


def check_theory(session_id: int, option: str, student_id: Optional[int] = None) -> dict:
    """Pregunta al final de la teoría: solo se avanza si se entendió POR QUÉ funciona."""
    _, student, state = _load(session_id, student_id)
    if state["phase"] != "fundamentos":
        raise TutorError("no hay teoría pendiente")
    course = _course(state)
    q = course.theory(with_answer=True)["question"]
    texts = {o["id"]: o["text"] for o in q["options"]}
    if option not in texts:
        raise TutorError("opción desconocida")
    ok = option == q["correct"]
    messages = [{"role": "student", "kind": "answer", "text": texts[option]}]
    db.log_event("fundamentos_respuesta", session_id, student["id"], {"course": course.id, "ok": ok})
    if not ok:
        messages.append(_msg(q["feedback"][option] + " Vuelve a leer las tarjetas y elige otra vez.",
                             "feedback_wrong"))
        return _save_and_view(session_id, student, state, messages)
    db.log_event("fundamentos", session_id, student["id"], {"course": course.id})
    messages.append(_msg("¡Exacto! Ya sabes por qué funciona. Ahora veamos qué tanto sabes hacer.",
                         "feedback_ok"))
    messages += _begin_diagnostic(state, course)
    return _save_and_view(session_id, student, state, messages)


def _resume_summary(student: dict, state: dict, course: Course, away: float) -> str:
    phase = PHASE_LABELS[state["phase"]]
    skill = course.skill_names.get(state.get("skill") or "", course.title)
    when = "hace un momento" if away < 1 else (f"hace {int(away)} día" + ("s" if int(away) != 1 else ""))
    return (f"¡Qué gusto verte, {student['name']}! Nos quedamos {when} en {phase.lower()} de "
            f"«{skill}». Tu avance está guardado justo donde lo dejaste.")


def _begin_review(state: dict, course: Course, mastered: list[str]) -> list[dict]:
    if state["phase"] in ("practica", "explicacion", "transferencia"):
        # Guardamos el punto exacto para regresar después del repaso
        snapshot = {k: state[k] for k in ("phase", "skill", "current", "hints_shown",
                                          "attempts_on_current", "streak", "streak_nohint",
                                          "exercises_in_skill", "practice_queue")}
        state["resume_after_review"] = snapshot
    state["phase"] = "repaso"
    state["review_queue"] = list(mastered)
    state["skill"] = state["review_queue"].pop(0)
    _next_exercise_for(state, course, state["skill"])
    return [_msg("Como pasó un tiempo, primero revisemos qué recuerdas. Es un repaso rápido, "
                 "no un examen: así sé si conviene reforzar algo.", "info")]


def _begin_explanation(state: dict, course: Course, skill: str) -> list[dict]:
    state["phase"] = "explicacion"
    state["skill"] = skill
    state["current"] = None
    state["streak"] = 0
    state["streak_nohint"] = False
    state["exercises_in_skill"] = 0
    state["stuck"] = False
    order = list(course.check_question(skill)["options"])
    random.shuffle(order)
    state["check_order"] = order
    n = len(course.explanation(skill)["body"])
    return [_msg(f"Vamos con: {course.skill_names[skill]}. Son {n} ideas cortas y una pregunta.", "info")]


def _exam_plan(course: Course) -> list[dict]:
    """Un ejercicio por habilidad (de la más fácil a la más difícil), un problema en contexto y
    una pregunta de «por qué». Si el curso tiene pocas habilidades, se agregan ejercicios de las
    más avanzadas hasta llegar a EXAM_SIZE."""
    questions = course.exam_questions()
    tail = int(bool(course.transfer_skill)) + int(bool(questions))
    skills = list(course.skills)
    extra = list(reversed(skills))
    while len(skills) + tail < EXAM_SIZE:
        skills.append(extra[(len(skills) - len(course.skills)) % len(extra)])
    skills.sort(key=course.skills.index)
    items = [{"kind": "ejercicio", "skill": s} for s in skills]
    if course.transfer_skill:
        items.append({"kind": "problema", "skill": course.transfer_skill})
    if questions:
        qi = random.randrange(len(questions))
        order = list(questions[qi]["options"])
        random.shuffle(order)
        items.append({"kind": "concepto", "q": qi, "order": order})
    return items


def _exam_item(state: dict) -> Optional[dict]:
    exam = state.get("exam")
    if state.get("phase") != "evaluacion" or not exam or exam["i"] >= len(exam["items"]):
        return None
    return exam["items"][exam["i"]]


def _load_exam_item(state: dict, course: Course) -> None:
    item = _exam_item(state)
    if item["kind"] == "concepto":
        state["current"] = None
        state["skill"] = None
        state["step"] = None
        state["prediction"] = None
        return
    state["skill"] = item["skill"]
    avoid = set(state.get("used", []))
    ex = course.transfer(random.Random(), avoid) if item["kind"] == "problema" else None
    if ex is None:
        ex = course.generate(item["skill"], random.Random(), avoid)
    _set_exercise(state, course, ex)


def _begin_exam(state: dict, course: Course) -> list[dict]:
    items = _exam_plan(course)
    state["phase"] = "evaluacion"
    state["exam"] = {"items": items, "i": 0, "results": []}
    state["practice_queue"] = []
    state["review_queue"] = []
    state["resume_after_review"] = None
    _load_exam_item(state, course)
    return [_msg(f"Evaluación final: {len(items)} preguntas para comprobar lo que aprendiste. Aquí no hay "
                 f"pistas ni ayuda: es tu turno de demostrarlo. Apruebas con {EXAM_PASS} de {len(items)}. "
                 "Si no, repasamos lo que faltó y la vuelves a presentar. Al final te digo cómo te fue "
                 "en cada pregunta.", "info")]


def _exam_record(state: dict, course: Course, student: dict, session_id: int, ok: bool,
                 detail: dict) -> list[dict]:
    exam = state["exam"]
    item = _exam_item(state)
    exam["results"].append({"kind": item["kind"], "skill": item.get("skill"), "ok": ok, **detail})
    exam["i"] += 1
    if exam["i"] < len(exam["items"]):
        _load_exam_item(state, course)
        return [_msg(f"Respuesta guardada. Pregunta {exam['i'] + 1} de {len(exam['items'])}.", "feedback")]
    return _finish_exam(state, course, student, session_id)


def _finish_exam(state: dict, course: Course, student: dict, session_id: int) -> list[dict]:
    res = state["exam"]["results"]
    score, total = sum(1 for r in res if r["ok"]), len(res)
    passed = score >= min(EXAM_PASS, total)
    db.log_event("evaluacion", session_id, student["id"],
                 {"course": course.id, "score": score, "total": total, "passed": passed,
                  "items": [{"kind": r["kind"], "skill": r.get("skill"), "ok": r["ok"]} for r in res]})
    state["exam"] = None
    state["current"] = None
    # Resultado por pregunta: qué estuvo bien y qué revisar. Nunca la respuesta correcta.
    msgs = [{"role": "tutor", "kind": "exam_result",
             "text": f"Resultado de tu evaluación final: {score} de {total}.",
             "exam": {"score": score, "total": total, "pass_mark": EXAM_PASS, "passed": passed,
                      "items": [{k: r.get(k) for k in ("label", "prompt", "answer", "ok", "note")}
                                for r in res]}}]
    if passed:
        msgs.append(_msg(f"¡Aprobaste la evaluación final con {score} de {total}! Lo resolviste sin pistas "
                         f"ni ayuda: eso demuestra que lo entiendes. Ganaste la constancia de «{course.title}».",
                         "milestone"))
        return msgs + _close(state, student, course)
    failed = {r["skill"] for r in res if not r["ok"] and r.get("skill")}
    weak = [s for s in course.skills if s in failed] or [course.skills[-1]]
    for s in weak:
        db.unmark_mastered(student["id"], s)
    names = ", ".join(f"«{course.skill_names[s]}»" for s in weak)
    msgs.append(_msg(f"Esta vez no alcanzó: necesitas {EXAM_PASS} de {total}. No es un castigo, es "
                     f"información: ya sé qué reforzar. Repasemos {names} y luego la presentas otra vez.",
                     "info"))
    state["practice_queue"] = weak[1:]
    return msgs + _begin_explanation(state, course, weak[0])


def _next_after_mastery(state: dict, course: Course, student: dict) -> list[dict]:
    mastery = db.get_mastery(student["id"])
    queue = [s for s in state.get("practice_queue", []) if not mastery.get(s, {}).get("mastered")]
    if queue:
        state["practice_queue"] = queue[1:]
        return _begin_explanation(state, course, queue[0])
    return _begin_exam(state, course)


# --------------------------------------------------------------------------
# Acciones
# --------------------------------------------------------------------------
def check_explanation(session_id: int, option: str, student_id: Optional[int] = None) -> dict:
    """Pregunta de comprobación al final de la explicación: solo se avanza si se entendió la idea."""
    _, student, state = _load(session_id, student_id)
    if state["phase"] != "explicacion":
        raise TutorError("no hay una explicación pendiente")
    course = _course(state)
    q = course.check_question(state["skill"])
    if option not in q["options"]:
        raise TutorError("opción desconocida")
    messages = [{"role": "student", "kind": "answer", "text": q["options"][option]}]
    db.log_event("comprobacion", session_id, student["id"],
                 {"skill": state["skill"], "option": option, "ok": option == q["correct"]})
    if option != q["correct"]:
        messages.append(_msg(q["feedback"][option] + " Vuelve a leer la idea y elige otra vez.",
                             "feedback_wrong"))
        return _save_and_view(session_id, student, state, messages)
    state["phase"] = "practica"
    _next_exercise_for(state, course, state["skill"])
    state["exercises_in_skill"] = 1
    messages += [_msg("¡Exacto! Ya tienes la idea.", "feedback_ok"),
                 _msg("¡Ahora tú! Si te atoras, pide una pista.", "info")]
    return _save_and_view(session_id, student, state, messages)


def exam_option(session_id: int, option: str, student_id: Optional[int] = None) -> dict:
    """Pregunta de «por qué» de la evaluación final."""
    _, student, state = _load(session_id, student_id)
    item = _exam_item(state)
    if not item or item["kind"] != "concepto":
        raise TutorError("no hay una pregunta de la evaluación pendiente")
    course = _course(state)
    q = course.exam_questions()[item["q"]]
    if option not in q["options"]:
        raise TutorError("opción desconocida")
    ok = option == q["correct"]
    messages = [{"role": "student", "kind": "answer", "text": q["options"][option]}]
    messages += _exam_record(state, course, student, session_id, ok,
                             {"label": "Pregunta de por qué", "prompt": q["question"],
                              "answer": q["options"][option], "note": None if ok else q["feedback"][option]})
    status = "completed" if state["phase"] == "cierre" else "active"
    return _save_and_view(session_id, student, state, messages, status)


def predict(session_id: int, choice: str, student_id: Optional[int] = None) -> dict:
    """Estimación antes de calcular: ¿mayor o menor que X?"""
    _, student, state = _load(session_id, student_id)
    if not _prediction_pending(state):
        raise TutorError("no hay una predicción pendiente")
    if choice not in ("mayor", "menor"):
        raise TutorError("elige mayor o menor")
    course = _course(state)
    ex = course.load(state["current"])
    ok, text, visual = course.prediction_feedback(ex, state["prediction"], choice)
    state["prediction"]["answered"] = choice
    state["prediction"]["ok"] = ok
    state["last_at"] = _now_iso()
    db.log_event("prediccion", session_id, student["id"], {"ok": ok})
    messages = [{"role": "student", "kind": "answer", "text": choice.capitalize()},
                _msg(text, "feedback_ok" if ok else "feedback_wrong", visual)]
    return _save_and_view(session_id, student, state, messages)


def step_answer(session_id: int, values: list[str], student_id: Optional[int] = None) -> dict:
    """El alumno responde el mini paso de la pista actual. Si se traba, NO se revela:
    se activa la ayuda extra."""
    _, student, state = _load(session_id, student_id)
    if not _step_pending(state):
        raise TutorError("no hay un paso pendiente")
    st = state["step"]
    results = check_step(st["data"], values)
    messages: list[dict] = [{"role": "student", "kind": "answer", "text": ", ".join(v for v in values if v)}]
    state["last_at"] = _now_iso()
    if all(results):
        st["done"] = True
        db.log_event("paso_ok", session_id, student["id"])
        hints_total = len(_course(state).hints(_course(state).load(state["current"])))
        more = state["hints_shown"] < hints_total
        messages.append(_msg("¡Eso! Paso resuelto. " + ("Úsalo para el ejercicio o pide la siguiente pista."
                                                        if more else "Úsalo para resolver el ejercicio."),
                             "feedback_ok"))
        return _save_and_view(session_id, student, state, messages)
    st["tries"] = st.get("tries", 0) + 1
    if st["tries"] >= STEP_TRIES_BEFORE_HELP and not state.get("stuck") and state["phase"] == "practica":
        state["stuck"] = True
        db.log_event("ayuda_activada", session_id, student["id"], {"motivo": "paso"})
        messages.append(_msg("Este paso se está complicando, y está bien. " + HELP_OPTIONS_TEXT, "info"))
    else:
        messages.append(_msg("Ese paso todavía no. Vuelve a leer la pista y prueba otra vez.",
                             "feedback_wrong"))
    return _save_and_view(session_id, student, state, messages)


def answer(session_id: int, raw: str, dont_know: bool = False, student_id: Optional[int] = None) -> dict:
    _, student, state = _load(session_id, student_id)
    phase = state["phase"]
    if not state.get("current") or phase in ("explicacion", "cierre", "fundamentos"):
        raise TutorError("no hay ejercicio activo")
    if _prediction_pending(state):
        raise TutorError("primero haz tu predicción: ¿mayor o menor?")
    course = _course(state)
    ex = course.load(state["current"])
    style = _style(student)
    messages: list[dict] = [{"role": "student", "kind": "answer", "text": raw if not dont_know else "No lo sé todavía"}]
    elapsed = _seconds_since_last(state)
    state["last_at"] = _now_iso()

    not_simplified = False
    if dont_know:
        if phase not in ("diagnostico", "evaluacion"):
            raise TutorError("«No lo sé» solo existe en el diagnóstico; aquí puedes pedir una pista")
        result_correct, misconception = False, "no_sabe"
    else:
        ev = course.evaluate(ex, raw)
        if ev.unparsable:
            db.log_event("error_de_dedo", session_id, student["id"], {"raw": raw})
            messages.append(_msg(course.feedback_for(ex, "no_interpretable"), "warning"))
            return _save_and_view(session_id, student, state, messages)
        result_correct, misconception, not_simplified = ev.correct, ev.misconception, ev.not_simplified

    db.record_attempt(session_id, student["id"], phase, ex.skill, ex.to_dict(), raw,
                      result_correct, misconception, state["hints_shown"])
    if not result_correct and not dont_know:
        state["wrong_answers"] = (state.get("wrong_answers", []) + [raw])[-3:]

    # Respuestas al azar: varios errores muy rápidos seguidos -> pedir calma (sin castigar)
    slow_down = []
    if not result_correct and phase in ("practica", "repaso") and elapsed < FAST_SECONDS:
        state["fast_wrong"] = state.get("fast_wrong", 0) + 1
        if state["fast_wrong"] == FAST_WRONG_LIMIT:
            db.log_event("respuestas_rapidas", session_id, student["id"])
            slow_down = [_msg("Vas muy rápido 🙂. Antes de otro intento, lee otra vez el ejercicio: "
                              "¿qué parte te está costando? Una pista leída con calma ayuda más que "
                              "adivinar.", "slowdown")]

    if phase == "diagnostico":
        messages += _handle_diagnostic(state, course, student, ex, result_correct)
    elif phase == "repaso":
        messages += _handle_review(state, course, student, ex, raw, result_correct, misconception, style)
    elif phase == "evaluacion":
        label = ("Problema en contexto" if _exam_item(state)["kind"] == "problema"
                 else course.skill_names[ex.skill])
        note = None if result_correct else (
            "La dejaste para después: es justo lo que conviene repasar." if dont_know
            else course.feedback_for(ex, misconception))
        messages += _exam_record(state, course, student, session_id, result_correct,
                                 {"label": label, "prompt": course.prompt(ex),
                                  "answer": None if dont_know else raw, "note": note})
    else:
        messages += _handle_practice(state, course, student, ex, raw, not_simplified, result_correct,
                                     misconception, style)

    messages += slow_down
    status = "completed" if state["phase"] == "cierre" else "active"
    return _save_and_view(session_id, student, state, messages, status)


def _handle_diagnostic(state, course: Course, student, ex, correct: bool) -> list[dict]:
    state["diag_results"][ex.skill] = correct
    db.update_mastery(student["id"], ex.skill, correct, 0)
    state["diag_queue"] = [s for s in state["diag_queue"] if s != ex.skill]
    msgs = [_msg("¡Anotado, gracias!" if correct else "Anotado. Esto me ayuda a saber por dónde empezar.",
                 "feedback")]
    if state["diag_queue"]:
        state["skill"] = state["diag_queue"][0]
        _next_exercise_for(state, course, state["skill"])
        return msgs

    failed = [s for s in course.skills if not state["diag_results"].get(s)]
    for s in course.skills:
        if s in failed:
            break
        db.mark_mastered(student["id"], s)  # prerrequisitos demostrados
    if not failed:
        msgs.append(_msg("¡Respondiste todo bien! Vamos directo a la evaluación final para confirmarlo.",
                         "info"))
        return msgs + _begin_exam(state, course)
    start = failed[0]
    state["practice_queue"] = list(course.skills[course.skills.index(start) + 1:])
    msgs.append(_msg(f"Listo. Según tus respuestas, empezaremos por «{course.skill_names[start]}». "
                     "Si en algún momento quieres ir más rápido o más despacio, dímelo.", "info"))
    return msgs + _begin_explanation(state, course, start)


def _feedback_wrong(style: dict, course: Course, ex, misconception: Optional[str]) -> str:
    return f"{style['wrong_intro']} {course.feedback_for(ex, misconception)}"


def _handle_practice(state, course: Course, student, ex, raw, not_simplified, correct, misconception,
                     style) -> list[dict]:
    hints_used = state["hints_shown"]
    db.update_mastery(student["id"], ex.skill, correct, hints_used)
    if not correct:
        state["attempts_on_current"] += 1
        state["streak"] = 0
        msgs = [_msg(_feedback_wrong(style, course, ex, misconception), "feedback_wrong",
                     course.misconception_visual(ex, raw, misconception))]
        pred = state.get("prediction") or {}
        if misconception == "suma_num_y_den" and pred.get("ok") and pred.get("ref_kind") == "mayor_fraccion":
            msgs.append(_msg(f"Tú predijiste que sería mayor que {pred['ref']}, y tu resultado no lo es. "
                             "¡Tu estimación ya te estaba avisando!", "info"))
        total = len(course.hints(ex))
        if hints_used >= total:
            if not state.get("stuck"):
                state["stuck"] = True
                db.log_event("ayuda_activada", None, student["id"], {"motivo": "pistas_agotadas"})
                msgs.append(_msg("Ya usaste todas las pistas. " + HELP_OPTIONS_TEXT, "info"))
        elif state["attempts_on_current"] >= 2 and hints_used == 0:
            msgs.append(_msg("¿Quieres una pista? Están para eso.", "info"))
        return msgs

    msgs = [_msg(random.choice(style["correct"]), "feedback_ok")]
    if not_simplified:
        msgs.append(_msg("Tu resultado es correcto. Bonus: se puede simplificar dividiendo arriba y "
                         "abajo entre el mismo número.", "info"))
    if state.get("attempts_on_current", 0) >= GUESS_ATTEMPTS:
        # Muchos intentos antes de atinar: puede ser al tanteo, no cuenta para el dominio
        state["streak"] = 0
        msgs.append(_msg("Lo lograste tras varios intentos. Hagamos otro con calma para ver que ya "
                         "lo dominas.", "info"))
    elif hints_used <= MAX_HINTS_FOR_MASTERY:
        state["streak"] += 1
        state["streak_nohint"] = state["streak_nohint"] or hints_used == 0
    else:
        state["streak"] = 0
        msgs.append(_msg("Lo lograste con ayuda; hagamos otro para que te salga sin pistas.", "info"))

    if state["streak"] >= MASTERY_STREAK and state["streak_nohint"]:
        db.mark_mastered(student["id"], ex.skill)
        msgs.append(_msg(f"¡Dominaste «{course.skill_names[ex.skill]}»! No por hacer muchos ejercicios, "
                         "sino porque ya lo resuelves por tu cuenta.", "milestone"))
        return msgs + _next_after_mastery(state, course, student)

    state["exercises_in_skill"] += 1
    if state["exercises_in_skill"] > MAX_EXERCISES_PER_SKILL:
        msgs.append(_msg("Llevas un buen rato con este tema. Si quieres, toma un descanso: "
                         "guardo tu lugar exacto.", "empathy"))
    _next_exercise_for(state, course, ex.skill)
    return msgs


def _handle_review(state, course: Course, student, ex, raw, correct, misconception, style) -> list[dict]:
    db.update_mastery(student["id"], ex.skill, correct, state["hints_shown"])
    if not correct:
        # Refuerzo puntual: esta habilidad vuelve a práctica
        msgs = [_msg(_feedback_wrong(style, course, ex, misconception), "feedback_wrong",
                     course.misconception_visual(ex, raw, misconception)),
                _msg(f"Parece que «{course.skill_names[ex.skill]}» se te olvidó un poco: es normal. "
                     "Hagamos un refuerzo corto.", "info")]
        db.unmark_mastered(student["id"], ex.skill)
        state["review_queue"] = []
        # Tras el refuerzo seguimos con las habilidades siguientes (las ya dominadas se saltan)
        state["practice_queue"] = list(course.skills[course.skills.index(ex.skill) + 1:])
        state["resume_after_review"] = None
        return msgs + _begin_explanation(state, course, ex.skill)

    msgs = [_msg(random.choice(style["correct"]) + " Lo recuerdas bien.", "feedback_ok")]
    if state.get("review_queue"):
        state["skill"] = state["review_queue"].pop(0)
        _next_exercise_for(state, course, state["skill"])
        return msgs
    snap = state.get("resume_after_review")
    if snap:
        state.update(snap)
        state["resume_after_review"] = None
        state["step"] = None
        state["prediction"] = None
        state["stuck"] = False
        msgs.append(_msg("¡Repaso superado! Seguimos justo donde te quedaste.", "info"))
        return msgs
    mastery = db.get_mastery(student["id"])
    pending = [s for s in course.skills if not mastery.get(s, {}).get("mastered")]
    if pending:
        state["practice_queue"] = pending[1:]
        return msgs + _begin_explanation(state, course, pending[0])
    if not db.exam_status(student["id"], course.id)["passed"]:
        msgs.append(_msg("Conservas todo lo que aprendiste. Solo te falta aprobar la evaluación final.",
                         "milestone"))
        return msgs + _begin_exam(state, course)
    msgs.append(_msg("Conservas todo lo que aprendiste. ¡Excelente memoria!", "milestone"))
    return msgs + _close(state, student, course)


def _close(state: dict, student: dict, course: Course) -> list[dict]:
    state["phase"] = "cierre"
    state["current"] = None
    prog = progress_for(student["id"], course)
    mastered = [s["name"] for s in prog["skills"] if s["mastered"]]
    text = "Resumen de hoy: dominaste " + (", ".join(mastered) if mastered else "tus primeros pasos") + "."
    if prog["exam"]["passed"]:
        text += f" Evaluación final: {prog['exam']['score']} de {prog['exam']['total']}."
    if prog["errors_overcome"]:
        text += " Además dejaste atrás este error: " + "; ".join(prog["errors_overcome"]) + "."
    nxt = _next_course(student["id"], course)
    text += (f" Cuando quieras, sigue con «{nxt.title}»." if nxt
             else " ¡Ya recorriste todos los cursos disponibles!")
    return [_msg(text, "summary")]


def _next_course(student_id: int, current: Course) -> Optional[Course]:
    mastery = db.get_mastery(student_id)
    for c in all_courses():
        if c.id == current.id or c.order < current.order:
            continue
        if not all(mastery.get(s, {}).get("mastered") for s in c.skills):
            return c
    return None


def _show_hint(state: dict, course: Course) -> list[dict]:
    ex = course.load(state["current"])
    hs = course.hints(ex)
    i = state["hints_shown"]
    state["hints_shown"] = i + 1
    state["last_at"] = _now_iso()
    step = course.hint_step(ex, i)
    state["step"] = {"data": step, "done": False, "tries": 0} if step else None
    text = f"Pista {i + 1} de {len(hs)}: {hs[i]}"
    if i == len(hs) - 1 and not step:
        text += " (Es la última pista: con ella ya puedes resolverlo tú.)"
    return [_msg(text, "hint", course.hint_visual(ex, i))]


def hint(session_id: int, student_id: Optional[int] = None) -> dict:
    _, student, state = _load(session_id, student_id)
    view = _view(session_id, student, state, [])
    if not view["hints"]["can_hint"]:
        raise TutorError("no hay pistas disponibles en este momento")
    return _save_and_view(session_id, student, state, _show_hint(state, _course(state)))


def example(session_id: int, student_id: Optional[int] = None) -> dict:
    """Ayuda extra: un ejemplo parecido resuelto, con OTROS números."""
    _, student, state = _load(session_id, student_id)
    if not _stuck(state):
        raise TutorError(HELP_LOCKED_TEXT)
    course = _course(state)
    ex = course.load(state["current"])
    w = course.worked_example(ex, random.Random())
    db.log_event("ejemplo", session_id, student["id"])
    messages = [_msg(f"Mira este ejemplo con otros números.\n{w['prompt']}\n{w['text']}\n"
                     "Ahora intenta el tuyo siguiendo los mismos pasos.", "example", w.get("visual"))]
    return _save_and_view(session_id, student, state, messages)


def skip(session_id: int, student_id: Optional[int] = None) -> dict:
    """Ayuda extra: cambiar a otro ejercicio de la misma habilidad, sin penalización."""
    _, student, state = _load(session_id, student_id)
    if not _stuck(state):
        raise TutorError(HELP_LOCKED_TEXT)
    course = _course(state)
    db.log_event("cambio_ejercicio", session_id, student["id"])
    state["exercises_in_skill"] += 1
    _next_exercise_for(state, course, state["skill"])
    return _save_and_view(session_id, student, state,
                          [_msg("Va, probemos con otro. El anterior no cuenta en tu contra.", "info")])


def pause(session_id: int, student_id: Optional[int] = None) -> dict:
    _, student, state = _load(session_id, student_id)
    db.log_event("pausa", session_id, student["id"])
    msg = _msg("Guardé tu avance exacto. Descansa, toma agua. ¡Sin prisa!", "empathy")
    return _save_and_view(session_id, student, state, [msg], status="paused")


def free_message(session_id: int, text: str, student_id: Optional[int] = None) -> dict:
    """Pregunta libre a Loop (IA). Disponible al leer una explicación o como ayuda extra."""
    _, student, state = _load(session_id, student_id)
    text = (text or "").strip()[:500]
    if not text:
        raise TutorError("mensaje vacío")
    messages: list[dict] = [{"role": "student", "kind": "message", "text": text}]

    if _contains_any(text, FRUSTRATION_WORDS):
        db.log_event("frustracion", session_id, student["id"], {"text": text})
        messages.append(_msg(
            "Te entiendo: esto cuesta y sentirse así es normal cuando estamos aprendiendo algo "
            "de verdad. Equivocarte no dice nada malo de ti. ¿Quieres tomar un descanso (guardo "
            "tu lugar) o prefieres que lo veamos con un paso más pequeño?", "empathy"))
        return _save_and_view(session_id, student, state, messages)

    stuck = _stuck(state)
    if not (state["phase"] in ("explicacion", "fundamentos") or stuck):
        raise TutorError(HELP_LOCKED_TEXT)

    course = _course(state)
    ex = course.load(state["current"]) if state.get("current") else None
    if ex and _contains_any(text, ANSWER_REQUEST_WORDS):
        db.log_event("pide_respuesta", session_id, student["id"])
        messages.append(_msg("Si te doy la respuesta, el que aprende soy yo 😉. Mejor cuéntame qué "
                             "parte no te queda clara, o mira un ejemplo parecido resuelto.", "info"))
        return _save_and_view(session_id, student, state, messages)

    # Pregunta libre -> IA con memoria estructurada (no historial largo)
    skill = state.get("skill")
    mastery = {k: v["mastery"] for k, v in db.get_mastery(student["id"]).items() if k in course.skills}
    ctx = TutorContext(
        student_name=student["name"],
        tutor_style=student.get("tutor_style") or DEFAULT_STYLE,
        phase=state["phase"],
        skill=course.skill_names.get(skill or "", skill),
        exercise_prompt=course.prompt(ex) if ex else None,
        hints_already_shown=course.hints(ex)[: state["hints_shown"]] if ex else [],
        recent_misconceptions=[m["misconception"] for m in db.frequent_misconceptions(student["id"])],
        mastery=mastery,
        recent_turns=state.get("turns", []),
        course_title=course.title,
        extra_level=stuck,
        alt_explanation=course.alt_explanation(skill) if skill else
        " ".join(c["text"] for c in (course.theory() or {"cards": []})["cards"]) or None,
        wrong_answers=list(state.get("wrong_answers", [])),
    )
    reply = get_provider().reply(ctx, text)
    db.log_ai_usage(session_id, reply.provider, reply.model, reply.input_tokens, reply.output_tokens)
    reply_text = reply.text
    if ex and leaks_answer(reply_text, course.answer_forms(ex)):
        # Red de seguridad: si la IA revela el resultado, lo reemplazamos por contenido verificado
        db.log_event("ia_filtrada", session_id, student["id"])
        reply_text = ("Prefiero no darte el resultado 😉. Veámoslo de otra forma: "
                      f"{course.alt_explanation(skill)} ¿Qué paso intentarías ahora?")
    if stuck:
        db.log_event("ayuda_extra", session_id, student["id"])
    state["turns"] = (state.get("turns", []) + [{"role": "user", "content": text},
                                                {"role": "assistant", "content": reply_text}])[-4:]
    messages.append(_msg(reply_text, "ai"))
    return _save_and_view(session_id, student, state, messages)


def get_view(session_id: int, student_id: Optional[int] = None) -> dict:
    session, student, state = _load(session_id, student_id)
    return _view(session_id, student, state, [], session["status"])
