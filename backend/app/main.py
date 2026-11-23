"""API de ThinkLoop (FastAPI).

Correr en desarrollo:
    cd backend && .venv/bin/uvicorn app.main:app --reload
Documentación interactiva: http://localhost:8000/docs

Autenticación: el alumno entra con usuario + contraseña (sin correo) y recibe un
token que se manda en `Authorization: Bearer <token>`. Todas las rutas del alumno
(/api/me, /api/courses, /api/sessions) lo exigen y solo dejan ver lo propio.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import achievements, auth, db, teacher, tutor
from .ai import get_provider
from .courses import UnknownCourse, all_courses, get_course
from .lesson import TUTOR_STYLES


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="ThinkLoop API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("THINKLOOP_CORS", "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

DEMO_MODE = os.environ.get("THINKLOOP_DEMO", "1") == "1"
# PIN del panel docente. En la demo es "1234"; en producción se reemplaza por cuentas reales.
TEACHER_PIN = os.environ.get("THINKLOOP_TEACHER_PIN", "1234")


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except tutor.TutorError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------- modelos ----------------
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=1, max_length=64)
    tutor_style: str = "paciente"
    group_code: Optional[str] = Field(default=None, max_length=20)


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=64)


class ResetIn(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    recovery_code: str = Field(min_length=4, max_length=30)
    new_password: str = Field(min_length=1, max_length=64)


class StyleChange(BaseModel):
    tutor_style: str


class AnswerIn(BaseModel):
    answer: str = Field(default="", max_length=40)
    dont_know: bool = False


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class CheckIn(BaseModel):
    option: str = Field(min_length=1, max_length=30)


class PredictIn(BaseModel):
    choice: str = Field(min_length=1, max_length=10)


class StepIn(BaseModel):
    values: list[str] = Field(min_length=1, max_length=4)


class TheoryIn(BaseModel):
    option: str = Field(min_length=1, max_length=30)


class StartIn(BaseModel):
    days_away: Optional[float] = None  # solo demo: simula un regreso tras N días


# ---------------- autenticación ----------------
def current_student(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Inicia sesión para continuar.")
    s = db.student_by_token(auth.hash_token(authorization[7:].strip()))
    if not s:
        raise HTTPException(401, "Tu sesión expiró. Vuelve a entrar.")
    return s


def _login_response(student: dict, recovery_code: Optional[str] = None) -> dict:
    token, token_hash = auth.new_token()
    db.create_token(student["id"], token_hash, auth.TOKEN_DAYS)
    out = {"token": token, "student": db.public_student(student)}
    if recovery_code:
        out["recovery_code"] = recovery_code  # se muestra una sola vez
    return out


@app.post("/api/auth/register")
def register(body: RegisterIn):
    try:
        username = auth.validate_new_credentials(body.username, body.password)
    except auth.AuthError as e:
        raise HTTPException(400, str(e))
    if body.tutor_style not in TUTOR_STYLES:
        raise HTTPException(400, "estilo de tutor desconocido")
    if db.get_student_by_username(username):
        raise HTTPException(409, "Ese usuario ya existe. Elige otro apodo.")
    code = auth.new_recovery_code()
    s = db.create_student(body.username.strip(), body.tutor_style, teacher.normalize_group(body.group_code),
                          username=username, password_hash=auth.hash_password(body.password),
                          recovery_hash=auth.hash_recovery(code))
    return _login_response(s, code)


@app.post("/api/auth/login")
def login(body: LoginIn):
    username = auth.normalize_username(body.username)
    try:
        auth.throttle.check(username)
    except auth.AuthError as e:
        raise HTTPException(429, str(e))
    s = db.get_student_by_username(username)
    if not s or not auth.verify_password(body.password, s.get("password_hash")):
        auth.throttle.fail(username)
        raise HTTPException(401, "Usuario o contraseña incorrectos.")
    auth.throttle.reset(username)
    return _login_response(s)


@app.post("/api/auth/reset")
def reset_password(body: ResetIn):
    """Recuperar el acceso con el código que se mostró al registrarse (no hay correo)."""
    username = auth.normalize_username(body.username)
    key = f"reset:{username}"
    try:
        auth.throttle.check(key)
        auth.validate_password(body.new_password, username)
    except auth.AuthError as e:
        raise HTTPException(429 if "intentos" in str(e) else 400, str(e))
    s = db.get_student_by_username(username)
    if not s or not s.get("recovery_hash") or auth.hash_recovery(body.recovery_code) != s["recovery_hash"]:
        auth.throttle.fail(key)
        raise HTTPException(401, "Usuario o código de recuperación incorrectos.")
    auth.throttle.reset(key)
    code = auth.new_recovery_code()  # el código usado deja de servir
    db.set_credentials(s["id"], auth.hash_password(body.new_password), auth.hash_recovery(code))
    db.delete_tokens_of(s["id"])
    return _login_response(s, code)


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    if authorization and authorization.lower().startswith("bearer "):
        db.delete_token(auth.hash_token(authorization[7:].strip()))
    return {"ok": True}


# ---------------- general ----------------
@app.get("/api/health")
def health():
    p = get_provider()
    return {"ok": True, "ai_provider": p.name, "demo_mode": DEMO_MODE}


@app.get("/api/tutor-styles")
def tutor_styles():
    return [{"id": k, "label": v["label"]} for k, v in TUTOR_STYLES.items()]


# ---------------- el alumno ----------------
@app.get("/api/me")
def me(student: dict = Depends(current_student)):
    return db.public_student(student)


@app.patch("/api/me")
def change_style(body: StyleChange, student: dict = Depends(current_student)):
    if body.tutor_style not in TUTOR_STYLES:
        raise HTTPException(400, "estilo de tutor desconocido")
    db.update_student_style(student["id"], body.tutor_style)
    return db.public_student(db.get_student(student["id"]))


@app.delete("/api/me")
def delete_me(student: dict = Depends(current_student)):
    """El alumno puede borrar todos sus datos (incluida su cuenta)."""
    db.delete_student(student["id"])
    return {"deleted": True}


@app.get("/api/me/progress")
def my_progress(student: dict = Depends(current_student)):
    return [tutor.progress_for(student["id"], c) for c in all_courses()]


@app.get("/api/me/achievements")
def my_achievements(student: dict = Depends(current_student)):
    return achievements.achievements_for(student["id"])


@app.get("/api/me/certificates")
def my_certificates(student: dict = Depends(current_student)):
    return achievements.certificates_for(student)


# ---------------- cursos ----------------
@app.get("/api/courses")
def courses(student: dict = Depends(current_student)):
    sessions = db.course_sessions(student["id"])
    out = []
    for c in all_courses():
        prog = tutor.progress_for(student["id"], c)
        sess = sessions.get(c.id)
        status = "completado" if prog["completed"] else ("en_curso" if sess or any(
            s["attempts"] for s in prog["skills"]) else "nuevo")
        out.append({**c.summary(), "progress": prog["pct"], "status": status,
                    "last_activity": sess["updated_at"] if sess else None})
    return out


@app.get("/api/courses/{course_id}")
def course_detail(course_id: str, student: dict = Depends(current_student)):
    try:
        c = get_course(course_id)
    except UnknownCourse:
        raise HTTPException(404, "curso no encontrado")
    return {**c.summary(), "progress": tutor.progress_for(student["id"], c), "theory": c.theory()}


@app.post("/api/courses/{course_id}/session")
def start_session(course_id: str, body: StartIn | None = None, student: dict = Depends(current_student)):
    days_away = body.days_away if (body and DEMO_MODE) else None
    return _run(tutor.start_or_resume, student["id"], course_id, days_away)


# ---------------- sesión de estudio (solo la propia) ----------------
@app.get("/api/sessions/{session_id}")
def get_session(session_id: int, student: dict = Depends(current_student)):
    return _run(tutor.get_view, session_id, student_id=student["id"])


@app.post("/api/sessions/{session_id}/theory")
def theory(session_id: int, body: TheoryIn, student: dict = Depends(current_student)):
    """Pregunta al final de la teoría del curso (fundamentos)."""
    return _run(tutor.check_theory, session_id, body.option, student_id=student["id"])


@app.post("/api/sessions/{session_id}/check")
def check(session_id: int, body: CheckIn, student: dict = Depends(current_student)):
    """Pregunta de comprobación al final de la explicación (reemplaza a «Entendido»)."""
    return _run(tutor.check_explanation, session_id, body.option, student_id=student["id"])


@app.post("/api/sessions/{session_id}/exam")
def exam_option(session_id: int, body: CheckIn, student: dict = Depends(current_student)):
    """Pregunta de «por qué» de la evaluación final."""
    return _run(tutor.exam_option, session_id, body.option, student_id=student["id"])


@app.post("/api/sessions/{session_id}/predict")
def predict(session_id: int, body: PredictIn, student: dict = Depends(current_student)):
    """Estimación antes de calcular: «mayor» o «menor»."""
    return _run(tutor.predict, session_id, body.choice, student_id=student["id"])


@app.post("/api/sessions/{session_id}/step")
def step(session_id: int, body: StepIn, student: dict = Depends(current_student)):
    """Respuesta al mini paso de la pista actual."""
    return _run(tutor.step_answer, session_id, [v[:20] for v in body.values], student_id=student["id"])


@app.post("/api/sessions/{session_id}/answer")
def answer(session_id: int, body: AnswerIn, student: dict = Depends(current_student)):
    if not body.dont_know and not body.answer.strip():
        raise HTTPException(400, "respuesta vacía")
    return _run(tutor.answer, session_id, body.answer, body.dont_know, student_id=student["id"])


@app.post("/api/sessions/{session_id}/hint")
def hint(session_id: int, student: dict = Depends(current_student)):
    return _run(tutor.hint, session_id, student_id=student["id"])


@app.post("/api/sessions/{session_id}/example")
def example(session_id: int, student: dict = Depends(current_student)):
    """Ayuda extra: ejemplo parecido resuelto con otros números."""
    return _run(tutor.example, session_id, student_id=student["id"])


@app.post("/api/sessions/{session_id}/skip")
def skip(session_id: int, student: dict = Depends(current_student)):
    """Ayuda extra: cambiar de ejercicio sin penalización."""
    return _run(tutor.skip, session_id, student_id=student["id"])


@app.post("/api/sessions/{session_id}/message")
def message(session_id: int, body: MessageIn, student: dict = Depends(current_student)):
    return _run(tutor.free_message, session_id, body.text, student_id=student["id"])


@app.post("/api/sessions/{session_id}/pause")
def pause(session_id: int, student: dict = Depends(current_student)):
    return _run(tutor.pause, session_id, student_id=student["id"])


@app.get("/api/metrics/usage")
def usage():
    """Costos: llamadas a la IA y tokens, para medir costo por sesión."""
    return db.usage_summary()


# ---------------- panel docente ----------------
def _check_pin(pin: Optional[str]) -> None:
    if not pin or pin != TEACHER_PIN:
        raise HTTPException(401, "PIN docente incorrecto")


@app.get("/api/teacher/groups")
def teacher_groups(x_teacher_pin: Optional[str] = Header(default=None)):
    _check_pin(x_teacher_pin)
    return db.list_groups()


@app.get("/api/teacher/courses")
def teacher_courses(x_teacher_pin: Optional[str] = Header(default=None)):
    _check_pin(x_teacher_pin)
    return [{"id": c.id, "title": c.title} for c in all_courses()]


@app.get("/api/teacher/groups/{group_code}")
def teacher_summary(group_code: str, course: str = teacher.DEMO_COURSE,
                    x_teacher_pin: Optional[str] = Header(default=None)):
    """Reporte de un minuto: errores agrupados, dominio por habilidad y alumnos a acompañar."""
    _check_pin(x_teacher_pin)
    code = teacher.normalize_group(group_code)
    if not code:
        raise HTTPException(400, "código de grupo inválido")
    try:
        return teacher.group_summary(code, course)
    except UnknownCourse:
        raise HTTPException(404, "curso no encontrado")


@app.post("/api/teacher/demo-group")
def teacher_demo_group(x_teacher_pin: Optional[str] = Header(default=None)):
    """Solo demo: crea un grupo de 20 alumnos SIMULADOS para mostrar el panel."""
    _check_pin(x_teacher_pin)
    if not DEMO_MODE:
        raise HTTPException(403, "solo disponible en modo demo")
    return teacher.group_summary(teacher.seed_demo_group())
