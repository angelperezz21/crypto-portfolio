"""
Router: /api/v1/fiscal/{year}
GET → ganancias/pérdidas realizadas en el año fiscal (método FIFO)

Cálculo FIFO correcto para fiscal:
- Se usan TODOS los buys históricos (no solo del año)
- Los sells del año consumen lots por antigüedad
- El P&L realizado del año son las ganancias/pérdidas de esas ventas
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_account, get_db
from core.responses import ok
from models.account import Account
from models.transaction import Transaction
from services.portfolio_service import compute_fifo

router = APIRouter()


@router.get("/{year}")
async def get_fiscal_year(
    year: int,
    method: str = Query("fifo", description="Método: fifo (LIFO próximamente)"),
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> dict:
    """
    P&L realizado para el año fiscal indicado, método FIFO.
    Agrupa por activo y muestra el desglose de ventas.
    """
    year_start = datetime(year, 1, 1, tzinfo=timezone.utc)
    year_end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    # Todos los buys históricos (hasta fin del año fiscal)
    all_buys_q = (
        select(Transaction)
        .where(
            Transaction.account_id == account.id,
            Transaction.type.in_(["buy", "deposit"]),
            Transaction.executed_at <= year_end,
        )
        .order_by(Transaction.base_asset, Transaction.executed_at)
    )
    all_buys = (await db.execute(all_buys_q)).scalars().all()

    # Solo las ventas del año fiscal
    year_sells_q = (
        select(Transaction)
        .where(
            Transaction.account_id == account.id,
            Transaction.type.in_(["sell", "withdrawal"]),
            Transaction.executed_at >= year_start,
            Transaction.executed_at <= year_end,
        )
        .order_by(Transaction.base_asset, Transaction.executed_at)
    )
    year_sells = (await db.execute(year_sells_q)).scalars().all()

    # Agrupar por activo
    buys_by_asset: dict[str, list] = {}
    for tx in all_buys:
        buys_by_asset.setdefault(tx.base_asset, []).append(tx)

    sells_by_asset: dict[str, list] = {}
    for tx in year_sells:
        sells_by_asset.setdefault(tx.base_asset, []).append(tx)

    assets_detail = []
    total_pnl = 0
    from decimal import Decimal

    for asset, sells in sells_by_asset.items():
        buys = buys_by_asset.get(asset, [])
        fifo = compute_fifo(buys, sells)
        total_sold = sum((s.quantity for s in sells), Decimal("0"))
        total_proceeds = sum(
            (s.quantity * (s.price or Decimal("0")) for s in sells), Decimal("0")
        )
        assets_detail.append(
            {
                "asset": asset,
                "total_sold": str(total_sold),
                "total_proceeds_usd": str(total_proceeds.quantize(Decimal("0.00000001"))),
                "realized_pnl_usd": str(fifo.realized_pnl),
                "sell_events": len(sells),
            }
        )
        total_pnl += float(fifo.realized_pnl)

    assets_detail.sort(key=lambda x: float(x["realized_pnl_usd"]), reverse=True)

    return ok(
        data={
            "year": year,
            "method": method,
            "total_realized_pnl_usd": str(round(total_pnl, 8)),
            "assets": assets_detail,
        },
        meta={
            "note": "El P&L realizado puede diferir de las obligaciones fiscales reales. Consulta a un asesor fiscal.",
            "buy_lots_used": len(all_buys),
            "sell_events_in_year": len(year_sells),
        },
    )
