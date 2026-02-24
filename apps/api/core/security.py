"""
Capa de seguridad:
- JWT HS256 para autenticación de sesión web
- AES-256-GCM para cifrar las API Keys de Binance en reposo (RNF-05)
- secrets.compare_digest para verificar la contraseña de la app (timing-safe)

NUNCA loguear ni exponer: SECRET_KEY, ENCRYPTION_KEY, APP_PASSWORD,
api_key_encrypted, api_secret_encrypted, ni sus valores descifrados.
"""

import base64
import os
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt

from core.config import settings

ALGORITHM = "HS256"
_SUBJECT = "portfolio_owner"   # sistema mono-usuario
_NONCE_BYTES = 12              # 96 bits — estándar GCM


# ---------------------------------------------------------------------------
# Contraseña de la aplicación web
# ---------------------------------------------------------------------------


def verify_app_password(plain: str) -> bool:
    """
    Compara la contraseña enviada por el usuario contra APP_PASSWORD.
    Usa compare_digest para evitar timing attacks.
    """
    return secrets.compare_digest(plain.encode("utf-8"), settings.APP_PASSWORD.encode("utf-8"))


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


def create_access_token() -> str:
    """Genera un JWT con expiración configurada en ACCESS_TOKEN_EXPIRE_MINUTES."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": _SUBJECT, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> str:
    """
    Valida el JWT y retorna el subject.
    Lanza ValueError si el token es inválido o expirado.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError(f"Token inválido: {exc}") from exc

    sub = payload.get("sub")
    if sub != _SUBJECT:
        raise ValueError("Token con subject inválido")
    return sub


# ---------------------------------------------------------------------------
# AES-256-GCM — cifrado de API Keys de Binance
# ---------------------------------------------------------------------------


def _get_aes_key() -> bytes:
    """Decodifica ENCRYPTION_KEY (base64url → 32 bytes). Falla si la longitud es incorrecta."""
    key = base64.urlsafe_b64decode(settings.ENCRYPTION_KEY)
    if len(key) != 32:
        raise ValueError(f"ENCRYPTION_KEY debe ser 32 bytes, tiene {len(key)}")
    return key


def encrypt_secret(plaintext: str) -> str:
    """
    Cifra un string con AES-256-GCM.
    Formato del resultado: base64url(nonce[12] || ciphertext+tag)
    La librería `cryptography` añade el tag (16 bytes) al final del ciphertext.
    """
    key = _get_aes_key()
    nonce = os.urandom(_NONCE_BYTES)
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext_with_tag).decode("utf-8")


def decrypt_secret(encrypted: str) -> str:
    """
    Descifra un valor cifrado con encrypt_secret.
    Lanza ValueError si la clave es incorrecta o el dato está corrupto.
    """
    key = _get_aes_key()
    try:
        raw = base64.urlsafe_b64decode(encrypted)
    except Exception as exc:
        raise ValueError("Formato de cifrado inválido") from exc

    if len(raw) < _NONCE_BYTES + 16:  # nonce + tag mínimo
        raise ValueError("Dato cifrado demasiado corto")

    nonce = raw[:_NONCE_BYTES]
    ciphertext_with_tag = raw[_NONCE_BYTES:]
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext_with_tag, None).decode("utf-8")
    except InvalidTag as exc:
        raise ValueError("Descifrado fallido: clave incorrecta o dato corrupto") from exc
