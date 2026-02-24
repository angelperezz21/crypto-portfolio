"""
Router: /api/v1/transactions
GET /           → historial paginado con filtros
GET /export     → descarga CSV del historial filtrado
"""

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_account, get_db
from core.responses import ok
from models.account import Account
from models.transaction import Transaction, TRANSACTION_TYPES

router = APIRouter()


def _apply_filters(query, account_id, tx_type, asset, from_date, to_date):
    """Aplica filtros comunes a la query de transactions."""
    query = query.where(Transaction.account_id == account_id)
    if tx_type:
        query = query.where(Transaction.type == tx_type)
    if asset:
        query = query.where(Transaction.base_asset == asset.upper())
    if from_date:
        query = query.where(Transaction.executed_at >= from_date)
    if to_date:
        query = query.where(Transaction.executed_at <= to_date)
    return query


@router.get("")
async def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    type: str | None = Query(None, description=f"Filtro por tipo: {TRANSACTION_TYPES}"),
    asset: str | None = Query(None, description="Filtro por activo, e.g. BTC"),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> dict:
    """
    Historial paginado de transacciones con filtros opcionales.
    meta incluye: page, limit, total, pages.
    """
    offset = (page - 1) * limit

    # Total sin paginar
    count_q = _apply_filters(
        select(func.count()).select_from(Transaction),
        account.id, type, asset, from_date, to_date,
    )
    total: int = (await db.execute(count_q)).scalar_one()

    # Datos paginados
    data_q = _apply_filters(
        select(Transaction),
        account.id, type, asset, from_date, to_date,
    ).order_by(Transaction.executed_at.desc()).offset(offset).limit(limit)

    rows = (await db.execute(data_q)).scalars().all()

    return ok(
        data=[_tx_to_dict(tx) for tx in rows],
        meta={
            "page": page,
            "limit": limit,
            "total": total,
            "pages": max(1, -(-total // limit)),  # ceil division
        },
    )


@router.get("/export")
async def export_transactions(
    type: str | None = Query(None),
    asset: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> StreamingResponse:
    """
    Exporta transacciones filtradas como CSV.
    El payload raw de Binance (raw_data) se excluye del CSV.
    """
    data_q = _apply_filters(
        select(Transaction),
        account.id, type, asset, from_date, to_date,
    ).order_by(Transaction.executed_at.desc())

    rows = (await db.execute(data_q)).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "binance_id", "type", "base_asset", "quote_asset",
        "quantity", "price", "total_value_usd",
        "fee_asset", "fee_amount", "executed_at",
    ])
    for tx in rows:
        writer.writerow([
            str(tx.id), tx.binance_id, tx.type,
            tx.base_asset, tx.quote_asset,
            str(tx.quantity), str(tx.price) if tx.price else "",
            str(tx.total_value_usd) if tx.total_value_usd else "",
            tx.fee_asset, str(tx.fee_amount) if tx.fee_amount else "",
            tx.executed_at.isoformat(),
        ])

    output.seek(0)
    filename = f"transactions_{date.today()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _tx_to_dict(tx: Transaction) -> dict:
    return {
        "id": str(tx.id),
        "binance_id": tx.binance_id,
        "type": tx.type,
        "base_asset": tx.base_asset,
        "quote_asset": tx.quote_asset,
        "quantity": str(tx.quantity),
        "price": str(tx.price) if tx.price else None,
        "total_value_usd": str(tx.total_value_usd) if tx.total_value_usd else None,
        "fee_asset": tx.fee_asset,
        "fee_amount": str(tx.fee_amount) if tx.fee_amount else None,
        "executed_at": tx.executed_at.isoformat(),
    }
