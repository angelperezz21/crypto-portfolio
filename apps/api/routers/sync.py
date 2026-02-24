"""
Router: /api/v1/sync
POST /trigger → lanza sincronización inmediata en background
GET  /status  → estado del último sync
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_account, get_current_user, get_db
from core.responses import ok
from core.security import decrypt_secret
from models.account import Account
from sync.sync_service import SyncService

router = APIRouter()

# Registro en memoria del último job de sync (suficiente para mono-usuario en Fase 1)
_last_job: dict = {}


async def _run_sync(account_id: uuid.UUID, api_key: str, api_secret: str) -> None:
    """
    Tarea de fondo: ejecuta la sincronización y actualiza _last_job.
    NOTA: En Fase 1c se reemplazará por el job APScheduler.
    """
    from core.database import AsyncSessionLocal

    _last_job.update(
        {
            "job_id": str(account_id),
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "records": 0,
            "errors": [],
        }
    )
    try:
        async with AsyncSessionLocal() as db:
            result = await db.get(Account, account_id)
            if result is None:
                _last_job["status"] = "error"
                _last_job["errors"] = ["Account not found"]
                return
            service = SyncService(db=db, account=result, api_key=api_key, api_secret=api_secret)
            # Todos los pares BTC relevantes para cubrir el historial completo
            stats = await service.sync_all(
                symbols=["BTCUSDT", "BTCEUR", "BTCBUSD", "BTCFDUSD"]
            )
            _last_job.update(
                {
                    "status": "idle" if not stats.errors else "error",
                    "finished_at": stats.finished_at.isoformat() if stats.finished_at else None,
                    "records": stats.total_records,
                    "errors": stats.errors,
                }
            )
    except Exception as exc:
        _last_job.update({"status": "error", "errors": [str(exc)]})


@router.post("/trigger")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> dict:
    """
    Lanza una sincronización manual inmediata en background.
    Retorna job_id para consultar el estado con GET /status.
    """
    if not account.api_key_encrypted or not account.api_secret_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configura las API Keys de Binance antes de sincronizar (POST /api/v1/settings).",
        )

    if _last_job.get("status") == "running":
        return ok(
            data={"job_id": _last_job.get("job_id"), "status": "already_running"},
            meta={"message": "Ya hay una sincronización en curso"},
        )

    try:
        api_key = decrypt_secret(account.api_key_encrypted)
        api_secret = decrypt_secret(account.api_secret_encrypted)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al descifrar las API Keys: {exc}",
        ) from exc

    job_id = str(uuid.uuid4())
    _last_job["job_id"] = job_id
    background_tasks.add_task(_run_sync, account.id, api_key, api_secret)

    return ok(
        data={"job_id": job_id, "status": "triggered"},
        meta={"message": "Sincronización iniciada. Consulta GET /api/v1/sync/status para seguimiento."},
    )


@router.get("/status")
async def get_sync_status(
    account: Account = Depends(get_account),
) -> dict:
    """Estado del último sync: tomado del modelo Account + último job en memoria."""
    return ok(
        data={
            "sync_status": account.sync_status,
            "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
            "last_job": _last_job or None,
        }
    )
