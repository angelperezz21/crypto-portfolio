"""
Tests de los algoritmos financieros puros.
No requieren base de datos.
Todas las aserciones usan Decimal para evitar errores de precisión.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from services.portfolio_service import (
    DCABuyEvent,
    DrawdownResult,
    FIFOLot,
    FIFOResult,
    PortfolioSnapshot,
    compute_drawdown,
    compute_fifo,
    compute_vwap,
    compute_xirr,
)

# ---------------------------------------------------------------------------
# Helpers de fixtures
# ---------------------------------------------------------------------------


def make_tx(
    tx_type: str,
    quantity: str,
    price: str | None,
    executed_at: datetime | None = None,
    asset: str = "BTC",
    total_value_usd: str | None = None,
):
    """Crea un objeto Transaction mínimo para tests (no necesita SQLAlchemy)."""
    from unittest.mock import MagicMock

    tx = MagicMock()
    tx.type = tx_type
    tx.base_asset = asset
    tx.quantity = Decimal(quantity)
    tx.price = Decimal(price) if price is not None else None
    tx.executed_at = executed_at or datetime(2024, 1, 1, tzinfo=timezone.utc)
    tx.total_value_usd = Decimal(total_value_usd) if total_value_usd else None
    return tx


def make_snapshot(
    snapshot_date: date,
    total_value_usd: str,
    invested_usd: str = "10000",
):
    from unittest.mock import MagicMock

    snap = MagicMock(spec=PortfolioSnapshot)
    snap.snapshot_date = snapshot_date
    snap.total_value_usd = Decimal(total_value_usd)
    snap.invested_usd = Decimal(invested_usd)
    return snap


# ===========================================================================
# Tests: compute_fifo
# ===========================================================================


class TestComputeFifo:
    def test_single_buy_no_sell_returns_full_lot(self):
        buys = [make_tx("buy", "1.0", "50000")]
        result = compute_fifo(buys, [])

        assert len(result.remaining_lots) == 1
        assert result.remaining_lots[0].quantity == Decimal("1.0")
        assert result.remaining_lots[0].unit_cost == Decimal("50000")
        assert result.cost_basis == Decimal("50000")
        assert result.realized_pnl == Decimal("0")

    def test_sell_entire_lot_at_profit(self):
        buys = [make_tx("buy", "1.0", "40000")]
        sells = [make_tx("sell", "1.0", "50000")]
        result = compute_fifo(buys, sells)

        assert result.remaining_lots == []
        assert result.cost_basis == Decimal("0")
        assert result.realized_pnl == Decimal("10000")

    def test_sell_entire_lot_at_loss(self):
        buys = [make_tx("buy", "1.0", "60000")]
        sells = [make_tx("sell", "1.0", "50000")]
        result = compute_fifo(buys, sells)

        assert result.realized_pnl == Decimal("-10000")

    def test_fifo_consumes_oldest_lot_first(self):
        """Con dos compras a precios distintos, la venta debe consumir el lote más antiguo."""
        buys = [
            make_tx("buy", "1.0", "30000", datetime(2023, 1, 1, tzinfo=timezone.utc)),
            make_tx("buy", "1.0", "50000", datetime(2023, 6, 1, tzinfo=timezone.utc)),
        ]
        sells = [make_tx("sell", "1.0", "40000", datetime(2023, 7, 1, tzinfo=timezone.utc))]
        result = compute_fifo(buys, sells)

        # Vende el lote a 30000, gana 10000
        assert result.realized_pnl == Decimal("10000")
        # Queda el lote comprado a 50000
        assert len(result.remaining_lots) == 1
        assert result.remaining_lots[0].unit_cost == Decimal("50000")
        assert result.cost_basis == Decimal("50000")

    def test_partial_lot_consumption(self):
        """Venta parcial debe ajustar la cantidad del lot sin eliminarlo."""
        buys = [make_tx("buy", "2.0", "40000")]
        sells = [make_tx("sell", "1.0", "50000")]
        result = compute_fifo(buys, sells)

        assert len(result.remaining_lots) == 1
        assert result.remaining_lots[0].quantity == Decimal("1.0")
        assert result.remaining_lots[0].unit_cost == Decimal("40000")
        assert result.realized_pnl == Decimal("10000")
        assert result.cost_basis == Decimal("40000")  # 1.0 * 40000

    def test_multiple_buys_and_sells_fifo_order(self):
        buys = [
            make_tx("buy", "0.5", "20000", datetime(2022, 1, 1, tzinfo=timezone.utc)),
            make_tx("buy", "0.5", "40000", datetime(2023, 1, 1, tzinfo=timezone.utc)),
            make_tx("buy", "0.5", "60000", datetime(2024, 1, 1, tzinfo=timezone.utc)),
        ]
        sells = [make_tx("sell", "1.0", "50000", datetime(2024, 6, 1, tzinfo=timezone.utc))]
        result = compute_fifo(buys, sells)

        # Consume lot 20000 (0.5) → ganancia 0.5 * 30000 = 15000
        # Consume lot 40000 (0.5) → ganancia 0.5 * 10000 = 5000
        # Total realizado = 20000
        assert result.realized_pnl == Decimal("20000")
        # Queda el lot 60000 con 0.5 BTC
        assert len(result.remaining_lots) == 1
        assert result.remaining_lots[0].unit_cost == Decimal("60000")
        assert result.cost_basis == Decimal("30000")  # 0.5 * 60000

    def test_empty_inputs(self):
        result = compute_fifo([], [])
        assert result.remaining_lots == []
        assert result.cost_basis == Decimal("0")
        assert result.realized_pnl == Decimal("0")

    def test_deposit_without_price_has_zero_cost_basis(self):
        """Un depósito cripto sin precio tiene coste base 0 (regalo/airdrip)."""
        buys = [make_tx("deposit", "1.0", None)]
        result = compute_fifo(buys, [])
        assert result.cost_basis == Decimal("0")

    def test_sell_exceeding_holdings_does_not_crash(self):
        """Si se vende más de lo comprado (data gap), no debe fallar."""
        buys = [make_tx("buy", "0.5", "50000")]
        sells = [make_tx("sell", "1.0", "60000")]
        result = compute_fifo(buys, sells)

        assert result.remaining_lots == []
        # Solo puede realizar P&L sobre los 0.5 BTC disponibles
        assert result.realized_pnl == Decimal("5000")  # 0.5 * (60000 - 50000)


# ===========================================================================
# Tests: compute_vwap
# ===========================================================================


class TestComputeVwap:
    def test_single_buy(self):
        buys = [make_tx("buy", "1.0", "50000")]
        assert compute_vwap(buys) == Decimal("50000")

    def test_equal_quantities_different_prices(self):
        """Con cantidades iguales, VWAP es la media aritmética."""
        buys = [
            make_tx("buy", "1.0", "40000"),
            make_tx("buy", "1.0", "60000"),
        ]
        assert compute_vwap(buys) == Decimal("50000")

    def test_different_quantities_weights_correctly(self):
        """VWAP pondera por cantidad: compra grande a precio bajo baja el promedio."""
        buys = [
            make_tx("buy", "2.0", "30000"),  # 60000 total
            make_tx("buy", "1.0", "60000"),  # 60000 total
        ]
        # VWAP = (60000 + 60000) / 3.0 = 40000
        assert compute_vwap(buys) == Decimal("40000")

    def test_skips_transactions_without_price(self):
        buys = [
            make_tx("buy", "1.0", "50000"),
            make_tx("deposit", "0.5", None),  # sin precio, se ignora
        ]
        # Solo cuenta la compra: VWAP = 50000
        assert compute_vwap(buys) == Decimal("50000")

    def test_skips_zero_price(self):
        buys = [make_tx("staking_reward", "0.01", "0")]
        assert compute_vwap(buys) == Decimal("0")

    def test_empty_list_returns_zero(self):
        assert compute_vwap([]) == Decimal("0")

    def test_result_is_decimal_not_float(self):
        buys = [make_tx("buy", "1.0", "50000")]
        result = compute_vwap(buys)
        assert isinstance(result, Decimal), "VWAP debe ser Decimal, nunca float"

    def test_high_precision_quantities(self):
        """Verifica que la precisión no se pierde con cantidades cripto pequeñas."""
        buys = [
            make_tx("buy", "0.00000001", "50000"),  # 1 satoshi
            make_tx("buy", "0.00000001", "60000"),
        ]
        vwap = compute_vwap(buys)
        assert vwap == Decimal("55000")


# ===========================================================================
# Tests: compute_drawdown
# ===========================================================================


class TestComputeDrawdown:
    def test_monotone_rising_portfolio_zero_drawdown(self):
        snaps = [
            make_snapshot(date(2024, 1, 1), "10000"),
            make_snapshot(date(2024, 2, 1), "12000"),
            make_snapshot(date(2024, 3, 1), "15000"),
        ]
        result = compute_drawdown(snaps)
        assert result.max_drawdown_pct == Decimal("0")

    def test_simple_peak_and_trough(self):
        snaps = [
            make_snapshot(date(2024, 1, 1), "10000"),
            make_snapshot(date(2024, 2, 1), "20000"),  # pico
            make_snapshot(date(2024, 3, 1), "10000"),  # caída 50%
        ]
        result = compute_drawdown(snaps)
        assert result.max_drawdown_pct == Decimal("-50.00")
        assert result.peak_date == date(2024, 2, 1)
        assert result.trough_date == date(2024, 3, 1)
        assert result.peak_value_usd == Decimal("20000")
        assert result.trough_value_usd == Decimal("10000")

    def test_multiple_drawdowns_takes_worst(self):
        snaps = [
            make_snapshot(date(2024, 1, 1), "10000"),
            make_snapshot(date(2024, 2, 1), "15000"),  # pico 1
            make_snapshot(date(2024, 3, 1), "13000"),  # -13.33%
            make_snapshot(date(2024, 4, 1), "20000"),  # pico 2
            make_snapshot(date(2024, 5, 1), "12000"),  # -40%  ← peor
        ]
        result = compute_drawdown(snaps)
        assert result.max_drawdown_pct == Decimal("-40.00")
        assert result.peak_value_usd == Decimal("20000")
        assert result.trough_value_usd == Decimal("12000")

    def test_empty_snapshots(self):
        result = compute_drawdown([])
        assert result.max_drawdown_pct == Decimal("0")
        assert result.peak_date is None
        assert result.trough_date is None

    def test_single_snapshot_zero_drawdown(self):
        result = compute_drawdown([make_snapshot(date(2024, 1, 1), "10000")])
        assert result.max_drawdown_pct == Decimal("0")

    def test_result_uses_decimal_not_float(self):
        snaps = [
            make_snapshot(date(2024, 1, 1), "10000"),
            make_snapshot(date(2024, 2, 1), "5000"),
        ]
        result = compute_drawdown(snaps)
        assert isinstance(result.max_drawdown_pct, Decimal)


# ===========================================================================
# Tests: compute_xirr
# ===========================================================================


class TestComputeXirr:
    def test_single_cashflow_returns_none(self):
        flows = [(date(2024, 1, 1), Decimal("-10000"))]
        assert compute_xirr(flows) is None

    def test_breakeven_returns_near_zero(self):
        """Invertir 10000 y recuperar 10000 = IRR ~0%."""
        flows = [
            (date(2024, 1, 1), Decimal("-10000")),
            (date(2025, 1, 1), Decimal("10000")),
        ]
        result = compute_xirr(flows)
        assert result is not None
        # Debe ser muy cercano a 0
        assert abs(result) < Decimal("0.01")

    def test_positive_return_gives_positive_irr(self):
        """Invertir 10000, recuperar 12000 en un año → IRR ~20%."""
        flows = [
            (date(2024, 1, 1), Decimal("-10000")),
            (date(2025, 1, 1), Decimal("12000")),
        ]
        result = compute_xirr(flows)
        assert result is not None
        assert Decimal("18") < result < Decimal("22")

    def test_negative_return_gives_negative_irr(self):
        """Invertir 10000, recuperar 8000 → IRR negativa."""
        flows = [
            (date(2024, 1, 1), Decimal("-10000")),
            (date(2025, 1, 1), Decimal("8000")),
        ]
        result = compute_xirr(flows)
        assert result is not None
        assert result < Decimal("0")

    def test_result_is_decimal_not_float(self):
        flows = [
            (date(2024, 1, 1), Decimal("-10000")),
            (date(2025, 1, 1), Decimal("12000")),
        ]
        result = compute_xirr(flows)
        assert result is None or isinstance(result, Decimal)

    def test_multiple_deposits_dca(self):
        """IRR con múltiples depósitos (caso DCA típico)."""
        flows = [
            (date(2022, 1, 1), Decimal("-1000")),
            (date(2022, 7, 1), Decimal("-1000")),
            (date(2023, 1, 1), Decimal("-1000")),
            (date(2024, 1, 1), Decimal("4500")),  # valor final > suma invertida
        ]
        result = compute_xirr(flows)
        assert result is not None
        assert result > Decimal("0")  # rendimiento positivo
