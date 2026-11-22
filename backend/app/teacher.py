"""Panel docente: agrupa los errores de razonamiento de un grupo y sugiere dónde intervenir.

La idea es que el docente lea un reporte de un minuto («El 60% del grupo suma
numeradores y denominadores») en vez de revisar 45 libretas. Todo se calcula con
SQL sobre los intentos ya guardados, sin llamadas a la IA: el costo es $0.

Las sugerencias de intervención son un borrador: deben revisarse con la docente.
"""
from __future__ import annotations

import random
import re
from typing import Optional

from . import db
from .fractions_engine import SKILLS, Exercise, generate_exercise

DEMO_COURSE = "MAT-FRAC"

# Cómo nombramos cada error para el docente, y qué puede hacer en clase.
MISCONCEPTIONS = {
    "suma_num_y_den": {
        "label": "Suma numeradores y denominadores (1/2 + 1/3 = 2/5)",
        "action": "Pide al grupo que sume 1/2 + 1/2 con su regla y que dibuje el resultado en "
                  "barras: el resultado (2/4) es otra vez media barra. Discutan por qué juntar dos "
                  "mitades no puede dar una mitad.",
    },
    "no_convirtio_numeradores": {
        "label": "Encuentra el denominador común pero no convierte los numeradores",
        "action": "Usa barras partidas: 1/2 en sextos son 3 pedazos, no 1. Pide que verbalicen "
                  "«si parto cada pedazo en 3, ¿cuántos pedazos tengo ahora?».",
    },
    "pensamiento_aditivo": {
        "label": "Suma en vez de multiplicar para hacer equivalencias",
        "action": "Compara 2/3 y 11/12 (sumar 9 arriba y abajo) con barras del mismo largo: no "
                  "son la misma cantidad. Refuerza «lo que multiplicas abajo, lo multiplicas arriba».",
    },
    "solo_factor": {
        "label": "Encuentra el factor pero no lo aplica al numerador",
        "action": "Pide que escriban el procedimiento en dos renglones: primero el denominador y "
                  "luego el numerador, con el mismo factor.",
    },
    "multiplico": {
        "label": "Multiplica las fracciones en lugar de sumarlas",
        "action": "Plantea un problema de juntar cantidades (dos pedazos de pizza) y pregunta qué "
                  "operación representa «juntar».",
    },
    "solo_una_fraccion": {
        "label": "Deja una de las fracciones sin sumar",
        "action": "Pide que estimen antes de calcular: ¿el resultado debe ser mayor que cada fracción?",
    },
    "invertida": {
        "label": "Escribe la fracción volteada",
        "action": "Repasa brevemente qué indica el numerador (cuántos tomo) y el denominador "
                  "(en cuántas partes partí).",
    },
    "error_calculo": {
        "label": "Procedimiento correcto, errores de cuentas",
        "action": "No es un problema conceptual: conviene practicar tablas o revisar el resultado "
                  "con una estimación.",
    },
    "denominador_distinto": {
        "label": "Da una equivalente, pero no con el denominador pedido",
        "action": "Aclara la instrucción y pide que comprueben con qué número se multiplicó.",
    },
}

ATTENTION_FRUSTRATION = 2   # eventos de frustración a partir de los cuales se sugiere acercarse
ATTENTION_LOW_ACCURACY = 0.4


