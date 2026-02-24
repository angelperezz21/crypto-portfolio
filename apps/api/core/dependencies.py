"""
Dependencias inyectables de FastAPI.
Uso: añadir como parámetro en la firma del endpoint con Depends().
"""

from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import AsyncSessionLocal
from core.security import verify_token
from models.account import Account

_bearer = HTTPBearer()


# ---------------------------------------------------------------------------
# Sesión de base de datos
# ---------------------------------------------------------------------------


async def get_db() -> AsyncIterator[AsyncSession]:
    """Proporciona una sesión SQLAlchemy async con commit/rollback automático."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Autenticación JWT
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    """
    Valida el Bearer token JWT.
    Lanza 401 si el token es inválido o expirado.
    """
    try:
        return verify_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ---------------------------------------------------------------------------
# Cuenta activa (sistema mono-usuario)
# ---------------------------------------------------------------------------


async def get_account(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> Account:
    """
    Devuelve la única cuenta configurada en el sistema.
    Lanza 404 si todavía no se han configurado las API Keys (POST /settings).
    """
    result = await db.execute(select(Account).limit(1))
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay cuenta configurada. Usa POST /api/v1/settings para añadir tus API Keys.",
        )
    return account
