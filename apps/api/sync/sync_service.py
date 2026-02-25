"""
Servicio de sincronización incremental con la API de Binance.

Reglas:
- El scheduler es el ÚNICO proceso que escribe datos de Binance en la BD.
- Sync incremental: consultar el último timestamp/fromId en BD antes de llamar a Binance.
- Idempotente: usar ON CONFLICT DO NOTHING en base a binance_id único.
- Logging estructurado de cada sync con total de registros importados y errores.
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.account import Account
from models.balance_snapshot import BalanceSnapshot
from models.price_history import PriceHistory
from models.transaction import Transaction
from sync.binance_client import BinanceClient, BinanceAPIError

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Resultado de sincronización
# ---------------------------------------------------------------------------


@dataclass
class SyncStats:
    account_id: uuid.UUID
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    balances_saved: int = 0
    trades_saved: int = 0
    deposits_saved: int = 0
    withdrawals_saved: int = 0
    fiat_orders_saved: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total_records(self) -> int:
        return (
            self.balances_saved
            + self.trades_saved
            + self.deposits_saved
            + self.withdrawals_saved
            + self.fiat_orders_saved
        )

    @property
    def duration_seconds(self) -> float:
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0.0

    def finish(self) -> None:
        self.finished_at = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Servicio principal
# ---------------------------------------------------------------------------


class SyncService:
    """
    Ejecuta sincronización incremental de una cuenta de Binance.

    Uso:
        service = SyncService(db=session, account=account, api_key=key, api_secret=secret)
        stats = await service.sync_all()

    La decifración de API Keys se hace fuera, en la capa de seguridad,
    antes de construir este servicio (NUNCA aquí).
    """

    def __init__(
        self,
        db: AsyncSession,
        account: Account,
        api_key: str,
        api_secret: str,
    ) -> None:
        self.db = db
        self.account = account
        self.stats = SyncStats(account_id=account.id)
        self._client = BinanceClient(api_key=api_key, api_secret=api_secret)

    async def sync_all(self, symbols: list[str] | None = None) -> SyncStats:
        """
        Sincronización completa: balances + trades + depósitos + retiros + fiat.
        symbols: lista de pares a sincronizar en trades (e.g. ["BTCUSDT", "ETHUSDT"]).
                 Si es None, solo se sincronizan balances + depósitos/retiros.
        """
        log = logger.bind(account_id=str(self.account.id))
        log.info("sync.start")

        try:
            await self._set_status("syncing")

            await self._run_step("balances",        self._sync_balances())
            await self._run_step("prices",           self._sync_prices())
            if symbols:
                await self._run_step("trades",       self._sync_trades(symbols))
            await self._run_step("deposits",         self._sync_deposits())
            await self._run_step("withdrawals",      self._sync_withdrawals())
            await self._run_step("fiat_deposits",    self._sync_fiat(transaction_type=0))
            await self._run_step("fiat_withdrawals", self._sync_fiat(transaction_type=1))
            # Rellenar total_value_usd en trades EUR históricos (backfill idempotente)
            await self._run_step("enrich_usd",       self._enrich_trade_usd_values())

            await self._set_status("idle")

        except Exception as exc:
            self.stats.errors.append(str(exc))
            log.error("sync.failed", error=str(exc))
            await self._set_status("error")

        finally:
            self.stats.finish()
            await self._client.close()

        log.info(
            "sync.complete",
            total_records=self.stats.total_records,
            duration_seconds=round(self.stats.duration_seconds, 2),
            errors=len(self.stats.errors),
        )
        return self.stats

    async def _run_step(self, name: str, coro) -> None:
        """Ejecuta un paso de sync capturando errores para no abortar el resto."""
        try:
            await coro
        except BinanceAPIError as exc:
            msg = f"{name}: {exc}"
            self.stats.errors.append(msg)
            logger.warning("sync.step_error", step=name, error=msg)
        except Exception as exc:
            msg = f"{name}: {exc}"
            self.stats.errors.append(msg)
            logger.error("sync.step_unexpected_error", step=name, error=msg)

    # -----------------------------------------------------------------------
    # Balances
    # -----------------------------------------------------------------------

    # Activos que nos interesan: BTC + saldos líquidos (stablecoins y fiat)
    _TRACKED_ASSETS: frozenset[str] = frozenset(
        {"BTC", "USDT", "USDC", "BUSD", "FDUSD", "EUR", "USD"}
    )

    async def _sync_balances(self) -> None:
        """Snapshot de balances BTC del momento actual."""
        data = await self._client.get_account()
        now = datetime.now(timezone.utc)
        count = 0

        for raw in data.get("balances", []):
            asset = raw["asset"]
            if asset not in self._TRACKED_ASSETS:
                continue

            free = Decimal(raw["free"])
            locked = Decimal(raw["locked"])
            if free == 0 and locked == 0:
                continue

            self.db.add(
                BalanceSnapshot(
                    account_id=self.account.id,
                    asset=asset,
                    free=free,
                    locked=locked,
                    snapshot_at=now,
                    value_usd=None,  # se enriquece en Fase 2
                )
            )
            count += 1

        await self.db.commit()
        self.stats.balances_saved += count
        logger.info("sync.balances_done", count=count)

    # -----------------------------------------------------------------------
    # Trades
    # -----------------------------------------------------------------------

    # Inicio del historial: 2021-01-01 00:00:00 UTC
    _HISTORY_START_MS: int = 1_609_459_200_000

    async def _sync_trades(self, symbols: list[str]) -> None:
        """
        Sync de trades por símbolo.
        - Sin trades en BD: descarga todo desde _HISTORY_START_MS.
        - Con trades en BD pero gap anterior a _HISTORY_START_MS: backfill del gap primero.
        - Siempre termina con sync incremental por fromId para capturar trades nuevos.
        """
        total = 0
        for symbol in symbols:
            last_id = await self._get_last_trade_id(symbol)
            count = 0

            if last_id is None:
                # Primera sincronización: descargar todo el historial completo
                logger.info("sync.trades_initial", symbol=symbol)
                async for batch in self._client.get_all_trades_by_time(
                    symbol, start_time_ms=self._HISTORY_START_MS
                ):
                    rows = [self._map_trade(t, symbol) for t in batch]
                    count += await self._upsert_transactions(rows)
            else:
                # Comprobar si falta historial anterior al primer trade conocido
                first_dt = await self._get_first_trade_datetime(symbol)
                if first_dt is not None:
                    first_ms = int(first_dt.timestamp() * 1000)
                    if first_ms > self._HISTORY_START_MS:
                        logger.info(
                            "sync.trades_backfill",
                            symbol=symbol,
                            from_ms=self._HISTORY_START_MS,
                            to_ms=first_ms,
                        )
                        async for batch in self._client.get_all_trades_by_time(
                            symbol, start_time_ms=self._HISTORY_START_MS
                        ):
                            # Solo trades estrictamente anteriores al primero ya almacenado
                            pre_batch = [t for t in batch if int(t["time"]) < first_ms]
                            if pre_batch:
                                rows = [self._map_trade(t, symbol) for t in pre_batch]
                                count += await self._upsert_transactions(rows)
                            # Parar al alcanzar el historial ya conocido
                            if int(batch[-1]["time"]) >= first_ms:
                                break

                # Sync incremental: trades nuevos desde el último ID conocido
                logger.info("sync.trades_incremental", symbol=symbol, from_id=last_id)
                async for batch in self._client.get_all_trades(symbol, from_id=last_id):
                    rows = [self._map_trade(t, symbol) for t in batch]
                    count += await self._upsert_transactions(rows)

            total += count
            logger.info("sync.trades_symbol_done", symbol=symbol, count=count)

        self.stats.trades_saved += total

    async def _get_last_trade_id(self, symbol: str) -> int | None:
        """
        Devuelve el último binance_id numérico de trades del par, o None.
        Usa el par completo (e.g. 'BTCUSDT') almacenado en raw_data,
        no el base_asset parseado, para evitar colisiones entre pares.
        binance_id es VARCHAR pero los IDs de trades son numéricos: se ordena MAX().
        """
        result = await self.db.execute(
            select(func.max(Transaction.binance_id)).where(
                Transaction.account_id == self.account.id,
                Transaction.type.in_(["buy", "sell"]),
                # Filtrar por par completo usando el campo raw_data
                Transaction.raw_data["symbol"].as_string() == symbol,
            )
        )
        last = result.scalar_one_or_none()
        return int(last) + 1 if last else None

    async def _get_first_trade_datetime(self, symbol: str) -> datetime | None:
        """
        Devuelve el datetime del trade más antiguo del par, o None.
        Se usa para detectar si falta historial anterior a _HISTORY_START_MS.
        """
        result = await self.db.execute(
            select(func.min(Transaction.executed_at)).where(
                Transaction.account_id == self.account.id,
                Transaction.type.in_(["buy", "sell"]),
                Transaction.raw_data["symbol"].as_string() == symbol,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _parse_symbol(symbol: str) -> tuple[str, str]:
        """
        Parsea un par de Binance en (base_asset, quote_asset).
        e.g. BTCUSDT → ("BTC", "USDT"), ETHBTC → ("ETH", "BTC")
        La API /api/v3/myTrades no devuelve baseAsset/quoteAsset en el payload.
        """
        for quote in ("USDT", "BUSD", "FDUSD", "BTC", "ETH", "BNB", "EUR", "USD"):
            if symbol.endswith(quote) and len(symbol) > len(quote):
                return symbol[: -len(quote)], quote
        return symbol, "USDT"

    # Pares cuya moneda de cotización ya es USD o equivalente
    _USD_QUOTE_ASSETS: frozenset[str] = frozenset({"USDT", "BUSD", "FDUSD", "USD"})

    def _map_trade(self, raw: dict, symbol: str) -> dict:
        """Convierte un trade de la API al formato de la tabla transactions."""
        qty = Decimal(raw["qty"])
        price = Decimal(raw["price"])
        is_buy = raw["isBuyer"]

        # Binance /api/v3/myTrades no incluye baseAsset/quoteAsset — parsear del symbol
        sym = raw.get("symbol", symbol)
        base_asset, quote_asset = self._parse_symbol(sym)

        # Para pares USD/stablecoin, total_value_usd es inmediato (price ya en USD).
        # Para pares EUR, se rellena en _enrich_trade_usd_values() usando EURUSDT histórico.
        if quote_asset in self._USD_QUOTE_ASSETS:
            total_value_usd = (price * qty).quantize(Decimal("0.00000001"))
        else:
            total_value_usd = None

        return {
            "id": uuid.uuid4(),
            "account_id": self.account.id,
            "binance_id": str(raw["id"]),
            "type": "buy" if is_buy else "sell",
            "base_asset": base_asset,
            "quote_asset": quote_asset,
            "quantity": qty,
            "price": price,
            "total_value_usd": total_value_usd,
            "fee_asset": raw.get("commissionAsset"),
            "fee_amount": Decimal(raw["commission"]) if raw.get("commission") else None,
            "executed_at": datetime.fromtimestamp(raw["time"] / 1000, tz=timezone.utc),
            "raw_data": raw,
        }

    # -----------------------------------------------------------------------
    # Depósitos de cripto
    # -----------------------------------------------------------------------

    async def _sync_deposits(self) -> None:
        """Sync de depósitos desde _HISTORY_START_MS. ON CONFLICT DO NOTHING garantiza idempotencia."""
        total = 0

        async for batch in self._client.get_all_deposits(since_ms=self._HISTORY_START_MS):
            rows = [
                self._map_deposit(d) for d in batch
                if d.get("coin") in self._TRACKED_ASSETS
            ]
            total += await self._upsert_transactions(rows)

        await self.db.commit()
        self.stats.deposits_saved += total
        logger.info("sync.deposits_done", count=total)

    def _map_deposit(self, raw: dict) -> dict:
        return {
            "id": uuid.uuid4(),
            "account_id": self.account.id,
            "binance_id": raw.get("id") or raw.get("txId", str(uuid.uuid4())),
            "type": "deposit",
            "base_asset": raw["coin"],
            "quote_asset": None,
            "quantity": Decimal(str(raw["amount"])),
            "price": None,
            "total_value_usd": None,
            "fee_asset": None,
            "fee_amount": None,
            "executed_at": datetime.fromtimestamp(raw["insertTime"] / 1000, tz=timezone.utc),
            "raw_data": raw,
        }

    # -----------------------------------------------------------------------
    # Retiros de cripto
    # -----------------------------------------------------------------------

    async def _sync_withdrawals(self) -> None:
        """Sync de retiros desde _HISTORY_START_MS. ON CONFLICT DO NOTHING garantiza idempotencia."""
        total = 0

        async for batch in self._client.get_all_withdrawals(since_ms=self._HISTORY_START_MS):
            rows = [
                self._map_withdrawal(w) for w in batch
                if w.get("coin") in self._TRACKED_ASSETS
            ]
            total += await self._upsert_transactions(rows)

        await self.db.commit()
        self.stats.withdrawals_saved += total
        logger.info("sync.withdrawals_done", count=total)

    def _map_withdrawal(self, raw: dict) -> dict:
        return {
            "id": uuid.uuid4(),
            "account_id": self.account.id,
            "binance_id": raw.get("id", str(uuid.uuid4())),
            "type": "withdrawal",
            "base_asset": raw["coin"],
            "quote_asset": None,
            "quantity": Decimal(str(raw["amount"])),
            "price": None,
            "total_value_usd": None,
            "fee_asset": raw["coin"],
            "fee_amount": Decimal(str(raw.get("transactionFee", "0"))),
            "executed_at": datetime.fromisoformat(raw["applyTime"].replace("Z", "+00:00")),
            "raw_data": raw,
        }

    # -----------------------------------------------------------------------
    # Fiat (depósitos y retiros)
    # -----------------------------------------------------------------------

    async def _sync_fiat(self, transaction_type: int) -> None:
        """
        Sync de órdenes fiat (0=depósito, 1=retiro) con paginación por ventanas de 90 días.

        IMPORTANTE: Requiere el permiso "Enable Fiat" en el API Key de Binance.
        Si el API Key no tiene ese permiso, Binance devuelve -2015 (Invalid API-key)
        y este step se omite con un warning en el log.
        """
        tx_type = "deposit" if transaction_type == 0 else "withdrawal"
        total = 0

        try:
            async for batch in self._client.get_all_fiat_orders(
                transaction_type, since_ms=self._HISTORY_START_MS
            ):
                rows = [self._map_fiat_order(item, tx_type) for item in batch]
                total += await self._upsert_transactions(rows)
        except BinanceAPIError as exc:
            # -2015 = API-key sin permiso fiat; -1002 = no autorizado
            if exc.code in (-2015, -1002, -2014):
                logger.warning(
                    "sync.fiat_permission_missing",
                    transaction_type=transaction_type,
                    error_code=exc.code,
                    hint=(
                        "El API Key necesita el permiso 'Enable Fiat' en Binance "
                        "para importar el historial de transferencias bancarias."
                    ),
                )
                return
            raise

        await self.db.commit()
        self.stats.fiat_orders_saved += total
        logger.info("sync.fiat_done", transaction_type=transaction_type, count=total)

    def _map_fiat_order(self, raw: dict, tx_type: str) -> dict:
        return {
            "id": uuid.uuid4(),
            "account_id": self.account.id,
            "binance_id": raw.get("orderNo", str(uuid.uuid4())),
            "type": tx_type,
            "base_asset": raw.get("fiatCurrency", "EUR"),
            "quote_asset": None,
            "quantity": Decimal(str(raw.get("amount", "0"))),
            "price": None,
            "total_value_usd": None,
            "fee_asset": raw.get("fiatCurrency"),
            "fee_amount": Decimal(str(raw.get("totalFee", "0"))),
            # createTime puede ser epoch-ms (int) o string ISO según el endpoint
            "executed_at": (
                datetime.fromtimestamp(raw["createTime"] / 1000, tz=timezone.utc)
                if isinstance(raw["createTime"], (int, float))
                else datetime.fromisoformat(str(raw["createTime"]).replace("Z", "+00:00"))
            ),
            "raw_data": raw,
        }

    # -----------------------------------------------------------------------
    # Precios históricos BTC
    # -----------------------------------------------------------------------

    async def _sync_prices(self) -> None:
        """
        Descarga velas diarias de BTCUSDT y EURUSDT desde _HISTORY_START_MS hasta hoy,
        paginando en lotes de 1000. ON CONFLICT DO NOTHING garantiza idempotencia.
        Cubre el historial completo necesario para enriquecer trades EUR históricos.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert_ph

        price_symbols = ["BTCUSDT", "EURUSDT"]
        total = 0

        for sym in price_symbols:
            sym_count = 0
            try:
                async for batch in self._client.get_all_klines(
                    sym, "1d", start_time_ms=self._HISTORY_START_MS
                ):
                    rows = [
                        {
                            "symbol":   sym,
                            "interval": "1d",
                            "open_at":  datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                            "open":     Decimal(str(k[1])),
                            "high":     Decimal(str(k[2])),
                            "low":      Decimal(str(k[3])),
                            "close":    Decimal(str(k[4])),
                            "volume":   Decimal(str(k[5])),
                        }
                        for k in batch
                    ]
                    stmt = pg_insert_ph(PriceHistory).values(rows)
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=["symbol", "interval", "open_at"]
                    )
                    await self.db.execute(stmt)
                    await self.db.commit()
                    sym_count += len(rows)
            except Exception as exc:
                logger.warning("sync.prices_symbol_error", symbol=sym, error=str(exc))
                continue

            total += sym_count
            logger.info("sync.prices_symbol_done", symbol=sym, count=sym_count)

        logger.info("sync.prices_done", count=total)

    # -----------------------------------------------------------------------
    # Enriquecimiento: total_value_usd para trades históricos
    # -----------------------------------------------------------------------

    async def _enrich_trade_usd_values(self) -> None:
        """
        Rellena total_value_usd en transacciones que aún no lo tienen:
        - Pares USD/stablecoin: total_value_usd = price * quantity
        - Pares EUR: total_value_usd = price * quantity * EURUSDT_close del día

        Usa un UPDATE bulk para eficiencia. Es idempotente: solo toca filas
        con total_value_usd IS NULL.
        """
        from sqlalchemy import text

        # 1. Pares USDT/BUSD/FDUSD/USD — conversión directa
        await self.db.execute(
            text("""
                UPDATE transactions
                SET total_value_usd = ROUND((price * quantity)::numeric, 8)
                WHERE account_id  = :account_id
                  AND total_value_usd IS NULL
                  AND quote_asset IN ('USDT', 'BUSD', 'FDUSD', 'USD')
                  AND price IS NOT NULL
            """),
            {"account_id": self.account.id},
        )

        # 2. Pares EUR — multiplicar por tipo de cambio EURUSDT del día
        await self.db.execute(
            text("""
                UPDATE transactions t
                SET total_value_usd = ROUND(
                    (t.price * t.quantity * ph.close)::numeric, 8
                )
                FROM price_history ph
                WHERE t.account_id     = :account_id
                  AND t.total_value_usd IS NULL
                  AND t.quote_asset    = 'EUR'
                  AND t.price          IS NOT NULL
                  AND ph.symbol        = 'EURUSDT'
                  AND ph.interval      = '1d'
                  AND ph.open_at::date = t.executed_at::date
            """),
            {"account_id": self.account.id},
        )

        await self.db.commit()
        logger.info("sync.enrich_usd_done", account_id=str(self.account.id))

    # -----------------------------------------------------------------------
    # Helpers de base de datos
    # -----------------------------------------------------------------------

    async def _upsert_transactions(self, rows: list[dict]) -> int:
        """
        Inserta transacciones ignorando conflictos en binance_id (idempotente).
        Devuelve el número de filas nuevas insertadas.
        """
        if not rows:
            return 0

        stmt = pg_insert(Transaction).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["binance_id"])
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount or 0

    async def _set_status(self, status: str) -> None:
        self.account.sync_status = status
        self.account.last_sync_at = datetime.now(timezone.utc)
        await self.db.commit()
