"""
Servicio de cálculos financieros del portafolio.

Reglas críticas (skill financial-calcs):
- NUNCA float para datos de negocio: siempre Decimal("...") o Decimal(str(valor))
- VWAP: sum(precio_i * qty_i) / sum(qty_i), solo BUY + DEPOSIT con precio
- FIFO: los sells consumen los lots más antiguos primero
- Drawdown: (valor_dia - max_histórico_hasta_ese_dia) / max_histórico, tomar mínimo
- XIRR: Newton-Raphson puro, sin numpy; float solo en el algoritmo iterativo (no en datos)
"""

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

import structlog
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from models.balance_snapshot import BalanceSnapshot
from models.portfolio_snapshot import PortfolioSnapshot
from models.transaction import Transaction

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

SATOSHI = Decimal("0.00000001")
FIAT_AND_STABLECOINS = frozenset(
    {"EUR", "USD", "GBP", "CHF", "USDT", "USDC", "BUSD", "FDUSD", "DAI", "TUSD", "USDP"}
)
BUY_TYPES = frozenset({"buy", "deposit", "earn_interest", "staking_reward"})
SELL_TYPES = frozenset({"sell", "withdrawal"})

# Precisiones de redondeo
PRICE_PRECISION = Decimal("0.00000001")   # 8 decimales para precios
QTY_PRECISION = Decimal("0.000000000000000001")  # 18 dec para cantidades
PCT_PRECISION = Decimal("0.01")           # 2 decimales para porcentajes


# ---------------------------------------------------------------------------
# Tipos de retorno
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FIFOLot:
    quantity: Decimal
    unit_cost: Decimal      # coste por unidad en USD
    unit_cost_eur: Decimal  # coste por unidad en EUR histórico


@dataclass
class FIFOResult:
    remaining_lots: list[FIFOLot]
    realized_pnl: Decimal
    cost_basis: Decimal      # sum(lot.quantity * lot.unit_cost) en USD
    cost_basis_eur: Decimal  # sum(lot.quantity * lot.unit_cost_eur) en EUR histórico


@dataclass
class AssetMetrics:
    asset: str
    quantity: Decimal
    value_usd: Decimal
    portfolio_pct: Decimal      # % del portafolio total (se rellena en overview)
    avg_buy_price_usd: Decimal  # cost_basis_usd / quantity
    avg_buy_price_eur: Decimal  # cost_basis_eur / quantity (EUR histórico)
    cost_basis_usd: Decimal
    cost_basis_eur: Decimal     # EUR histórico (tx.price para BTCEUR, aprox para BTCUSDT)
    pnl_usd: Decimal
    pnl_pct: Decimal            # (pnl / cost_basis) * 100
    realized_pnl_usd: Decimal


@dataclass
class PortfolioOverview:
    total_value_usd: Decimal
    invested_usd: Decimal
    pnl_unrealized_usd: Decimal
    pnl_realized_usd: Decimal
    roi_pct: Decimal
    irr_annual_pct: Decimal | None
    assets: list[AssetMetrics]


@dataclass
class DCABuyEvent:
    executed_at: datetime
    quantity: Decimal
    price_usd: Decimal
    price_eur: Decimal           # EUR histórico: tx.price para BTCEUR; USD/eur_usd_actual para BTCUSDT
    cumulative_quantity: Decimal
    cumulative_vwap: Decimal     # VWAP acumulado en USD hasta este evento
    cumulative_vwap_eur: Decimal # VWAP acumulado en EUR histórico hasta este evento


@dataclass
class DCAAnalysis:
    asset: str
    current_price_usd: Decimal
    total_quantity: Decimal
    vwap_usd: Decimal            # precio promedio ponderado en USD
    vwap_eur: Decimal            # precio promedio ponderado en EUR histórico
    cost_basis_usd: Decimal
    pnl_usd: Decimal
    pnl_pct: Decimal
    total_events: int
    buy_events: list[DCABuyEvent]


@dataclass
class PerformancePoint:
    snapshot_date: date
    total_value_usd: Decimal
    invested_usd: Decimal
    pnl_usd: Decimal
    pnl_pct: Decimal             # (pnl / invested) * 100


