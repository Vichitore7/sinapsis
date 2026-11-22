"""Catálogo de cursos (biblioteca curricular estructurada).

Cada curso vive en `content/<curso>.json` con el estándar de lección ThinkLoop
(objetivo, prerrequisitos, explicación, comprobación, pistas con pasos, errores
frecuentes, reto final y metadatos de fuente, licencia y estado de validación).
El campo "motor" indica qué código genera y califica sus ejercicios.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .base import Course, leaks_answer  # noqa: F401
from .fractions_course import FractionsCourse
from .generic import GenericCourse

CONTENT_DIR = Path(__file__).parent / "content"
DEFAULT_COURSE = "MAT-FRAC"
# Sesiones creadas antes del catálogo usaban este id de lección
LEGACY_LESSON_IDS = {"fracciones-suma-v1": "MAT-FRAC"}

_ENGINES = {"generico": GenericCourse, "fracciones": FractionsCourse}


class UnknownCourse(KeyError):
    pass


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Course]:
    courses = []
    for path in sorted(CONTENT_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        courses.append(_ENGINES[data["motor"]](data))
    courses.sort(key=lambda c: c.order)
    return {c.id: c for c in courses}


def all_courses() -> list[Course]:
    return list(_catalog().values())


def get_course(course_id: str | None) -> Course:
    cid = LEGACY_LESSON_IDS.get(course_id or DEFAULT_COURSE, course_id or DEFAULT_COURSE)
    try:
        return _catalog()[cid]
    except KeyError:
        raise UnknownCourse(cid) from None


def course_of_skill(skill: str) -> Course | None:
    for c in all_courses():
        if skill in c.skills:
            return c
    return None
