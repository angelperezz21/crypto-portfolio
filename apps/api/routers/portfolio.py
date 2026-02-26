"""
Router: /api/v1/portfolio
GET /assets  → balances actuales con métricas FIFO
GET /history → serie temporal de portfolio_snapshots
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_account, get_db
from core.responses import ok
from models.account import Account
from models.balance_snapshot import BalanceSnapshot
from models.portfolio_snapshot import PortfolioSnapshot
from models.price_history import PriceHistory
from services.portfolio_service import PortfolioService

router = APIRouter()


async def _get_prices(db: AsyncSession, account_id) -> dict[str, Decimal]:
    """
    Aproxima precios actuales leyendo el cierre más reciente de price_history.
    prices["BTC"] = USD/BTC
    prices["EUR"] = USD/EUR (tipo de cambio, i.e. EURUSDT close)
    Si un activo no tiene datos históricos, su precio se omite (quedará como 0).
    """
    subq = (
        select(
            PriceHistory.symbol,
            func.max(PriceHistory.open_at).label("last_at"),
        )
        .where(PriceHistory.interval == "1d")
        .group_by(PriceHistory.symbol)
        .subquery()
    )
    q = select(PriceHistory.symbol, PriceHistory.close).join(
        subq,
        (PriceHistory.symbol == subq.c.symbol) & (PriceHistory.open_at == subq.c.last_at),
    )
    rows = (await db.execute(q)).fetchall()

    prices: dict[str, Decimal] = {}
    for row in rows:
        # BTCUSDT → BTC, EURUSDT → EUR, etc.
        sym: str = row.symbol
        for quote in ("USDT", "BUSD", "USD", "EUR"):
            if sym.endswith(quote):
                asset = sym[: -len(quote)]
                prices[asset] = Decimal(str(row.close))
                break

    # Stablecoins y fiat siempre valen 1 USD
    for stable in ("USDT", "USDC", "BUSD", "FDUSD", "DAI", "TUSD"):
        prices.setdefault(stable, Decimal("1"))
    # EUR fallback si no hay datos
    prices.setdefault("EUR", Decimal("1.08"))

    return prices


def _to_eur(usd_value: Decimal, eur_usd: Decimal) -> Decimal:
    """Convierte un valor USD a EUR usando el tipo de cambio actual."""
    if eur_usd <= Decimal("0"):
        return Decimal("0")
    return (usd_value / eur_usd).quantize(Decimal("0.00000001"), rounding="ROUND_HALF_UP")


@router.get("/assets")
async def get_assets(
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> dict:
    """
    Lista de activos en cartera con métricas por activo:
    balance, valor USD, precio medio de compra (FIFO), P&L.
    """
    prices = await _get_prices(db, account.id)
    eur_usd = prices.get("EUR", Decimal("1.08"))
    service = PortfolioService(db=db, account_id=account.id)
    metrics = await service.calculate_asset_metrics(current_prices=prices)

    return ok(
        data=[
            {
                "asset": m.asset,
                "quantity": str(m.quantity),
                "value_usd": str(m.value_usd),
                "value_eur": str(_to_eur(m.value_usd, eur_usd)),
                "portfolio_pct": str(m.portfolio_pct),
                "avg_buy_price_usd": str(m.avg_buy_price_usd),
                "avg_buy_price_eur": str(m.avg_buy_price_eur),
                "cost_basis_usd": str(m.cost_basis_usd),
                "cost_basis_eur": str(m.cost_basis_eur),
                "pnl_usd": str(m.pnl_usd),
                "pnl_eur": str(_to_eur(m.pnl_usd, eur_usd)),
                "pnl_pct": str(m.pnl_pct),
                "realized_pnl_usd": str(m.realized_pnl_usd),
                "realized_pnl_eur": str(_to_eur(m.realized_pnl_usd, eur_usd)),
            }
            for m in metrics
        ],
        meta={
            "prices_source": "price_history",
            "assets_count": len(metrics),
            "eur_usd_rate": str(eur_usd),
        },
    )


@router.get("/liquid")
async def get_liquid_balance(
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> dict:
    """
    Saldo líquido actual: stablecoins + fiat (EUR, USD) en la cuenta.
    Valor en USD: stablecoins a 1:1, EUR convertido vía precio EURUSDT más reciente.
    """
    LIQUID_ASSETS = frozenset({"USDT", "USDC", "BUSD", "FDUSD", "DAI", "EUR", "USD"})
    STABLECOINS   = frozenset({"USDT", "USDC", "BUSD", "FDUSD", "DAI"})

    # Precio EUR/USD desde price_history (si existe), sino fallback 1.08
    eur_usd = Decimal("1.08")
    subq = (
        select(func.max(PriceHistory.open_at).label("last_at"))
        .where(PriceHistory.symbol == "EURUSDT", PriceHistory.interval == "1d")
        .subquery()
    )
    row = (
        await db.execute(
            select(PriceHistory.close)
            .join(subq, PriceHistory.open_at == subq.c.last_at)
            .where(PriceHistory.symbol == "EURUSDT")
        )
    ).first()
    if row:
        eur_usd = Decimal(str(row.close))

    # Último snapshot por activo líquido
    latest_ts_subq = (
        select(
            BalanceSnapshot.asset,
            func.max(BalanceSnapshot.snapshot_at).label("max_ts"),
        )
        .where(
            BalanceSnapshot.account_id == account.id,
            BalanceSnapshot.asset.in_(LIQUID_ASSETS),
        )
        .group_by(BalanceSnapshot.asset)
        .subquery()
    )
    q = (
        select(BalanceSnapshot)
        .join(
            latest_ts_subq,
            (BalanceSnapshot.asset == latest_ts_subq.c.asset)
            & (BalanceSnapshot.snapshot_at == latest_ts_subq.c.max_ts),
        )
        .where(BalanceSnapshot.account_id == account.id)
    )
    snapshots = list((await db.execute(q)).scalars().all())

    items = []
    total_usd = Decimal("0")

    for snap in snapshots:
        qty = snap.free + snap.locked
        if qty <= Decimal("0"):
            continue
        if snap.asset in STABLECOINS:
            value_usd = qty
        elif snap.asset in ("EUR", "USD"):
            value_usd = qty * eur_usd if snap.asset == "EUR" else qty
        else:
            value_usd = Decimal("0")
        total_usd += value_usd
        value_eur = (value_usd / eur_usd).quantize(Decimal("0.01"))
        items.append({
            "asset":     snap.asset,
            "quantity":  str(qty),
            "value_usd": str(value_usd.quantize(Decimal("0.01"))),
            "value_eur": str(value_eur),
        })

    # Ordenar por valor descendente
    items.sort(key=lambda x: Decimal(x["value_usd"]), reverse=True)

    total_eur = (total_usd / eur_usd).quantize(Decimal("0.01"))

    return ok(
        data={
            "total_liquid_usd": str(total_usd.quantize(Decimal("0.01"))),
            "total_liquid_eur": str(total_eur),
            "items": items,
        }
    )


@router.get("/history")
async def get_history(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> dict:
    """
    Serie temporal diaria de portfolio_snapshots.
    Si from_date / to_date no se especifican, retorna todo el histórico.
    """
    service = PortfolioService(db=db, account_id=account.id)
    points = await service.calculate_performance_history(
        from_date=from_date or date(2000, 1, 1),
        to_date=to_date or date.today(),
    )

    return ok(
        data=[
            {
                "date": p.snapshot_date.isoformat(),
                "total_value_usd": str(p.total_value_usd),
                "invested_usd": str(p.invested_usd),
                "pnl_usd": str(p.pnl_usd),
                "pnl_pct": str(p.pnl_pct),
            }
            for p in points
        ],
        meta={
            "from_date": (from_date or date(2000, 1, 1)).isoformat(),
            "to_date": (to_date or date.today()).isoformat(),
            "points": len(points),
        },
    )
