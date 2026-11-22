"""Inicio de sesión simple: sin correo, contraseñas con hash, recuperación por código
y cada alumno solo ve lo suyo."""
from conftest import PASSWORD, register, start

from app import auth, db


def test_register_login_and_private_fields(client):
    st, _ = register(client, "Leo")
    assert "password_hash" not in st and "recovery_hash" not in st
    me = client.get("/api/me").json()
    assert me["username"] == st["username"] and "password_hash" not in me
    stored = db.get_student_by_username(st["username"])
    assert stored["password_hash"].startswith("scrypt$") and PASSWORD not in stored["password_hash"]

    client.headers.pop("Authorization")
    assert client.get("/api/me").status_code == 401
    r = client.post("/api/auth/login", json={"username": st["username"].upper(), "password": PASSWORD})
    assert r.status_code == 200 and r.json()["token"]
    assert "recovery_code" not in r.json()


def test_register_validation(client):
    st, _ = register(client, "Mia")
    dup = client.post("/api/auth/register", json={"username": st["username"], "password": "otra12345"})
    assert dup.status_code == 409
    bad = client.post("/api/auth/register", json={"username": "a b", "password": "otra12345"})
    assert bad.status_code == 400
    short = client.post("/api/auth/register", json={"username": "nuevo1", "password": "123"})
    assert short.status_code == 400
    same = client.post("/api/auth/register", json={"username": "nuevo2", "password": "nuevo2"})
    assert same.status_code == 400


def test_wrong_password_is_throttled(client):
    st, _ = register(client, "Eva")
    for _ in range(auth.MAX_FAILS):
        assert client.post("/api/auth/login", json={"username": st["username"], "password": "mal"}).status_code == 401
    r = client.post("/api/auth/login", json={"username": st["username"], "password": PASSWORD})
    assert r.status_code == 429
    auth.throttle.reset(st["username"])


def test_recovery_code_resets_password_once(client):
    username = "recupera1"
    r = client.post("/api/auth/register", json={"username": username, "password": PASSWORD}).json()
    code = r["recovery_code"]
    assert len(code) == 14 and code.count("-") == 2
    bad = client.post("/api/auth/reset", json={"username": username, "recovery_code": "AAAA-BBBB-CCCC",
                                               "new_password": "nueva123"})
    assert bad.status_code == 401
    ok = client.post("/api/auth/reset", json={"username": username, "recovery_code": code.lower(),
                                              "new_password": "nueva123"})
    assert ok.status_code == 200 and ok.json()["recovery_code"] != code
    # El token anterior deja de servir y el código usado ya no sirve otra vez
    assert client.get("/api/me", headers={"Authorization": f"Bearer {r['token']}"}).status_code == 401
    again = client.post("/api/auth/reset", json={"username": username, "recovery_code": code,
                                                 "new_password": "otra1234"})
    assert again.status_code == 401
    assert client.post("/api/auth/login", json={"username": username, "password": "nueva123"}).status_code == 200


def test_students_only_see_their_own_sessions(client):
    register(client, "Uno")
    s = start(client)["session_id"]
    _, h2 = register(client, "Dos")
    assert client.get(f"/api/sessions/{s}", headers=h2).status_code == 400
    assert client.post(f"/api/sessions/{s}/answer", headers=h2, json={"answer": "1"}).status_code == 400
    assert client.get(f"/api/sessions/{s}", headers={}).status_code in (400, 401)


def test_logout_invalidates_token(client):
    _, h = register(client, "Sal")
    assert client.post("/api/auth/logout").json()["ok"]
    assert client.get("/api/me", headers=h).status_code == 401