@dataclass
class DrawdownResult:
    max_drawdown_pct: Decimal    # negativo: -25.34 = caída del 25.34%
    peak_date: date | None
    trough_date: date | None
    peak_value_usd: Decimal
    trough_value_usd: Decimal


# ---------------------------------------------------------------------------
# Algoritmos financieros puros (sin BD, sin IO, 100% testables)
# ---------------------------------------------------------------------------


def _usd_unit_cost(tx: "Transaction") -> Decimal:
    """
    Precio unitario en USD para FIFO.
    Prioridad: total_value_usd / quantity (convierte EUR→USD si fue rellenado).
    Fallback: tx.price (solo correcto si quote_asset es USD/stablecoin).
    """
    if tx.total_value_usd is not None and tx.quantity > Decimal("0"):
        return (tx.total_value_usd / tx.quantity).quantize(PRICE_PRECISION, ROUND_HALF_UP)
    return tx.price if tx.price is not None else Decimal("0")


def _eur_unit_cost(tx: "Transaction", eur_usd: Decimal) -> Decimal:
    """
    Precio unitario en EUR histórico.
    - Trades BTCEUR: tx.price ya está en EUR — se usa directamente (exacto).
    - Trades BTCUSDT: se convierte el precio USD con el tipo de cambio actual
      (mejor aproximación posible sin almacenar el tipo histórico por transacción).
    """
    if tx.quote_asset == "EUR":
        return tx.price if tx.price is not None else Decimal("0")
    usd_cost = _usd_unit_cost(tx)
    if eur_usd <= Decimal("0"):
        return Decimal("0")
    return (usd_cost / eur_usd).quantize(PRICE_PRECISION, ROUND_HALF_UP)


def compute_fifo(
    buys: list["Transaction"],
    sells: list["Transaction"],
    eur_usd: Decimal = Decimal("1.08"),
) -> FIFOResult:
    """
    Computa el coste base (FIFO) y el P&L realizado.

    buys:  transacciones buy/deposit ordenadas por executed_at ASC
    sells: transacciones sell/withdrawal ordenadas por executed_at ASC
    eur_usd: tipo de cambio EUR/USD actual (usado para trades BTCUSDT).

    unit_cost en USD: usa total_value_usd/qty (histórico, correcto para BTCEUR).
    unit_cost_eur: tx.price para BTCEUR (exacto); USD/eur_usd para BTCUSDT (aproximado).
    Los lots se consumen de más antiguo a más nuevo. Si una venta supera
    los lots disponibles (data gap), se ignora el exceso.
    """
    lots: deque[FIFOLot] = deque(
        FIFOLot(
            quantity=tx.quantity,
            unit_cost=_usd_unit_cost(tx),
            unit_cost_eur=_eur_unit_cost(tx, eur_usd),
        )
        for tx in buys
    )

    realized_pnl = Decimal("0")

    for sell in sells:
        qty_to_sell = sell.quantity
        sell_price = _usd_unit_cost(sell) if sell.total_value_usd is not None else (
            sell.price if sell.price is not None else Decimal("0")
        )

        while qty_to_sell > Decimal("0") and lots:
            lot = lots[0]
            if lot.quantity <= qty_to_sell:
                realized_pnl += (sell_price - lot.unit_cost) * lot.quantity
                qty_to_sell -= lot.quantity
                lots.popleft()
            else:
                realized_pnl += (sell_price - lot.unit_cost) * qty_to_sell
                # Lot parcialmente consumido — preservar unit_cost_eur del lot original
                lots[0] = FIFOLot(
                    quantity=lot.quantity - qty_to_sell,
                    unit_cost=lot.unit_cost,
                    unit_cost_eur=lot.unit_cost_eur,
                )
                qty_to_sell = Decimal("0")

    remaining = list(lots)
    cost_basis = sum(
        (lot.quantity * lot.unit_cost for lot in remaining),
        Decimal("0"),
    )
    cost_basis_eur = sum(
        (lot.quantity * lot.unit_cost_eur for lot in remaining),
        Decimal("0"),
    )

    return FIFOResult(
        remaining_lots=remaining,
        realized_pnl=realized_pnl.quantize(PRICE_PRECISION, ROUND_HALF_UP),
        cost_basis=cost_basis.quantize(PRICE_PRECISION, ROUND_HALF_UP),
        cost_basis_eur=cost_basis_eur.quantize(PRICE_PRECISION, ROUND_HALF_UP),
    )


