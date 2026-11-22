"""Persistencia con SQLite (stdlib). Se puede migrar a PostgreSQL sin cambiar
las rutas: todo el SQL está aquí.

Memoria estructurada: en vez de guardar/enviar el historial completo del chat,
guardamos hechos compactos (dominio por habilidad, errores frecuentes, pistas,
punto de reanudación). Eso es lo que se le pasa a la IA como contexto.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

DB_PATH = os.environ.get("THINKLOOP_DB", os.path.join(os.path.dirname(__file__), "..", "thinkloop.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    tutor_style TEXT NOT NULL DEFAULT 'paciente',
    group_code  TEXT,                              -- grupo/salón (opcional) para el panel docente
    simulated   INTEGER NOT NULL DEFAULT 0,        -- 1 = alumno de ejemplo para la demo docente
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  INTEGER NOT NULL REFERENCES students(id),
    lesson_id   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active',   -- active | paused | completed
    state_json  TEXT NOT NULL,                    -- punto exacto de reanudación
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    INTEGER NOT NULL REFERENCES sessions(id),
    student_id    INTEGER NOT NULL REFERENCES students(id),
    phase         TEXT NOT NULL,
    skill         TEXT NOT NULL,
    exercise_json TEXT NOT NULL,
    answer_raw    TEXT NOT NULL,
    correct       INTEGER NOT NULL,
    misconception TEXT,
    hints_used    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS skill_mastery (
    student_id     INTEGER NOT NULL REFERENCES students(id),
    skill          TEXT NOT NULL,
    mastery        REAL NOT NULL DEFAULT 0,   -- 0..1
    attempts       INTEGER NOT NULL DEFAULT 0,
    correct        INTEGER NOT NULL DEFAULT 0,
    hints_used     INTEGER NOT NULL DEFAULT 0,
    mastered       INTEGER NOT NULL DEFAULT 0,
    last_practiced TEXT,
    PRIMARY KEY (student_id, skill)
);
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    student_id INTEGER,
    kind       TEXT NOT NULL,     -- frustracion, pausa, regreso, pide_respuesta, ...
    detail     TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_tokens (
    token_hash  TEXT PRIMARY KEY,                 -- solo guardamos el hash del token
    student_id  INTEGER NOT NULL REFERENCES students(id),
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ai_usage (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    INTEGER,
    provider      TEXT NOT NULL,
    model         TEXT NOT NULL,
    input_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)
        # Migración sencilla para bases creadas antes del panel docente
        cols = {r["name"] for r in c.execute("PRAGMA table_info(students)")}
        if "group_code" not in cols:
            c.execute("ALTER TABLE students ADD COLUMN group_code TEXT")
        if "simulated" not in cols:
            c.execute("ALTER TABLE students ADD COLUMN simulated INTEGER NOT NULL DEFAULT 0")
        # Inicio de sesión simple (usuario + contraseña, sin correo)
        for col in ("username", "password_hash", "recovery_hash"):
            if col not in cols:
                c.execute(f"ALTER TABLE students ADD COLUMN {col} TEXT")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_students_username ON students(username)"
                  " WHERE username IS NOT NULL")
        mcols = {r["name"] for r in c.execute("PRAGMA table_info(skill_mastery)")}
        if "mastered_at" not in mcols:
            c.execute("ALTER TABLE skill_mastery ADD COLUMN mastered_at TEXT")
        # Sesiones de antes del catálogo de cursos
        c.execute("UPDATE sessions SET lesson_id='MAT-FRAC' WHERE lesson_id='fracciones-suma-v1'")


# ---------------- students ----------------
PRIVATE_FIELDS = ("password_hash", "recovery_hash")


def create_student(name: str, tutor_style: str, group_code: Optional[str] = None,
                   simulated: bool = False, username: Optional[str] = None,
                   password_hash: Optional[str] = None, recovery_hash: Optional[str] = None) -> dict:
    with connect() as c:
        cur = c.execute("INSERT INTO students(name, tutor_style, group_code, simulated, username,"
                        " password_hash, recovery_hash, created_at) VALUES (?,?,?,?,?,?,?,?)",
                        (name, tutor_style, group_code, int(simulated), username, password_hash,
                         recovery_hash, now()))
        return get_student(cur.lastrowid, c)


def public_student(s: Optional[dict]) -> Optional[dict]:
    """Datos del alumno sin secretos (lo único que sale por la API)."""
    if not s:
        return None
    return {k: v for k, v in s.items() if k not in PRIVATE_FIELDS}


def get_student_by_username(username: str) -> Optional[dict]:
    with connect() as c:
        r = c.execute("SELECT * FROM students WHERE username=?", (username,)).fetchone()
    return dict(r) if r else None


def set_credentials(student_id: int, password_hash: str, recovery_hash: Optional[str] = None) -> None:
    with connect() as c:
        if recovery_hash:
            c.execute("UPDATE students SET password_hash=?, recovery_hash=? WHERE id=?",
                      (password_hash, recovery_hash, student_id))
        else:
            c.execute("UPDATE students SET password_hash=? WHERE id=?", (password_hash, student_id))


# ---------------- tokens de sesión ----------------
def create_token(student_id: int, token_hash: str, days: int) -> None:
    from datetime import timedelta
    t = datetime.now(timezone.utc)
    with connect() as c:
        c.execute("DELETE FROM auth_tokens WHERE expires_at < ?", (t.isoformat(),))
        c.execute("INSERT INTO auth_tokens(token_hash, student_id, created_at, expires_at) VALUES (?,?,?,?)",
                  (token_hash, student_id, t.isoformat(), (t + timedelta(days=days)).isoformat()))


def student_by_token(token_hash: str) -> Optional[dict]:
    with connect() as c:
        r = c.execute("SELECT s.* FROM auth_tokens t JOIN students s ON s.id=t.student_id"
                      " WHERE t.token_hash=? AND t.expires_at > ?", (token_hash, now())).fetchone()
    return dict(r) if r else None


def delete_token(token_hash: str) -> None:
    with connect() as c:
        c.execute("DELETE FROM auth_tokens WHERE token_hash=?", (token_hash,))


def delete_tokens_of(student_id: int) -> None:
    with connect() as c:
        c.execute("DELETE FROM auth_tokens WHERE student_id=?", (student_id,))


def get_student(student_id: int, c: Optional[sqlite3.Connection] = None) -> Optional[dict]:
    def q(conn):
        r = conn.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
        return dict(r) if r else None
    if c is not None:
        return q(c)
    with connect() as conn:
        return q(conn)


def update_student_style(student_id: int, tutor_style: str) -> None:
    with connect() as c:
        c.execute("UPDATE students SET tutor_style=? WHERE id=?", (tutor_style, student_id))


def delete_student(student_id: int) -> None:
    """Gestión de datos por el propio alumno: borra todo lo suyo."""
    with connect() as c:
        sids = [r["id"] for r in c.execute("SELECT id FROM sessions WHERE student_id=?", (student_id,))]
        for sid in sids:
            c.execute("DELETE FROM ai_usage WHERE session_id=?", (sid,))
        c.execute("DELETE FROM events WHERE student_id=?", (student_id,))
        c.execute("DELETE FROM attempts WHERE student_id=?", (student_id,))
        c.execute("DELETE FROM skill_mastery WHERE student_id=?", (student_id,))
        c.execute("DELETE FROM sessions WHERE student_id=?", (student_id,))
        c.execute("DELETE FROM auth_tokens WHERE student_id=?", (student_id,))
        c.execute("DELETE FROM students WHERE id=?", (student_id,))


# ---------------- sessions ----------------
def create_session(student_id: int, lesson_id: str, state: dict) -> int:
    with connect() as c:
        t = now()
        cur = c.execute(
            "INSERT INTO sessions(student_id, lesson_id, status, state_json, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?)", (student_id, lesson_id, "active", json.dumps(state), t, t))
        return cur.lastrowid


def get_session(session_id: int) -> Optional[dict]:
    with connect() as c:
        r = c.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["state"] = json.loads(d.pop("state_json"))
    return d


def save_session(session_id: int, state: dict, status: Optional[str] = None) -> None:
    with connect() as c:
        if status:
            c.execute("UPDATE sessions SET state_json=?, status=?, updated_at=? WHERE id=?",
                      (json.dumps(state), status, now(), session_id))
        else:
            c.execute("UPDATE sessions SET state_json=?, updated_at=? WHERE id=?",
                      (json.dumps(state), now(), session_id))


def latest_open_session(student_id: int, lesson_id: str) -> Optional[dict]:
    with connect() as c:
        r = c.execute("SELECT id FROM sessions WHERE student_id=? AND lesson_id=? AND status!='completed'"
                      " ORDER BY updated_at DESC LIMIT 1", (student_id, lesson_id)).fetchone()
    return get_session(r["id"]) if r else None


def last_activity(student_id: int, lesson_id: Optional[str] = None) -> Optional[str]:
    with connect() as c:
        if lesson_id:
            r = c.execute("SELECT MAX(updated_at) AS t FROM sessions WHERE student_id=? AND lesson_id=?",
                          (student_id, lesson_id)).fetchone()
        else:
            r = c.execute("SELECT MAX(updated_at) AS t FROM sessions WHERE student_id=?",
                          (student_id,)).fetchone()
    return r["t"] if r else None


def course_sessions(student_id: int) -> dict[str, dict]:
    """Última sesión de cada curso: {lesson_id: {"status", "phase", "updated_at"}}."""
    with connect() as c:
        rows = c.execute("SELECT lesson_id, status, state_json, updated_at FROM sessions WHERE student_id=?"
                         " ORDER BY updated_at", (student_id,)).fetchall()
    out = {}
    for r in rows:
        out[r["lesson_id"]] = {"status": r["status"], "phase": json.loads(r["state_json"]).get("phase"),
                               "updated_at": r["updated_at"]}
    return out


# ---------------- attempts & mastery ----------------
def record_attempt(session_id: int, student_id: int, phase: str, skill: str, exercise: dict,
                   answer_raw: str, correct: bool, misconception: Optional[str], hints_used: int) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO attempts(session_id, student_id, phase, skill, exercise_json, answer_raw,"
            " correct, misconception, hints_used, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (session_id, student_id, phase, skill, json.dumps(exercise), answer_raw,
             int(correct), misconception, hints_used, now()))


def update_mastery(student_id: int, skill: str, correct: bool, hints_used: int,
                   mastered: Optional[bool] = None) -> dict:
    """Estimación sencilla y explicable del dominio (0..1)."""
    with connect() as c:
        r = c.execute("SELECT * FROM skill_mastery WHERE student_id=? AND skill=?",
                      (student_id, skill)).fetchone()
        m = dict(r) if r else {"mastery": 0.0, "attempts": 0, "correct": 0, "hints_used": 0, "mastered": 0}
        if correct:
            delta = 0.25 if hints_used == 0 else (0.15 if hints_used == 1 else 0.05)
        else:
            delta = -0.1
        m["mastery"] = max(0.0, min(1.0, m["mastery"] + delta))
        m["attempts"] += 1
        m["correct"] += int(correct)
        m["hints_used"] += hints_used
        if mastered is not None:
            m["mastered"] = int(mastered or m["mastered"])
        c.execute(
            "INSERT INTO skill_mastery(student_id, skill, mastery, attempts, correct, hints_used, mastered,"
            " last_practiced) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(student_id, skill) DO UPDATE SET"
            " mastery=excluded.mastery, attempts=excluded.attempts, correct=excluded.correct,"
            " hints_used=excluded.hints_used, mastered=excluded.mastered, last_practiced=excluded.last_practiced",
            (student_id, skill, m["mastery"], m["attempts"], m["correct"], m["hints_used"], m["mastered"], now()))
        return m


def mark_mastered(student_id: int, skill: str) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO skill_mastery(student_id, skill, mastery, mastered, last_practiced, mastered_at)"
            " VALUES (?,?,?,?,?,?) ON CONFLICT(student_id, skill) DO UPDATE SET mastered=1,"
            " mastery=MAX(mastery, 0.8), mastered_at=COALESCE(mastered_at, excluded.mastered_at)",
            (student_id, skill, 0.8, 1, now(), now()))


def unmark_mastered(student_id: int, skill: str) -> None:
    with connect() as c:
        c.execute("UPDATE skill_mastery SET mastered=0 WHERE student_id=? AND skill=?", (student_id, skill))


def get_mastery(student_id: int) -> dict[str, dict]:
    with connect() as c:
        rows = c.execute("SELECT * FROM skill_mastery WHERE student_id=?", (student_id,)).fetchall()
    return {r["skill"]: dict(r) for r in rows}


def frequent_misconceptions(student_id: int, limit: int = 3) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT misconception, COUNT(*) AS n FROM attempts WHERE student_id=? AND correct=0"
            " AND misconception IS NOT NULL AND misconception NOT IN ('no_interpretable','desconocido')"
            " GROUP BY misconception ORDER BY n DESC LIMIT ?", (student_id, limit)).fetchall()
    return [dict(r) for r in rows]


def overcome_misconceptions(student_id: int) -> list[dict]:
    """Errores que el alumno cometió y después superó (historia positiva):
    [{"misconception", "skill", "since"}], `since` = cuándo lo dejó atrás."""
    with connect() as c:
        rows = c.execute(
            "SELECT a.misconception, a.skill, MAX(a.created_at) AS last_wrong FROM attempts a"
            " WHERE a.student_id=? AND a.correct=0 AND a.misconception IS NOT NULL"
            " AND a.misconception NOT IN ('no_interpretable','desconocido','no_sabe','posible_dedo')"
            " GROUP BY a.misconception, a.skill", (student_id,)).fetchall()
        out = []
        for r in rows:
            later = c.execute(
                "SELECT created_at FROM attempts WHERE student_id=? AND skill=? AND correct=1"
                " AND created_at > ? ORDER BY created_at LIMIT 2",
                (student_id, r["skill"], r["last_wrong"])).fetchall()
            if len(later) >= 2:
                out.append({"misconception": r["misconception"], "skill": r["skill"],
                            "since": later[1]["created_at"]})
    return out


# ---------------- events & usage ----------------
def log_event(kind: str, session_id: Optional[int] = None, student_id: Optional[int] = None,
              detail: Any = None) -> None:
    with connect() as c:
        c.execute("INSERT INTO events(session_id, student_id, kind, detail, created_at) VALUES (?,?,?,?,?)",
                  (session_id, student_id, kind, json.dumps(detail) if detail is not None else None, now()))


def log_ai_usage(session_id: Optional[int], provider: str, model: str, input_tokens: int,
                 output_tokens: int) -> None:
    with connect() as c:
        c.execute("INSERT INTO ai_usage(session_id, provider, model, input_tokens, output_tokens, created_at)"
                  " VALUES (?,?,?,?,?,?)", (session_id, provider, model, input_tokens, output_tokens, now()))


def usage_summary() -> dict:
    with connect() as c:
        r = c.execute("SELECT COUNT(*) AS calls, COALESCE(SUM(input_tokens),0) AS input_tokens,"
                      " COALESCE(SUM(output_tokens),0) AS output_tokens,"
                      " COUNT(DISTINCT session_id) AS sessions FROM ai_usage").fetchone()
        s = c.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()["n"]
    d = dict(r)
    d["total_sessions"] = s
    return d


# ---------------- panel docente (datos agregados por grupo) ----------------
def group_students(group_code: str) -> list[dict]:
    with connect() as c:
        rows = c.execute("SELECT * FROM students WHERE group_code=? ORDER BY name", (group_code,)).fetchall()
    return [dict(r) for r in rows]


def list_groups() -> list[dict]:
    with connect() as c:
        rows = c.execute("SELECT group_code, COUNT(*) AS n, MAX(simulated) AS simulated FROM students"
                         " WHERE group_code IS NOT NULL GROUP BY group_code ORDER BY group_code").fetchall()
    return [dict(r) for r in rows]


def group_misconceptions(group_code: str, skills: Optional[list[str]] = None) -> list[dict]:
    """Por cada error de razonamiento: cuántos alumnos DISTINTOS lo cometieron y cuántas veces.
    `skills` limita el reporte a las habilidades de un curso."""
    skill_sql, params = "", [group_code]
    if skills:
        skill_sql = f" AND a.skill IN ({','.join('?' * len(skills))})"
        params += list(skills)
    with connect() as c:
        rows = c.execute(
            "SELECT a.misconception, COUNT(DISTINCT a.student_id) AS students, COUNT(*) AS times"
            " FROM attempts a JOIN students s ON s.id=a.student_id"
            " WHERE s.group_code=? AND a.correct=0 AND a.misconception IS NOT NULL"
            " AND a.misconception NOT IN ('no_interpretable','desconocido','no_sabe','posible_dedo')"
            + skill_sql + " GROUP BY a.misconception ORDER BY students DESC, times DESC", params).fetchall()
    return [dict(r) for r in rows]


def student_misconceptions(student_id: int, skills: Optional[list[str]] = None) -> list[str]:
    rows = frequent_misconceptions(student_id, limit=20)
    if skills:
        with connect() as c:
            keep = {r["misconception"] for r in c.execute(
                "SELECT DISTINCT misconception FROM attempts WHERE student_id=? AND correct=0 AND skill IN ("
                + ",".join("?" * len(skills)) + ")", (student_id, *skills))}
        rows = [m for m in rows if m["misconception"] in keep]
    return [m["misconception"] for m in rows[:2]]


def has_course_event(student_id: int, kind: str, course_id: str) -> bool:
    with connect() as c:
        return c.execute("SELECT 1 FROM events WHERE student_id=? AND kind=? AND json_extract(detail,'$.course')=?"
                         " LIMIT 1", (student_id, kind, course_id)).fetchone() is not None


def count_events(student_id: int, kind: str) -> int:
    with connect() as c:
        return c.execute("SELECT COUNT(*) AS n FROM events WHERE student_id=? AND kind=?",
                         (student_id, kind)).fetchone()["n"]


def student_activity(student_id: int, lesson_id: Optional[str] = None,
                     skills: Optional[list[str]] = None) -> dict:
    skill_sql = f" AND skill IN ({','.join('?' * len(skills))})" if skills else ""
    with connect() as c:
        r = c.execute("SELECT COUNT(*) AS attempts, COALESCE(SUM(correct),0) AS correct,"
                      " COALESCE(SUM(hints_used),0) AS hints, MAX(created_at) AS last"
                      " FROM attempts WHERE student_id=?" + skill_sql,
                      (student_id, *(skills or []))).fetchone()
        if lesson_id:
            sess = c.execute("SELECT state_json, status FROM sessions WHERE student_id=? AND lesson_id=?"
                             " ORDER BY updated_at DESC LIMIT 1", (student_id, lesson_id)).fetchone()
        else:
            sess = c.execute("SELECT state_json, status FROM sessions WHERE student_id=?"
                             " ORDER BY updated_at DESC LIMIT 1", (student_id,)).fetchone()
    d = dict(r)
    if sess:
        st = json.loads(sess["state_json"])
        d["phase"], d["skill"], d["status"] = st.get("phase"), st.get("skill"), sess["status"]
    else:
        d["phase"] = d["skill"] = d["status"] = None
    return d


def delete_group(group_code: str) -> None:
    for s in group_students(group_code):
        delete_student(s["id"])


# ---------------- logros (hechos de razonamiento, no de cantidad) ----------------
def achievement_facts(student_id: int) -> dict[str, Optional[str]]:
    """Cuándo ocurrió por primera vez cada hecho que da un logro (None = todavía no)."""
    q = {
        # Se animó a responder, aunque no estuviera seguro
        "valiente": "SELECT MIN(created_at) AS t FROM attempts WHERE student_id=?",
        # Se equivocó y corrigió el MISMO ejercicio sin pedir otra pista
        "detective": (
            "SELECT MIN(b.created_at) AS t FROM attempts a JOIN attempts b"
            " ON b.student_id=a.student_id AND b.created_at > a.created_at"
            " AND json_extract(b.exercise_json,'$.id') = json_extract(a.exercise_json,'$.id')"
            " WHERE a.student_id=? AND a.correct=0 AND b.correct=1 AND b.hints_used=a.hints_used"
            " AND a.phase IN ('practica','transferencia','repaso')"
            " AND COALESCE(a.misconception,'') NOT IN ('no_interpretable','no_sabe')"),
        # Estimó bien antes de calcular
        "estimador": ("SELECT MIN(created_at) AS t FROM events WHERE student_id=? AND kind='prediccion'"
                      " AND json_extract(detail,'$.ok')=1"),
        # Resolvió los pasos de las pistas y luego el ejercicio (para ver la 2ª pista hay que resolver un paso)
        "paso_a_paso": ("SELECT MIN(created_at) AS t FROM attempts WHERE student_id=? AND correct=1"
                        " AND hints_used >= 2"),
        # Resolvió un problema nuevo en contexto sin ninguna pista
        "por_tu_cuenta": ("SELECT MIN(created_at) AS t FROM attempts WHERE student_id=? AND correct=1"
                          " AND phase='transferencia' AND hints_used=0"),
        # Usó la ayuda extra y después resolvió en esa sesión
        "pregunta": (
            "SELECT MIN(a.created_at) AS t FROM events e JOIN attempts a ON a.session_id=e.session_id"
            " AND a.created_at > e.created_at AND a.correct=1"
            " WHERE e.student_id=? AND e.kind IN ('ayuda_extra','ejemplo')"),
        # Recordó lo aprendido en un repaso
        "memoria": ("SELECT MIN(created_at) AS t FROM attempts WHERE student_id=? AND correct=1"
                    " AND phase='repaso'"),
        # Tomó un descanso y regresó a seguir
        "descanso": (
            "SELECT MIN(a.created_at) AS t FROM events e JOIN attempts a ON a.student_id=e.student_id"
            " AND a.created_at > e.created_at WHERE e.student_id=? AND e.kind='pausa'"),
    }
    with connect() as c:
        out = {k: c.execute(sql, (student_id,)).fetchone()["t"] for k, sql in q.items()}
    overcome = overcome_misconceptions(student_id)
    out["error_vencido"] = min((o["since"] for o in overcome), default=None)
    return out
