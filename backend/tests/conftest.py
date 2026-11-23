"""Configuración compartida de las pruebas: base de datos temporal, IA mock y
ayudantes para registrar alumnos (inicio de sesión con usuario + contraseña)."""
import itertools
import os
import tempfile

os.environ["THINKLOOP_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["THINKLOOP_AI_PROVIDER"] = "mock"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.courses import get_course  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "secreta123"
_n = itertools.count()


@pytest.fixture()
def client():
    db.init_db()
    with TestClient(app) as c:
        yield c


def register(client, name=None, group=None, style="paciente"):
    """Registra un alumno y deja su token en el cliente. Devuelve (alumno, encabezados)."""
    username = f"{(name or 'alumno').lower()}{next(_n)}"
    r = client.post("/api/auth/register", json={"username": username, "password": PASSWORD,
                                                "tutor_style": style, "group_code": group})
    assert r.status_code == 200, r.text
    data = r.json()
    headers = {"Authorization": f"Bearer {data['token']}"}
    client.headers.update(headers)
    return data["student"], headers


def start(client, course="MAT-FRAC", theory=True, **body):
    """Inicia o reanuda un curso. Si toca la teoría (fundamentos), la responde bien,
    salvo que se pida `theory=False` para probarla."""
    r = client.post(f"/api/courses/{course}/session", json=body)
    assert r.status_code == 200, r.text
    v = r.json()
    if theory and v["phase"] == "fundamentos":
        ok = get_course(course).theory(with_answer=True)["question"]["correct"]
        v = client.post(f"/api/sessions/{v['session_id']}/theory", json={"option": ok}).json()
    return v


def state_of(session):
    return db.get_session(session)["state"]


def current(session):
    st = state_of(session)
    c = get_course(st["course"])
    return c, c.load(st["current"])


def correct_answer(view) -> str:
    c, ex = current(view["session_id"])
    if c.id == "MAT-FRAC":
        if ex.skill == "equivalencia" and not ex.story:
            return str(ex.a * ex.target_den // ex.b)
        return f"{ex.answer.numerator}/{ex.answer.denominator}"
    return c.answer_text(ex)


def pass_check(client, session):
    """Responde bien la pregunta de comprobación de la explicación actual."""
    st = state_of(session)
    q = get_course(st["course"]).check_question(st["skill"])
    return client.post(f"/api/sessions/{session}/check", json={"option": q["correct"]}).json()


def predict_if_needed(client, session, v):
    if v.get("prediction"):
        pred = state_of(session)["prediction"]
        v = client.post(f"/api/sessions/{session}/predict", json={"choice": pred["correct"]}).json()
    return v


def solve_step(client, session):
    """Responde correctamente el paso pendiente (sirve para avanzar en las pistas)."""
    data = state_of(session)["step"]["data"]
    vals = [str(f["multiple_of"]) if "multiple_of" in f else
            next((o for o in f.get("options", []) if o.lower() in {a.lower() for a in f["accept"]}),
                 f["accept"][0]) for f in data["fields"]]
    r = client.post(f"/api/sessions/{session}/step", json={"values": vals})
    assert r.status_code == 200, r.text
    return r.json()


def exam_answer(client, session, v, ok=True):
    """Responde la pregunta actual de la evaluación final, bien o mal («No lo sé»)."""
    if v["exam"]["kind"] == "concepto":
        st = state_of(session)
        item = st["exam"]["items"][st["exam"]["i"]]
        q = get_course(st["course"]).exam_questions()[item["q"]]
        opt = q["correct"] if ok else next(k for k in q["options"] if k != q["correct"])
        r = client.post(f"/api/sessions/{session}/exam", json={"option": opt})
    elif ok:
        r = client.post(f"/api/sessions/{session}/answer", json={"answer": correct_answer(v)})
    else:
        r = client.post(f"/api/sessions/{session}/answer", json={"dont_know": True})
    assert r.status_code == 200, r.text
    return r.json()


def take_exam(client, session, v, wrong=()):
    """Presenta toda la evaluación final; `wrong` son los números de pregunta (1…) que falla."""
    assert v["phase"] == "evaluacion", v["phase"]
    while v["phase"] == "evaluacion":
        v = exam_answer(client, session, v, ok=v["exam"]["index"] not in wrong)
    return v
