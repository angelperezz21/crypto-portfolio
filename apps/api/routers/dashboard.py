"""
Router: /api/v1/dashboard
GET /overview        → resumen ejecutivo del portafolio
GET /performance     → evolución temporal con selector de rango
GET /dca/{asset}     → análisis DCA completo para un activo
"""

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_account, get_db
from core.responses import ok
from models.account import Account
from routers.portfolio import _get_prices, _to_eur
from services.portfolio_service import PortfolioService

router = APIRouter()


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> dict:
    """
    Resumen ejecutivo:
    - Valor total, capital invertido, P&L no realizado/realizado, ROI, IRR
    - Top 5 activos por valor
    - Datos de los últimos 30 días de portfolio_snapshots
    """
    prices = await _get_prices(db, account.id)
    eur_usd = prices.get("EUR", Decimal("1.08"))
    service = PortfolioService(db=db, account_id=account.id)
    overview = await service.calculate_overview(current_prices=prices)

    # Serie de 30 días para el gráfico de evolución
    from_date = date.today() - timedelta(days=30)
    history = await service.calculate_performance_history(
        from_date=from_date, to_date=date.today()
    )

    return ok(
        data={
            "total_value_usd": str(overview.total_value_usd),
            "total_value_eur": str(_to_eur(overview.total_value_usd, eur_usd)),
            "invested_usd": str(overview.invested_usd),
            "invested_eur": str(_to_eur(overview.invested_usd, eur_usd)),
            "pnl_unrealized_usd": str(overview.pnl_unrealized_usd),
            "pnl_unrealized_eur": str(_to_eur(overview.pnl_unrealized_usd, eur_usd)),
            "pnl_realized_usd": str(overview.pnl_realized_usd),
            "pnl_realized_eur": str(_to_eur(overview.pnl_realized_usd, eur_usd)),
            "roi_pct": str(overview.roi_pct),
            "irr_annual_pct": str(overview.irr_annual_pct) if overview.irr_annual_pct else None,
            "eur_usd_rate": str(eur_usd),
            "top_assets": [
                {
                    "asset": m.asset,
                    "value_usd": str(m.value_usd),
                    "value_eur": str(_to_eur(m.value_usd, eur_usd)),
                    "portfolio_pct": str(m.portfolio_pct),
                    "pnl_pct": str(m.pnl_pct),
                }
                for m in overview.assets[:5]
                if m.value_usd > Decimal("0")
            ],
            "evolution_30d": [
                {
                    "date": p.snapshot_date.isoformat(),
                    "total_value_usd": str(p.total_value_usd),
                    "total_value_eur": str(_to_eur(p.total_value_usd, eur_usd)),
                }
                for p in history
            ],
        },
        meta={
            "account_name": account.name,
            "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
            "sync_status": account.sync_status,
        },
    )


@router.get("/performance")
async def get_performance(
    from_date: date | None = Query(None, description="Inicio del rango (ISO 8601)"),
    to_date: date | None = Query(None, description="Fin del rango (ISO 8601)"),
    interval: str = Query("1d", description="Granularidad: 1d | 1w | 1M (actualmente solo 1d)"),
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> dict:
    """
    Serie temporal del valor del portafolio.
    Selector de rango: 7d, 30d, 90d, 1y, todo.
    """
    resolved_to = to_date or date.today()
    resolved_from = from_date or (resolved_to - timedelta(days=30))

    prices = await _get_prices(db, account.id)
    eur_usd = prices.get("EUR", Decimal("1.08"))

    service = PortfolioService(db=db, account_id=account.id)
    points = await service.calculate_performance_history(
        from_date=resolved_from,
        to_date=resolved_to,
    )
    drawdown = await service.calculate_drawdown()

    return ok(
        data={
            "series": [
                {
                    "date": p.snapshot_date.isoformat(),
                    "total_value_usd": str(p.total_value_usd),
                    "total_value_eur": str(_to_eur(p.total_value_usd, eur_usd)),
                    "invested_usd": str(p.invested_usd),
                    "invested_eur": str(_to_eur(p.invested_usd, eur_usd)),
                    "pnl_usd": str(p.pnl_usd),
                    "pnl_eur": str(_to_eur(p.pnl_usd, eur_usd)),
                    "pnl_pct": str(p.pnl_pct),
                }
                for p in points
            ],
            "drawdown": {
                "max_drawdown_pct": str(drawdown.max_drawdown_pct),
                "peak_date": drawdown.peak_date.isoformat() if drawdown.peak_date else None,
                "trough_date": drawdown.trough_date.isoformat() if drawdown.trough_date else None,
                "peak_value_usd": str(drawdown.peak_value_usd),
                "peak_value_eur": str(_to_eur(drawdown.peak_value_usd, eur_usd)),
                "trough_value_usd": str(drawdown.trough_value_usd),
                "trough_value_eur": str(_to_eur(drawdown.trough_value_usd, eur_usd)),
            },
        },
        meta={
            "from_date": resolved_from.isoformat(),
            "to_date": resolved_to.isoformat(),
            "interval": interval,
            "points": len(points),
        },
    )


@router.get("/dca/{asset}")
async def get_dca(
    asset: str,
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> dict:
    """
    Análisis DCA completo para el activo indicado (por defecto BTC).
    Incluye: VWAP, cantidad total, coste base, P&L, calendario de compras.
    """
    asset = asset.upper()
    prices = await _get_prices(db, account.id)
    eur_usd = prices.get("EUR", Decimal("1.08"))
    current_price = prices.get(asset, Decimal("0"))

    service = PortfolioService(db=db, account_id=account.id)
    dca = await service.calculate_dca_analysis(asset=asset, current_price=current_price)

    return ok(
        data={
            "asset": dca.asset,
            "current_price_usd": str(dca.current_price_usd),
            "current_price_eur": str(_to_eur(dca.current_price_usd, eur_usd)),
            "total_quantity": str(dca.total_quantity),
            "vwap_usd": str(dca.vwap_usd),
            "vwap_eur": str(_to_eur(dca.vwap_usd, eur_usd)),
            "cost_basis_usd": str(dca.cost_basis_usd),
            "cost_basis_eur": str(_to_eur(dca.cost_basis_usd, eur_usd)),
            "pnl_usd": str(dca.pnl_usd),
            "pnl_eur": str(_to_eur(dca.pnl_usd, eur_usd)),
            "pnl_pct": str(dca.pnl_pct),
            "total_events": dca.total_events,
            "buy_events": [
                {
                    "date": e.executed_at.isoformat(),
                    "quantity": str(e.quantity),
                    "price_usd": str(e.price_usd),
                    "price_eur": str(_to_eur(e.price_usd, eur_usd)),
                    "cumulative_quantity": str(e.cumulative_quantity),
                    "cumulative_vwap": str(e.cumulative_vwap),
                    "cumulative_vwap_eur": str(_to_eur(e.cumulative_vwap, eur_usd)),
                }
                for e in dca.buy_events
            ],
        },
        meta={
            "asset": asset,
            "price_source": "price_history" if current_price > Decimal("0") else "unavailable",
            "eur_usd_rate": str(eur_usd),
        },
    )
