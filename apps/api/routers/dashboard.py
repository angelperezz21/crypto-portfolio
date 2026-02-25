"""
Router: /api/v1/dashboard
GET /overview        → resumen ejecutivo del portafolio
GET /performance     → evolución temporal con selector de rango
GET /dca/{asset}     → análisis DCA completo para un activo
GET /btc-insights    → análisis de timing de compras BTC
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
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

    # Serie de los últimos 90 días para el mini-gráfico del overview
    from_date = date.today() - timedelta(days=90)
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
            "evolution_90d": [
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
    dca = await service.calculate_dca_analysis(
        asset=asset, current_price=current_price, eur_usd=eur_usd
    )

    return ok(
        data={
            "asset": dca.asset,
            "current_price_usd": str(dca.current_price_usd),
            "current_price_eur": str(_to_eur(dca.current_price_usd, eur_usd)),
            "total_quantity": str(dca.total_quantity),
            "vwap_usd": str(dca.vwap_usd),
            # vwap_eur calculado con precios históricos reales, no con tipo de cambio actual
            "vwap_eur": str(dca.vwap_eur),
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
                    # price_eur histórico: para BTCEUR es el precio real pagado en EUR
                    "price_eur": str(e.price_eur),
                    "cumulative_quantity": str(e.cumulative_quantity),
                    "cumulative_vwap": str(e.cumulative_vwap),
                    "cumulative_vwap_eur": str(e.cumulative_vwap_eur),
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


@router.get("/btc-insights")
async def get_btc_insights(
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> dict:
    """
    Análisis de timing de compras BTC:
    - Historial de precio BTC con dots de compra marcados
    - Histograma de BTC acumulado por rango de precio
    - Heatmap mensual de inversión
    - Stats: % compras en verde, mejor y peor entrada
    """
    from models.price_history import PriceHistory

    prices = await _get_prices(db, account.id)
    eur_usd = prices.get("EUR", Decimal("1.08"))
    current_price = prices.get("BTC", Decimal("0"))

    service = PortfolioService(db=db, account_id=account.id)
    dca = await service.calculate_dca_analysis("BTC", current_price, eur_usd)

    # Price history
    price_rows = list(
        (
            await db.execute(
                select(PriceHistory)
                .where(
                    PriceHistory.symbol == "BTCUSDT",
                    PriceHistory.interval == "1d",
                )
                .order_by(PriceHistory.open_at)
            )
        )
        .scalars()
        .all()
    )

    price_history_out = [
        {"date": ph.open_at.date().isoformat(), "price": str(ph.close)}
        for ph in price_rows
    ]

    # Buy events
    buy_events_out = [
        {
            "date": e.executed_at.date().isoformat(),
            "price_usd": str(e.price_usd),
            "quantity": str(e.quantity),
            "total_usd": str(
                (e.price_usd * e.quantity).quantize(Decimal("0.00000001"))
            ),
        }
        for e in dca.buy_events
    ]

    # Stats — iterar con Decimal, nunca float
    buys_in_profit = 0
    best_gain = Decimal("-999999")
    worst_gain = Decimal("999999")
    best_event = None
    worst_event = None

    for e in dca.buy_events:
        if e.price_usd > Decimal("0"):
            gain = (
                (current_price - e.price_usd)
                / e.price_usd
                * Decimal("100")
            ).quantize(Decimal("0.01"))
            if current_price > e.price_usd:
                buys_in_profit += 1
            if gain > best_gain:
                best_gain, best_event = gain, e
            if gain < worst_gain:
                worst_gain, worst_event = gain, e

    total_buys = len(dca.buy_events)
    in_profit_pct = (
        (Decimal(buys_in_profit) / Decimal(total_buys) * Decimal("100")).quantize(
            Decimal("0.01")
        )
        if total_buys
        else Decimal("0")
    )

    stats = {
        "total_buys": total_buys,
        "buys_in_profit": buys_in_profit,
        "buys_in_profit_pct": str(in_profit_pct),
        "date_first_buy": (
            dca.buy_events[0].executed_at.date().isoformat()
            if dca.buy_events
            else None
        ),
        "date_last_buy": (
            dca.buy_events[-1].executed_at.date().isoformat()
            if dca.buy_events
            else None
        ),
        "best_buy": (
            {
                "date": best_event.executed_at.date().isoformat(),
                "price_usd": str(best_event.price_usd),
                "quantity": str(best_event.quantity),
                "gain_pct": str(best_gain),
            }
            if best_event
            else None
        ),
        "worst_buy": (
            {
                "date": worst_event.executed_at.date().isoformat(),
                "price_usd": str(worst_event.price_usd),
                "quantity": str(worst_event.quantity),
                "gain_pct": str(worst_gain),
            }
            if worst_event
            else None
        ),
    }

    # Histograma — buckets de $5k con Decimal
    BUCKET = Decimal("5000")
    histogram: dict[int, dict] = {}
    if dca.buy_events:
        valid_prices = [e.price_usd for e in dca.buy_events if e.price_usd > Decimal("0")]
        if valid_prices:
            cur = (min(valid_prices) // BUCKET) * BUCKET
            end = ((max(valid_prices) // BUCKET) + 1) * BUCKET
            while cur < end:
                histogram[int(cur)] = {
                    "bucket_min": int(cur),
                    "bucket_max": int(cur + BUCKET),
                    "label": f"${int(cur / 1000)}k-{int((cur + BUCKET) / 1000)}k",
                    "btc_quantity": Decimal("0"),
                    "buy_count": 0,
                }
                cur += BUCKET
            for e in dca.buy_events:
                k = int((e.price_usd // BUCKET) * BUCKET)
                if k in histogram:
                    histogram[k]["btc_quantity"] += e.quantity
                    histogram[k]["buy_count"] += 1

    histogram_out = [
        {
            **{k: v for k, v in b.items() if k != "btc_quantity"},
            "btc_quantity": str(
                b["btc_quantity"].quantize(Decimal("0.00000001"))
            ),
        }
        for b in sorted(histogram.values(), key=lambda x: x["bucket_min"])
    ]

    # Heatmap mensual
    monthly: dict = defaultdict(
        lambda: {
            "total_usd": Decimal("0"),
            "total_btc": Decimal("0"),
            "buy_count": 0,
        }
    )
    for e in dca.buy_events:
        k = (e.executed_at.year, e.executed_at.month)
        monthly[k]["total_usd"] += (e.price_usd * e.quantity).quantize(
            Decimal("0.00000001")
        )
        monthly[k]["total_btc"] += e.quantity
        monthly[k]["buy_count"] += 1

    heatmap_out = [
        {
            "year": y,
            "month": m,
            "total_usd": str(v["total_usd"]),
            "total_btc": str(v["total_btc"].quantize(Decimal("0.00000001"))),
            "buy_count": v["buy_count"],
        }
        for (y, m), v in sorted(monthly.items())
    ]

    return ok(
        data={
            "current_price_usd": str(current_price),
            "vwap_usd": str(dca.vwap_usd),
            "stats": stats,
            "price_history": price_history_out,
            "buy_events": buy_events_out,
            "price_histogram": histogram_out,
            "monthly_heatmap": heatmap_out,
        },
        meta={
            "asset": "BTC",
            "eur_usd_rate": str(eur_usd),
            "price_history_points": len(price_history_out),
            "buy_events_count": total_buys,
        },
    )
