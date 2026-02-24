"""
Router: /api/v1/settings
GET  → configuración actual (NUNCA expone secrets)
POST → guarda API Keys cifradas con AES-256-GCM + crea cuenta si no existe
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_db
from core.responses import ok
from core.security import decrypt_secret, encrypt_secret
from models.account import Account

router = APIRouter()


class SettingsResponse(BaseModel):
    account_id: str
    name: str
    has_api_key: bool         # true si hay key cifrada — NUNCA el valor real
    has_api_secret: bool
    last_sync_at: str | None
    sync_status: str


class SettingsUpdate(BaseModel):
    name: str | None = None
    api_key: str | None = None     # plaintext — se cifra antes de guardar
    api_secret: str | None = None  # plaintext — se cifra antes de guardar

    @field_validator("api_key", "api_secret")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """
    Devuelve la configuración actual.
    NUNCA incluye api_key_encrypted ni api_secret_encrypted.
    """
    result = await db.execute(select(Account).limit(1))
    account = result.scalar_one_or_none()

    if account is None:
        return ok(
            data=None,
            meta={"message": "No hay cuenta configurada. Usa POST /api/v1/settings."},
        )

    return ok(
        data=SettingsResponse(
            account_id=str(account.id),
            name=account.name,
            has_api_key=account.api_key_encrypted is not None,
            has_api_secret=account.api_secret_encrypted is not None,
            last_sync_at=account.last_sync_at.isoformat() if account.last_sync_at else None,
            sync_status=account.sync_status,
        ).model_dump(),
    )


@router.post("")
async def save_settings(
    body: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """
    Crea o actualiza la configuración de la cuenta.
    Las API Keys se cifran con AES-256-GCM antes de persistir.
    """
    result = await db.execute(select(Account).limit(1))
    account = result.scalar_one_or_none()

    if account is None:
        # Primera configuración: crear la cuenta
        account = Account(
            id=uuid.uuid4(),
            name=body.name or "Cuenta Principal",
        )
        db.add(account)

    if body.name is not None:
        account.name = body.name

    if body.api_key is not None:
        if len(body.api_key) < 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="api_key demasiado corta",
            )
        account.api_key_encrypted = encrypt_secret(body.api_key)

    if body.api_secret is not None:
        if len(body.api_secret) < 10:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="api_secret demasiado corto",
            )
        account.api_secret_encrypted = encrypt_secret(body.api_secret)

    await db.commit()
    await db.refresh(account)

    return ok(
        data=SettingsResponse(
            account_id=str(account.id),
            name=account.name,
            has_api_key=account.api_key_encrypted is not None,
            has_api_secret=account.api_secret_encrypted is not None,
            last_sync_at=account.last_sync_at.isoformat() if account.last_sync_at else None,
            sync_status=account.sync_status,
        ).model_dump(),
        meta={"message": "Configuración guardada correctamente"},
    )
