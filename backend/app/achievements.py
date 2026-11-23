"""Logros y constancias.

Logros: premian CÓMO se piensa, no cuánto se hace. Nada de «resuelve 10
ejercicios»: se reconoce corregir un error propio, estimar antes de calcular,
resolver paso a paso, pedir ayuda a tiempo, descansar y regresar.

Constancias: una por curso, cuando se dominan todas sus habilidades y se aprueba
la evaluación final. Son internas y simbólicas: NO tienen valor curricular ni
validez oficial.
"""
from __future__ import annotations

from . import db
from .courses import all_courses

ACHIEVEMENTS = [
    {"id": "valiente", "icon": "🌱", "title": "Te animaste",
     "desc": "Respondiste tu primer ejercicio aunque no estuvieras seguro. Intentar es el primer paso."},
    {"id": "detective", "icon": "🔍", "title": "Detective de errores",
     "desc": "Te equivocaste, encontraste tu error y corregiste el mismo ejercicio sin pedir otra pista."},
    {"id": "estimador", "icon": "🎯", "title": "Buen estimador",
     "desc": "Antes de calcular, predijiste bien si el resultado sería mayor o menor."},
    {"id": "paso_a_paso", "icon": "🪜", "title": "Paso a paso",
     "desc": "Resolviste los pasos de las pistas y luego el ejercicio completo."},
    {"id": "error_vencido", "icon": "💪", "title": "Error vencido",
     "desc": "Cometiste un error de razonamiento y después lo dejaste atrás con dos aciertos."},
    {"id": "pregunta", "icon": "💬", "title": "Preguntar también es pensar",
     "desc": "Usaste la ayuda extra cuando te atoraste y después resolviste por tu cuenta."},
    {"id": "por_tu_cuenta", "icon": "🧭", "title": "Por tu cuenta",
     "desc": "Aprobaste una evaluación final, sin pistas ni ayuda."},
    {"id": "memoria", "icon": "🧠", "title": "Memoria de largo plazo",
     "desc": "Regresaste después de un tiempo y demostraste en el repaso que lo recuerdas."},
    {"id": "descanso", "icon": "☕", "title": "Pausa sabia",
     "desc": "Tomaste un descanso cuando lo necesitabas y regresaste a seguir aprendiendo."},
]

CERTIFICATE_NOTE = ("Constancia interna de ThinkLoop. Reconoce el aprendizaje en la plataforma; "
                    "no tiene valor curricular ni validez oficial.")


def achievements_for(student_id: int) -> list[dict]:
    facts = db.achievement_facts(student_id)
    return [{**a, "earned": bool(facts.get(a["id"])), "earned_at": facts.get(a["id"])}
            for a in ACHIEVEMENTS]


def certificates_for(student: dict) -> list[dict]:
    mastery = db.get_mastery(student["id"])
    out = []
    for c in all_courses():
        rows = [mastery.get(s, {}) for s in c.skills]
        done = sum(1 for m in rows if m.get("mastered"))
        exam = db.exam_status(student["id"], c.id)
        earned = done == len(c.skills) and exam["passed"]
        out.append({
            "course_id": c.id,
            "title": c.title,
            "level": c.level,
            "cover": c.cover,
            "earned": earned,
            "earned_at": exam["passed_at"] if earned else None,
            "pct": round(100 * (done + int(exam["passed"])) / (len(c.skills) + 1)),
            "exam": {"passed": exam["passed"], "score": exam["score"], "total": exam["total"],
                     "taken": exam["taken"]},
            "skills": [c.skill_names[s] for s in c.skills],
            "student_name": student["name"],
            "note": CERTIFICATE_NOTE,
            "content_status": c.summary()["meta"]["estado_label"],
        })
    return out
