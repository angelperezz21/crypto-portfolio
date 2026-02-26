"""
Router: /api/v1/dashboard
GET /overview                      → resumen ejecutivo del portafolio
GET /performance                   → evolución temporal con selector de rango
GET /dca/{asset}                   → análisis DCA completo para un activo
GET /btc-insights                  → análisis de timing de compras BTC
GET /btc-insights/dca-simulation   → DCA real vs DCA simulado perfecto
"""

from collections import defaultdict
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_account, get_db
from core.responses import ok
from models.account import Account
from models.price_history import PriceHistory
from models.transaction import Transaction
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
    - Datos de los últimos 90 días de portfolio_snapshots
    """
    prices = await _get_prices(db, account.id)
    eur_usd = prices.get("EUR", Decimal("1.08"))
    service = PortfolioService(db=db, account_id=account.id)
    overview = await service.calculate_overview(current_prices=prices)

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


# ---------------------------------------------------------------------------
# Helpers privados para btc-insights
# ---------------------------------------------------------------------------


def _compute_mas(
    price_rows: list,
) -> tuple[list[Decimal | None], list[Decimal | None]]:
    """
    Calcula MA50 y MA200 con ventana deslizante O(n).
    Devuelve dos listas paralelas a price_rows (None si no hay suficientes datos).
    """
    n = len(price_rows)
    ma50: list[Decimal | None] = [None] * n
    ma200: list[Decimal | None] = [None] * n

    running50 = Decimal("0")
    running200 = Decimal("0")

    for i, ph in enumerate(price_rows):
        c = Decimal(str(ph.close))
        running50 += c
        running200 += c

        if i >= 50:
            running50 -= Decimal(str(price_rows[i - 50].close))
        if i >= 200:
            running200 -= Decimal(str(price_rows[i - 200].close))

        if i >= 49:
            ma50[i] = (running50 / Decimal("50")).quantize(Decimal("0.01"))
        if i >= 199:
            ma200[i] = (running200 / Decimal("200")).quantize(Decimal("0.01"))

    return ma50, ma200


def _timing_percentile(
    buy_date: date,
    buy_price: Decimal,
    price_by_date: dict[date, Decimal],
) -> Decimal | None:
    """
    Percentil del precio de compra dentro del rango de los 30 días previos.
    0  = compraste en el mínimo mensual (dip buyer)
    100 = compraste en el máximo mensual (FOMO)
    """
    prior = [
        price_by_date[buy_date - timedelta(days=i)]
        for i in range(1, 31)
        if (buy_date - timedelta(days=i)) in price_by_date
    ]
    if not prior:
        return None
    lo, hi = min(prior), max(prior)
    if hi == lo:
        return Decimal("50")
    pct = (buy_price - lo) / (hi - lo) * Decimal("100")
    return max(Decimal("0"), min(Decimal("100"), pct)).quantize(Decimal("1"))


@router.get("/btc-insights")
async def get_btc_insights(
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> dict:
    """
    Análisis de timing de compras BTC:
    - Historial de precio BTC con MA50/MA200 y dots de compra coloreados por timing
    - Timing percentile por compra (0=dip, 100=FOMO) + análisis agregado
    - Histograma de BTC acumulado por rango de precio
    - Heatmap mensual de inversión
    - Stats: % compras en verde, mejor y peor entrada
    """
    prices = await _get_prices(db, account.id)
    eur_usd = prices.get("EUR", Decimal("1.08"))
    current_price = prices.get("BTC", Decimal("0"))

    service = PortfolioService(db=db, account_id=account.id)
    dca = await service.calculate_dca_analysis("BTC", current_price, eur_usd)

    # Historial completo de precios (necesario para MAs correctas desde el inicio)
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

    # Medias móviles — ventana deslizante O(n)
    ma50_vals, ma200_vals = _compute_mas(price_rows)

    price_history_out = [
        {
            "date": ph.open_at.date().isoformat(),
            "price": str(ph.close),
            "ma50": str(ma50_vals[i]) if ma50_vals[i] is not None else None,
            "ma200": str(ma200_vals[i]) if ma200_vals[i] is not None else None,
        }
        for i, ph in enumerate(price_rows)
    ]

    # Lookup fecha → precio de cierre para timing analysis
    price_by_date: dict[date, Decimal] = {
        ph.open_at.date(): Decimal(str(ph.close)) for ph in price_rows
    }

    # MA200 por fecha para contexto de cada compra
    ma200_by_date: dict[date, Decimal] = {
        price_rows[i].open_at.date(): ma200_vals[i]  # type: ignore[misc]
        for i in range(len(price_rows))
        if ma200_vals[i] is not None
    }

    # Buy events enriquecidos con timing percentile
    buy_events_out: list[dict] = []
    timing_percentiles: list[Decimal] = []
    buys_below_ma200 = 0
    buys_above_ma200 = 0

    for e in dca.buy_events:
        tp = _timing_percentile(e.executed_at.date(), e.price_usd, price_by_date)
        if tp is not None:
            timing_percentiles.append(tp)

        ma200_day = ma200_by_date.get(e.executed_at.date())
        if ma200_day is not None:
            if e.price_usd < ma200_day:
                buys_below_ma200 += 1
            else:
                buys_above_ma200 += 1

        buy_events_out.append(
            {
                "date": e.executed_at.date().isoformat(),
                "price_usd": str(e.price_usd),
                "quantity": str(e.quantity),
                "total_usd": str(
                    (e.price_usd * e.quantity).quantize(Decimal("0.00000001"))
                ),
                "timing_pct": str(tp) if tp is not None else None,
            }
        )

    # Timing — estadísticas agregadas
    dist = {"q1": 0, "q2": 0, "q3": 0, "q4": 0}
    for tp in timing_percentiles:
        if tp <= Decimal("25"):
            dist["q1"] += 1
        elif tp <= Decimal("50"):
            dist["q2"] += 1
        elif tp <= Decimal("75"):
            dist["q3"] += 1
        else:
            dist["q4"] += 1

    avg_tp: Decimal | None = None
    if timing_percentiles:
        avg_tp = (
            sum(timing_percentiles) / Decimal(len(timing_percentiles))
        ).quantize(Decimal("1"))

    timing_label = (
        "Dip Buyer" if avg_tp is not None and avg_tp < Decimal("33")
        else "FOMO Buyer" if avg_tp is not None and avg_tp > Decimal("67")
        else "Neutral"
    )

    timing_analysis = {
        "avg_percentile": str(avg_tp) if avg_tp is not None else None,
        "label": timing_label,
        "distribution": dist,
        "buys_below_ma200": buys_below_ma200,
        "buys_above_ma200": buys_above_ma200,
    }

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
            "timing_analysis": timing_analysis,
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


@router.get("/btc-insights/dca-simulation")
async def get_dca_simulation(
    interval: str = Query("weekly", description="weekly | monthly"),
    db: AsyncSession = Depends(get_db),
    account: Account = Depends(get_account),
) -> dict:
    """
    Compara la acumulación real de BTC con un DCA simulado (semanal o mensual)
    usando exactamente el mismo capital total y el mismo periodo temporal.

    Permite responder: ¿tu market timing añadió o restó BTC vs invertir de forma mecánica?
    """
    prices = await _get_prices(db, account.id)
    eur_usd = prices.get("EUR", Decimal("1.08"))
    current_price = prices.get("BTC", Decimal("0"))

    # Transacciones BTC de compra reales
    tx_q = (
        select(Transaction)
        .where(
            Transaction.account_id == account.id,
            Transaction.base_asset == "BTC",
            Transaction.type.in_(["buy", "deposit"]),
        )
        .order_by(Transaction.executed_at)
    )
    txns = list((await db.execute(tx_q)).scalars().all())

    if not txns:
        return ok(data={"real": [], "simulated": [], "summary": {}})

    # Capital total invertido
    total_invested = sum(
        (
            tx.total_value_usd
            or ((tx.price * tx.quantity) if tx.price else Decimal("0"))
        )
        for tx in txns
    )

    first_date = txns[0].executed_at.date()
    last_date = date.today()

    # Precios históricos BTCUSDT desde la primera compra
    from_dt = datetime.combine(first_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    price_rows = list(
        (
            await db.execute(
                select(PriceHistory)
                .where(
                    PriceHistory.symbol == "BTCUSDT",
                    PriceHistory.interval == "1d",
                    PriceHistory.open_at >= from_dt,
                )
                .order_by(PriceHistory.open_at)
            )
        )
        .scalars()
        .all()
    )

    price_by_date: dict[date, Decimal] = {
        ph.open_at.date(): Decimal(str(ph.close)) for ph in price_rows
    }

    # Generar fechas del DCA simulado
    step_days = 7 if interval == "weekly" else 30
    sim_dates: list[date] = []
    d_iter = first_date
    while d_iter <= last_date:
        sim_dates.append(d_iter)
        d_iter += timedelta(days=step_days)

    if not sim_dates:
        return ok(data={"real": [], "simulated": [], "summary": {}})

    amount_per_period = total_invested / Decimal(len(sim_dates))

    # Curva simulada — comprar igual cada periodo
    sim_btc = Decimal("0")
    sim_curve: list[dict] = []
    for sim_date in sim_dates:
        # Buscar precio más cercano (hasta 5 días hacia adelante)
        price = None
        for offset in range(5):
            candidate = sim_date + timedelta(days=offset)
            if candidate in price_by_date:
                price = price_by_date[candidate]
                break
        if price and price > Decimal("0"):
            sim_btc += (amount_per_period / price).quantize(Decimal("0.00000001"))
        sim_curve.append({
            "date": sim_date.isoformat(),
            "btc_accumulated": str(sim_btc),
        })

    # Curva real — acumulación por fecha de ejecución
    real_btc = Decimal("0")
    real_by_date: dict[date, Decimal] = {}
    for tx in txns:
        real_btc += tx.quantity
        real_by_date[tx.executed_at.date()] = real_btc

    # Curva real diaria alineada con fechas de simulación
    all_dates = sorted(set(sim_dates) | set(real_by_date.keys()))
    real_curve: list[dict] = []
    last_qty = Decimal("0")
    for d_val in all_dates:
        if d_val in real_by_date:
            last_qty = real_by_date[d_val]
        real_curve.append({
            "date": d_val.isoformat(),
            "btc_accumulated": str(last_qty),
        })

    # Summary
    diff_btc = real_btc - sim_btc
    diff_pct = (
        (diff_btc / sim_btc * Decimal("100")).quantize(Decimal("0.01"))
        if sim_btc > Decimal("0")
        else Decimal("0")
    )
    diff_value_usd = (
        (diff_btc * current_price).quantize(Decimal("0.01"))
        if current_price > Decimal("0")
        else Decimal("0")
    )

    summary = {
        "total_invested_usd": str(total_invested.quantize(Decimal("0.01"))),
        "real_btc": str(real_btc.quantize(Decimal("0.00000001"))),
        "simulated_btc": str(sim_btc.quantize(Decimal("0.00000001"))),
        "diff_btc": str(diff_btc.quantize(Decimal("0.00000001"))),
        "diff_pct": str(diff_pct),
        "diff_value_usd": str(diff_value_usd),
        "diff_value_eur": str(_to_eur(diff_value_usd, eur_usd).quantize(Decimal("0.01"))),
        "interval": interval,
        "periods_simulated": len(sim_dates),
    }

    return ok(
        data={
            "real": real_curve,
            "simulated": sim_curve,
            "summary": summary,
        },
        meta={
            "interval": interval,
            "from_date": first_date.isoformat(),
            "to_date": last_date.isoformat(),
        },
    )