def compute_vwap(transactions: list["Transaction"]) -> Decimal:
    """
    VWAP en USD = sum(unit_cost_usd_i * qty_i) / sum(qty_i).
    Usa _usd_unit_cost() para convertir correctamente trades EUR→USD.
    Ignora transacciones sin coste calculable.
    """
    total_cost = Decimal("0")
    total_qty = Decimal("0")

    for tx in transactions:
        unit_cost = _usd_unit_cost(tx)
        if unit_cost == Decimal("0"):
            continue
        total_cost += unit_cost * tx.quantity
        total_qty += tx.quantity

    if total_qty == Decimal("0"):
        return Decimal("0")

    return (total_cost / total_qty).quantize(PRICE_PRECISION, ROUND_HALF_UP)


def compute_drawdown(snapshots: list[PortfolioSnapshot]) -> DrawdownResult:
    """
    Drawdown máximo sobre la serie temporal de portfolio_snapshots.
    Para cada día: (valor - max_histórico) / max_histórico
    Retorna el mínimo (peor caída).
    """
    if not snapshots:
        return DrawdownResult(
            max_drawdown_pct=Decimal("0"),
            peak_date=None,
            trough_date=None,
            peak_value_usd=Decimal("0"),
            trough_value_usd=Decimal("0"),
        )

    running_max = Decimal("0")
    running_max_snap = snapshots[0]

    worst_drawdown = Decimal("0")
    worst_peak_snap = snapshots[0]
    worst_trough_snap = snapshots[0]

    for snap in snapshots:
        if snap.total_value_usd > running_max:
            running_max = snap.total_value_usd
            running_max_snap = snap

        if running_max > Decimal("0"):
            dd = (snap.total_value_usd - running_max) / running_max
            if dd < worst_drawdown:
                worst_drawdown = dd
                worst_peak_snap = running_max_snap
                worst_trough_snap = snap

    return DrawdownResult(
        max_drawdown_pct=(worst_drawdown * Decimal("100")).quantize(PCT_PRECISION, ROUND_HALF_UP),
        peak_date=worst_peak_snap.snapshot_date,
        trough_date=worst_trough_snap.snapshot_date,
        peak_value_usd=worst_peak_snap.total_value_usd,
        trough_value_usd=worst_trough_snap.total_value_usd,
    )


def compute_xirr(cash_flows: list[tuple[date, Decimal]]) -> Decimal | None:
    """
    Tasa Interna de Retorno para flujos de caja irregulares (XIRR).
    Implementación Newton-Raphson pura, sin scipy ni numpy.

    cash_flows: lista de (fecha, monto)
      - Inversiones/depósitos: montos NEGATIVOS
      - Valor actual del portafolio: monto POSITIVO al final

    NOTA: float se usa únicamente en el algoritmo numérico iterativo,
    no en datos de negocio. El resultado se convierte a Decimal.
    Retorna % anual, o None si no converge.
    """
    if len(cash_flows) < 2:
        return None

    dates = [cf[0] for cf in cash_flows]
    # float solo para el cálculo iterativo numérico
    amounts = [float(cf[1]) for cf in cash_flows]
    t0 = dates[0]
    years = [(d - t0).days / 365.25 for d in dates]

    def npv(rate: float) -> float:
        if rate <= -1.0:
            return float("inf")
        return sum(a / (1.0 + rate) ** t for a, t in zip(amounts, years))

    def d_npv(rate: float) -> float:
        if rate <= -1.0:
            return float("inf")
        return sum(-t * a / (1.0 + rate) ** (t + 1.0) for a, t in zip(amounts, years))

    rate = 0.1  # estimación inicial: 10% anual
    for _ in range(200):
        fn = npv(rate)
        dfn = d_npv(rate)
        if abs(dfn) < 1e-12:
            return None
        step = fn / dfn
        rate -= step
        if abs(step) < 1e-10:
            break
    else:
        return None  # no converge

    if rate <= -1.0 or rate > 100.0:
        return None  # resultado sin sentido económico

    return Decimal(str(round(rate * 100.0, 4)))


