"""Inicio de sesión simple y respetuoso con menores de edad.

- Sin correo ni nombre real: solo un apodo (usuario) y una contraseña.
- Si se olvida la contraseña, se recupera con un código que se muestra UNA vez al
  registrarse (no hay correo al cual mandar nada).
- Contraseñas con scrypt (biblioteca estándar) y sal aleatoria; los tokens de
  sesión se guardan solo como hash.
- Freno a intentos repetidos: 5 fallos en 10 minutos bloquean ese usuario un rato.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import threading
import time
from collections import defaultdict
from typing import Optional

USERNAME_RE = re.compile(r"^[a-z0-9_.-]{3,20}$")
MIN_PASSWORD = 6
MAX_PASSWORD = 64
TOKEN_DAYS = 30
MAX_FAILS = 5
FAIL_WINDOW = 600  # segundos

_RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O ni 1/I para no confundir


class AuthError(ValueError):
    pass


def normalize_username(username: str) -> str:
    return (username or "").strip().lower()


def validate_new_credentials(username: str, password: str) -> str:
    u = normalize_username(username)
    if not USERNAME_RE.match(u):
        raise AuthError("El usuario debe tener de 3 a 20 caracteres: letras, números, punto, guion o guion bajo.")
    validate_password(password, u)
    return u


def validate_password(password: str, username: str = "") -> None:
    if not (MIN_PASSWORD <= len(password or "") <= MAX_PASSWORD):
        raise AuthError(f"La contraseña debe tener entre {MIN_PASSWORD} y {MAX_PASSWORD} caracteres.")
    if username and password.strip().lower() == username:
        raise AuthError("La contraseña no puede ser igual a tu usuario.")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${h.hex()}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    try:
        algo, salt_hex, hash_hex = (stored or "").split("$")
    except ValueError:
        return False
    if algo != "scrypt":
        return False
    h = hashlib.scrypt((password or "").encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=32)
    return hmac.compare_digest(h.hex(), hash_hex)


def new_recovery_code() -> str:
    raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(12))
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def hash_recovery(code: str) -> str:
    norm = re.sub(r"[^A-Z0-9]", "", (code or "").upper())
    return hashlib.sha256(norm.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256((token or "").encode()).hexdigest()


class Throttle:
    """Cuenta intentos fallidos por usuario (en memoria; basta para un solo servidor)."""

    def __init__(self) -> None:
        self._fails: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            recent = [t for t in self._fails[key] if now - t < FAIL_WINDOW]
            self._fails[key] = recent
            if len(recent) >= MAX_FAILS:
                raise AuthError("Demasiados intentos. Espera unos minutos y vuelve a intentarlo.")

    def fail(self, key: str) -> None:
        with self._lock:
            self._fails[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)


throttle = Throttle()