def normalize_group(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    c = re.sub(r"[^A-Za-z0-9-]", "", code.strip().upper())[:12]
    return c or None


def _student_row(s: dict, course, labels: dict) -> dict:
    act = db.student_activity(s["id"], course.id, course.skills)
    mastery = db.get_mastery(s["id"])
    mastered = [k for k in course.skills if mastery.get(k, {}).get("mastered")]
    errors = db.student_misconceptions(s["id"], course.skills)
    frustration = db.count_events(s["id"], "frustracion")
    accuracy = (act["correct"] / act["attempts"]) if act["attempts"] else None
    reasons = []
    if frustration >= ATTENTION_FRUSTRATION:
        reasons.append("mostró frustración varias veces")
    if accuracy is not None and act["attempts"] >= 5 and accuracy < ATTENTION_LOW_ACCURACY:
        reasons.append("muchos intentos sin acertar")
    if act["hints"] >= 8 and len(mastered) < len(course.skills):
        reasons.append("depende mucho de las pistas")
    return {
        "id": s["id"],
        "name": s["name"],
        "simulated": bool(s.get("simulated")),
        "current_skill": course.skill_names.get(act.get("skill") or "", None),
        "completed": act.get("status") == "completed",
        "mastered": len(mastered),
        "attempts": act["attempts"],
        "accuracy": round(accuracy, 2) if accuracy is not None else None,
        "hints_used": act["hints"],
        "errors": [labels[e]["label"] for e in errors if e in labels],
        "needs_attention": reasons,
        "last_activity": act["last"],
    }


def group_summary(group_code: str, course_id: str = DEMO_COURSE) -> dict:
    from .courses import get_course
    course = get_course(course_id)
    labels = course.teacher_labels()
    students = db.group_students(group_code)
    n = len(students)
    rows = [_student_row(s, course, labels) for s in students]
    misconceptions = []
    for m in db.group_misconceptions(group_code, course.skills):
        info = labels.get(m["misconception"])
        if not info:
            continue
        misconceptions.append({
            "id": m["misconception"],
            "label": info["label"],
            "action": info["action"],
            "students": m["students"],
            "times": m["times"],
            "pct": round(100 * m["students"] / n) if n else 0,
        })

    skills = []
    for k in course.skills:
        done = sum(1 for s in students if db.get_mastery(s["id"]).get(k, {}).get("mastered"))
        skills.append({"id": k, "name": course.skill_names[k], "mastered": done,
                       "pct": round(100 * done / n) if n else 0})

    headline = _headline(n, misconceptions, skills)
    return {
        "group": group_code,
        "course": {"id": course.id, "title": course.title},
        "students_total": n,
        "students_active": sum(1 for r in rows if r["attempts"] > 0),
        "completed": sum(1 for r in rows if r["completed"]),
        "simulated": any(r["simulated"] for r in rows),
        "headline": headline,
        "misconceptions": misconceptions,
        "skills": skills,
        "attention": [r for r in rows if r["needs_attention"]],
        "students": rows,
    }


def _headline(n: int, misconceptions: list[dict], skills: list[dict]) -> str:
    if n == 0:
        return "Todavía no hay alumnos en este grupo."
    if not misconceptions:
        return "Sin errores de razonamiento frecuentes por ahora."
    top = misconceptions[0]
    text = (f"El {top['pct']}% del grupo ({top['students']} de {n}) comete este error: "
            f"{top['label'][0].lower() + top['label'][1:]}.")
    weakest = min(skills, key=lambda s: s["pct"])
    text += f" La habilidad menos dominada es «{weakest['name']}» ({weakest['pct']}% la domina)."
    return text


# --------------------------------------------------------------------------
# Grupo de ejemplo para la demo (datos SIMULADOS, marcados como tales)
# --------------------------------------------------------------------------
DEMO_GROUP = "DEMO-1A"
_DEMO_NAMES = ["Ana", "Luis", "Sofía", "Diego", "Valeria", "Mateo", "Ximena", "Emiliano",
               "Regina", "Santiago", "Camila", "Leonardo", "Renata", "Iker", "Fernanda",
               "Gael", "Daniela", "Rodrigo", "Paula", "Andrés"]


def _wrong_answer(ex: Exercise, misconception: str) -> str:
    if misconception == "suma_num_y_den":
        return f"{ex.a + ex.c}/{ex.b + ex.d}"
    if misconception == "no_convirtio_numeradores":
        return f"{ex.a + ex.c}/{ex.common_den}"
    if misconception == "pensamiento_aditivo":
        return str(ex.a + (ex.target_den - ex.b))
    if misconception == "multiplico":
        return f"{ex.a * ex.c}/{ex.b * ex.d}"
    return "1/1"


def seed_demo_group(rng: Optional[random.Random] = None) -> str:
    """Crea (o recrea) un grupo de 20 alumnos simulados con errores realistas."""
    rng = rng or random.Random(42)
    db.delete_group(DEMO_GROUP)
    for i, name in enumerate(_DEMO_NAMES):
        s = db.create_student(name, "paciente", DEMO_GROUP, simulated=True)
        sid = db.create_session(s["id"], DEMO_COURSE, {"course": DEMO_COURSE, "phase": "practica",
                                                        "skill": None})
        # Perfil: ~60% con el error 2/5, ~30% no convierte numeradores, ~25% pensamiento aditivo
        profile = []
        if i % 5 in (0, 1, 2):
            profile.append(("suma_distinto_den", "suma_num_y_den"))
        if i % 10 in (3, 6, 9):
            profile.append(("suma_distinto_den", "no_convirtio_numeradores"))
        if i % 4 == 1:
            profile.append(("equivalencia", "pensamiento_aditivo"))
        if i == 7:
            profile.append(("suma_distinto_den", "multiplico"))

        level = 0
        for skill in SKILLS:
            errs = [m for sk, m in profile if sk == skill]
            for m in errs:
                for _ in range(rng.randint(1, 3)):
                    ex = generate_exercise(skill, rng)
                    db.record_attempt(sid, s["id"], "practica", skill, ex.to_dict(),
                                      _wrong_answer(ex, m), False, m, rng.randint(0, 2))
                    db.update_mastery(s["id"], skill, False, 0)
            # Acierta algunas veces
            for _ in range(rng.randint(1, 3)):
                ex = generate_exercise(skill, rng)
                db.record_attempt(sid, s["id"], "practica", skill, ex.to_dict(),
                                  f"{ex.answer.numerator}/{ex.answer.denominator}", True, None,
                                  rng.randint(0, 1))
                db.update_mastery(s["id"], skill, True, 0)
            if not errs or rng.random() < 0.35:
                db.mark_mastered(s["id"], skill)
                level += 1
            else:
                break
        state = {"course": DEMO_COURSE, "phase": "cierre" if level == len(SKILLS) else "practica",
                 "skill": SKILLS[min(level, len(SKILLS) - 1)]}
        db.save_session(sid, state, "completed" if level == len(SKILLS) else "active")
        if i in (4, 11):
            for _ in range(2):
                db.log_event("frustracion", sid, s["id"], {"text": "(simulado)"})
    return DEMO_GROUP