# ---------------------------------------------------------------------------
# Servicio con acceso a base de datos
# ---------------------------------------------------------------------------


class PortfolioService:
    """
    Calcula métricas financieras del portafolio leyendo de la BD.

    current_prices: dict asset → precio actual en USD (Decimal).
    Este dict lo aporta la capa de llamada (router o scheduler),
    que lo obtiene de BinanceClient.get_ticker_price() o price_history.
    """

    def __init__(self, db: AsyncSession, account_id: uuid.UUID) -> None:
        self.db = db
        self.account_id = account_id

    # -----------------------------------------------------------------------
    # Queries auxiliares
    # -----------------------------------------------------------------------

    async def _get_transactions(self, asset: str | None = None) -> list[Transaction]:
        """Todas las transacciones de la cuenta, opcionalmente filtradas por activo."""
        q = select(Transaction).where(Transaction.account_id == self.account_id)
        if asset:
            q = q.where(Transaction.base_asset == asset)
        q = q.order_by(Transaction.executed_at)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def _get_latest_balances(self) -> dict[str, Decimal]:
        """
        Último balance conocido por activo (free + locked).
        Usa una subquery con MAX(snapshot_at) por asset para compatibilidad
        con cualquier backend SQLAlchemy (evita DISTINCT ON que es PostgreSQL-only
        y no es generado correctamente por el ORM).
        """
        # Subquery: timestamp máximo por asset para esta cuenta
        latest_ts_subq = (
            select(
                BalanceSnapshot.asset,
                func.max(BalanceSnapshot.snapshot_at).label("max_ts"),
            )
            .where(BalanceSnapshot.account_id == self.account_id)
            .group_by(BalanceSnapshot.asset)
            .subquery()
        )
        # Join para traer el registro completo del snapshot más reciente
        q = (
            select(
                BalanceSnapshot.asset,
                (BalanceSnapshot.free + BalanceSnapshot.locked).label("total"),
            )
            .join(
                latest_ts_subq,
                (BalanceSnapshot.asset == latest_ts_subq.c.asset)
                & (BalanceSnapshot.snapshot_at == latest_ts_subq.c.max_ts),
            )
            .where(BalanceSnapshot.account_id == self.account_id)
        )
        result = await self.db.execute(q)
        rows = result.fetchall()
        return {row.asset: Decimal(str(row.total)) for row in rows if row.total}

    async def _get_portfolio_snapshots(
        self,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[PortfolioSnapshot]:
        q = select(PortfolioSnapshot).where(
            PortfolioSnapshot.account_id == self.account_id
        )
        if from_date:
            q = q.where(PortfolioSnapshot.snapshot_date >= from_date)
        if to_date:
            q = q.where(PortfolioSnapshot.snapshot_date <= to_date)
        q = q.order_by(PortfolioSnapshot.snapshot_date)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # Helpers financieros
    # -----------------------------------------------------------------------

    @staticmethod
    def _split_buys_sells(
        txns: list[Transaction],
    ) -> tuple[list[Transaction], list[Transaction]]:
        buys = [t for t in txns if t.type in BUY_TYPES]
        sells = [t for t in txns if t.type in SELL_TYPES]
        return buys, sells

    @staticmethod
    def _compute_invested(txns: list[Transaction]) -> Decimal:
        """
        Capital invertido = total gastado en compras (buy + deposit)
                           - retiradas de fiat/stablecoin.
        Usa total_value_usd si está disponible; si no, price * quantity.
        Las ventas no reducen el capital invertido (métrica de capital total desplegado).
        """
        invested = Decimal("0")
        for tx in txns:
            if tx.type in ("deposit", "buy"):
                val = tx.total_value_usd or (
                    (tx.price * tx.quantity) if tx.price else Decimal("0")
                )
                invested += val
            elif tx.type == "withdrawal" and tx.base_asset in FIAT_AND_STABLECOINS:
                val = tx.total_value_usd or (
                    (tx.price * tx.quantity) if tx.price else Decimal("0")
                )
                invested -= val
        return invested.quantize(PRICE_PRECISION, ROUND_HALF_UP)

    # -----------------------------------------------------------------------
    # Métodos públicos
    # -----------------------------------------------------------------------

    async def calculate_asset_metrics(
        self,
        current_prices: dict[str, Decimal],
    ) -> list[AssetMetrics]:
        """
        Métricas por activo: balance, valor USD, coste base FIFO, P&L.
        current_prices: {asset: price_usd}
        """
        all_txns = await self._get_transactions()
        balances = await self._get_latest_balances()
        eur_usd = current_prices.get("EUR", Decimal("1.08"))

        # Agrupar transacciones por activo
        by_asset: dict[str, list[Transaction]] = {}
        for tx in all_txns:
            by_asset.setdefault(tx.base_asset, []).append(tx)

        total_value = Decimal("0")
        metrics: list[AssetMetrics] = []

        for asset, txns in by_asset.items():
            price = current_prices.get(asset, Decimal("0"))
            quantity = balances.get(asset, Decimal("0"))

            if quantity == Decimal("0"):
                continue  # activo sin balance actual

            buys, sells = self._split_buys_sells(txns)
            fifo = compute_fifo(buys, sells, eur_usd=eur_usd)

            value_usd = (quantity * price).quantize(PRICE_PRECISION, ROUND_HALF_UP)
            total_value += value_usd

            cost_basis = fifo.cost_basis
            pnl_usd = (value_usd - cost_basis).quantize(PRICE_PRECISION, ROUND_HALF_UP)
            pnl_pct = (
                (pnl_usd / cost_basis * Decimal("100")).quantize(PCT_PRECISION, ROUND_HALF_UP)
                if cost_basis > Decimal("0")
                else Decimal("0")
            )
            avg_buy_price_usd = (
                (cost_basis / quantity).quantize(PRICE_PRECISION, ROUND_HALF_UP)
                if quantity > Decimal("0")
                else Decimal("0")
            )
            avg_buy_price_eur = (
                (fifo.cost_basis_eur / quantity).quantize(PRICE_PRECISION, ROUND_HALF_UP)
                if quantity > Decimal("0")
                else Decimal("0")
            )

            metrics.append(
                AssetMetrics(
                    asset=asset,
                    quantity=quantity,
                    value_usd=value_usd,
                    portfolio_pct=Decimal("0"),  # se rellena abajo
                    avg_buy_price_usd=avg_buy_price_usd,
                    avg_buy_price_eur=avg_buy_price_eur,
                    cost_basis_usd=cost_basis,
                    cost_basis_eur=fifo.cost_basis_eur,
                    pnl_usd=pnl_usd,
                    pnl_pct=pnl_pct,
                    realized_pnl_usd=fifo.realized_pnl,
                )
            )

        # Calcular portfolio_pct una vez que tenemos el total
        if total_value > Decimal("0"):
            for m in metrics:
                m.portfolio_pct = (
                    m.value_usd / total_value * Decimal("100")
                ).quantize(PCT_PRECISION, ROUND_HALF_UP)

        return sorted(metrics, key=lambda m: m.value_usd, reverse=True)

    async def calculate_overview(
        self,
        current_prices: dict[str, Decimal],
    ) -> PortfolioOverview:
        """
        Resumen ejecutivo del portafolio.
        - total_value_usd: sum(quantity * precio_actual)
        - invested_usd: depósitos - retiros fiat (capital desembolsado)
        - pnl_unrealized: total_value - cost_basis FIFO
        - pnl_realized: ganancias de ventas ya cerradas (FIFO)
        - roi_pct: (total_value - invested) / invested * 100
        - irr_annual_pct: XIRR de los flujos de caja
        """
        all_txns = await self._get_transactions()
        asset_metrics = await self.calculate_asset_metrics(current_prices)

        total_value_usd = sum((m.value_usd for m in asset_metrics), Decimal("0"))
        total_cost_basis = sum((m.cost_basis_usd for m in asset_metrics), Decimal("0"))
        total_realized = sum((m.realized_pnl_usd for m in asset_metrics), Decimal("0"))
        pnl_unrealized = (total_value_usd - total_cost_basis).quantize(
            PRICE_PRECISION, ROUND_HALF_UP
        )

        invested_usd = self._compute_invested(all_txns)

        roi_pct = (
            ((total_value_usd - invested_usd) / invested_usd * Decimal("100")).quantize(
                PCT_PRECISION, ROUND_HALF_UP
            )
            if invested_usd > Decimal("0")
            else Decimal("0")
        )

        # Construir flujos de caja para XIRR
        # buy/deposit = dinero saliendo del bolsillo (negativo)
        # sell/withdrawal fiat = dinero entrando de vuelta (positivo)
        cash_flows: list[tuple[date, Decimal]] = []
        for tx in sorted(all_txns, key=lambda t: t.executed_at):
            if tx.type in ("deposit", "buy"):
                val = tx.total_value_usd or (
                    (tx.price * tx.quantity) if tx.price else Decimal("0")
                )
                if val > Decimal("0"):
                    cash_flows.append((tx.executed_at.date(), -val))  # salida de dinero
            elif tx.type in ("sell", "withdrawal") and tx.base_asset in FIAT_AND_STABLECOINS:
                val = tx.total_value_usd or (
                    (tx.price * tx.quantity) if tx.price else Decimal("0")
                )
                if val > Decimal("0"):
                    cash_flows.append((tx.executed_at.date(), val))   # entrada de dinero

        if cash_flows and total_value_usd > Decimal("0"):
            cash_flows.append((date.today(), total_value_usd))
            irr = compute_xirr(cash_flows)
        else:
            irr = None

        return PortfolioOverview(
            total_value_usd=total_value_usd,
            invested_usd=invested_usd,
            pnl_unrealized_usd=pnl_unrealized,
            pnl_realized_usd=total_realized.quantize(PRICE_PRECISION, ROUND_HALF_UP),
            roi_pct=roi_pct,
            irr_annual_pct=irr,
            assets=asset_metrics,
        )

    async def calculate_dca_analysis(
        self,
        asset: str,
        current_price: Decimal,
        eur_usd: Decimal = Decimal("1.08"),
    ) -> DCAAnalysis:
        """
        Análisis DCA para un activo:
        - VWAP acumulado y por evento
        - Sats totales acumuladas (para BTC: 1 BTC = 1e8 sats)
        - Calendario de compras con VWAP en cada punto
        - P&L vs precio promedio
        """
        txns = await self._get_transactions(asset=asset)
        buys = [t for t in txns if t.type in {"buy", "deposit"} and t.price is not None]
        sells = [t for t in txns if t.type in SELL_TYPES]

        fifo = compute_fifo(buys, sells)
        vwap = compute_vwap(buys)

        # Cantidad actual: usar balance real de Binance si está disponible,
        # si no, calcular desde transacciones (puede diferir por depósitos/comisiones)
        balances = await self._get_latest_balances()
        total_bought = sum((t.quantity for t in buys), Decimal("0"))
        total_sold = sum((t.quantity for t in sells), Decimal("0"))
        current_qty = balances.get(asset, total_bought - total_sold)

        cost_basis = fifo.cost_basis
        value_usd = (current_qty * current_price).quantize(PRICE_PRECISION, ROUND_HALF_UP)
        pnl_usd = (value_usd - cost_basis).quantize(PRICE_PRECISION, ROUND_HALF_UP)
        pnl_pct = (
            (pnl_usd / cost_basis * Decimal("100")).quantize(PCT_PRECISION, ROUND_HALF_UP)
            if cost_basis > Decimal("0")
            else Decimal("0")
        )

        # Construir calendario: VWAP acumulado en cada compra
        # USD: usa _usd_unit_cost() (total_value_usd/qty) → precio histórico en USD correcto.
        # EUR: para BTCEUR, tx.price ya es EUR — no necesita conversión.
        #       para BTCUSDT, usamos usd/eur_usd_actual como aproximación (el usuario
        #       pagó en USDT, no hay un "EUR pagado" exacto sin el tipo histórico).
        buy_events: list[DCABuyEvent] = []
        cum_qty = Decimal("0")
        cum_usd_cost = Decimal("0")
        cum_eur_cost = Decimal("0")

        for tx in buys:
            unit_cost_usd = _usd_unit_cost(tx)

            # Precio EUR histórico real: para BTCEUR usamos tx.price directamente,
            # para BTCUSDT convertimos con el tipo actual (mejor aproximación posible
            # sin almacenar el tipo histórico por transacción).
            if tx.quote_asset == "EUR":
                unit_cost_eur = tx.price if tx.price is not None else Decimal("0")
            else:
                unit_cost_eur = (
                    (unit_cost_usd / eur_usd).quantize(PRICE_PRECISION, ROUND_HALF_UP)
                    if eur_usd > Decimal("0")
                    else Decimal("0")
                )

            cum_qty += tx.quantity
            cum_usd_cost += unit_cost_usd * tx.quantity
            cum_eur_cost += unit_cost_eur * tx.quantity

            cum_vwap = (cum_usd_cost / cum_qty).quantize(PRICE_PRECISION, ROUND_HALF_UP) if cum_qty > Decimal("0") else Decimal("0")
            cum_vwap_eur = (cum_eur_cost / cum_qty).quantize(PRICE_PRECISION, ROUND_HALF_UP) if cum_qty > Decimal("0") else Decimal("0")

            buy_events.append(
                DCABuyEvent(
                    executed_at=tx.executed_at,
                    quantity=tx.quantity,
                    price_usd=unit_cost_usd,
                    price_eur=unit_cost_eur,
                    cumulative_quantity=cum_qty,
                    cumulative_vwap=cum_vwap,
                    cumulative_vwap_eur=cum_vwap_eur,
                )
            )

        # VWAP EUR histórico total (mismo cálculo que el acumulado final)
        vwap_eur = (cum_eur_cost / cum_qty).quantize(PRICE_PRECISION, ROUND_HALF_UP) if cum_qty > Decimal("0") else Decimal("0")

        return DCAAnalysis(
            asset=asset,
            current_price_usd=current_price,
            total_quantity=current_qty,
            vwap_usd=vwap,
            vwap_eur=vwap_eur,
            cost_basis_usd=cost_basis,
            pnl_usd=pnl_usd,
            pnl_pct=pnl_pct,
            total_events=len(buy_events),
            buy_events=buy_events,
        )

    async def calculate_performance_history(
        self,
        from_date: date,
        to_date: date,
    ) -> list[PerformancePoint]:
        """
        Serie temporal diaria de valor del portafolio.
        Prioridad:
          1. portfolio_snapshots si existen en el rango (escritos por APScheduler).
          2. Historia sintética generada desde price_history + transactions.
        """
        snapshots = await self._get_portfolio_snapshots(from_date=from_date, to_date=to_date)

        if snapshots:
            points: list[PerformancePoint] = []
            for snap in snapshots:
                pnl_usd = snap.total_value_usd - snap.invested_usd
                pnl_pct = (
                    (pnl_usd / snap.invested_usd * Decimal("100")).quantize(
                        PCT_PRECISION, ROUND_HALF_UP
                    )
                    if snap.invested_usd > Decimal("0")
                    else Decimal("0")
                )
                points.append(
                    PerformancePoint(
                        snapshot_date=snap.snapshot_date,
                        total_value_usd=snap.total_value_usd,
                        invested_usd=snap.invested_usd,
                        pnl_usd=pnl_usd.quantize(PRICE_PRECISION, ROUND_HALF_UP),
                        pnl_pct=pnl_pct,
                    )
                )
            return points

        # Sin snapshots: generar desde price_history + transacciones
        return await self._synthetic_performance_history(from_date, to_date)

    async def _synthetic_performance_history(
        self,
        from_date: date,
        to_date: date,
    ) -> list[PerformancePoint]:
        """
        Genera la serie temporal del portafolio desde price_history de BTCUSDT
        y las transacciones de la cuenta.

        Algoritmo:
        - Para cada día con precio en price_history:
            - Suma acumulada de BTC comprado/vendido hasta ese día
            - Suma acumulada de capital invertido (total_value_usd de compras)
            - valor_dia = btc_qty * close_price
        - Solo emite puntos a partir del día de la primera compra.
        """
        from datetime import timezone

        from models.price_history import PriceHistory

        from_dt = datetime.combine(from_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        to_dt = datetime.combine(to_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Precios diarios BTCUSDT en el rango
        price_q = (
            select(PriceHistory)
            .where(
                PriceHistory.symbol == "BTCUSDT",
                PriceHistory.interval == "1d",
                PriceHistory.open_at >= from_dt,
                PriceHistory.open_at <= to_dt,
            )
            .order_by(PriceHistory.open_at)
        )
        price_rows = list((await self.db.execute(price_q)).scalars().all())
        if not price_rows:
            return []

        # Todas las transacciones BTC de la cuenta hasta to_date
        tx_q = (
            select(Transaction)
            .where(
                Transaction.account_id == self.account_id,
                Transaction.base_asset == "BTC",
                Transaction.executed_at <= to_dt,
            )
            .order_by(Transaction.executed_at)
        )
        txns = list((await self.db.execute(tx_q)).scalars().all())
        if not txns:
            return []

        # Fecha de la primera transacción (solo emitir desde ese día)
        first_tx_date = txns[0].executed_at.date()

        # Acumuladores
        cum_qty = Decimal("0")
        cum_invested = Decimal("0")
        tx_idx = 0
        n_txns = len(txns)

        points: list[PerformancePoint] = []

        for ph in price_rows:
            day = ph.open_at.date()

            # Avanzar transacciones que ocurrieron en o antes de este día
            while tx_idx < n_txns and txns[tx_idx].executed_at.date() <= day:
                tx = txns[tx_idx]
                val = tx.total_value_usd or (
                    (tx.price * tx.quantity) if tx.price else Decimal("0")
                )
                if tx.type in ("buy", "deposit"):
                    cum_qty += tx.quantity
                    cum_invested += val
                elif tx.type in ("sell", "withdrawal"):
                    cum_qty -= tx.quantity
                    # No reducir cum_invested: mostramos capital total desplegado
                tx_idx += 1

            # Solo emitir puntos a partir de la primera compra y con posición positiva
            if day < first_tx_date or cum_qty <= Decimal("0"):
                continue

            value_usd = (cum_qty * ph.close).quantize(PRICE_PRECISION, ROUND_HALF_UP)
            pnl_usd = (value_usd - cum_invested).quantize(PRICE_PRECISION, ROUND_HALF_UP)
            pnl_pct = (
                (pnl_usd / cum_invested * Decimal("100")).quantize(PCT_PRECISION, ROUND_HALF_UP)
                if cum_invested > Decimal("0")
                else Decimal("0")
            )

            points.append(
                PerformancePoint(
                    snapshot_date=day,
                    total_value_usd=value_usd,
                    invested_usd=cum_invested,
                    pnl_usd=pnl_usd,
                    pnl_pct=pnl_pct,
                )
            )

        return points

    async def calculate_drawdown(self) -> DrawdownResult:
        """
        Drawdown máximo del portafolio sobre toda la historia de snapshots.
        Si no hay snapshots, usa la historia sintética completa.
        """
        snapshots = await self._get_portfolio_snapshots()
        if snapshots:
            return compute_drawdown(snapshots)

        # Drawdown desde historia sintética (todo el rango disponible)
        today = date.today()
        from datetime import date as date_cls
        synthetic = await self._synthetic_performance_history(
            from_date=date_cls(2021, 1, 1), to_date=today
        )
        if not synthetic:
            return DrawdownResult(
                max_drawdown_pct=Decimal("0"),
                peak_date=None,
                trough_date=None,
                peak_value_usd=Decimal("0"),
                trough_value_usd=Decimal("0"),
            )

        # Convertir PerformancePoint a objetos duck-typed que compute_drawdown acepta
        @dataclass
        class _Snap:
            snapshot_date: date
            total_value_usd: Decimal

        fake_snaps = [_Snap(p.snapshot_date, p.total_value_usd) for p in synthetic]
        return compute_drawdown(fake_snaps)  # type: ignore[arg-type]
