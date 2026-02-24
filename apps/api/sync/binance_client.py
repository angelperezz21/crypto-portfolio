"""
Cliente HTTP para la API REST de Binance.

Reglas (skill binance-client):
- Autenticación HMAC-SHA256 en todos los endpoints privados
- Respetar X-MBX-USED-WEIGHT-1M; pausar si > 1100 (límite 1200)
- Backoff exponencial en 429/418, leer Retry-After header
- Paginación: myTrades por fromId, deposits/withdrawals por ventana 90d, fiat por page
"""

import asyncio
import hashlib
import hmac
import logging
import time
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog

logger = structlog.get_logger(__name__)

WEIGHT_LIMIT: int = 1200
WEIGHT_PAUSE_THRESHOLD: int = 1100  # pausar antes de llegar al límite
_90_DAYS_MS: int = 90 * 24 * 60 * 60 * 1000


# ---------------------------------------------------------------------------
# Excepciones
# ---------------------------------------------------------------------------


class BinanceAPIError(Exception):
    def __init__(self, status_code: int, code: int, msg: str) -> None:
        self.status_code = status_code
        self.code = code
        self.msg = msg
        super().__init__(f"Binance error {code}: {msg} (HTTP {status_code})")


class BinanceRateLimitError(BinanceAPIError):
    def __init__(self, status_code: int, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(status_code, -1003, f"Rate limit exceeded, retry after {retry_after}s")


class BinanceAuthError(BinanceAPIError):
    pass


# ---------------------------------------------------------------------------
# Rate limit manager
# ---------------------------------------------------------------------------


class RateLimitManager:
    """
    Rastrea X-MBX-USED-WEIGHT-1M de cada respuesta.
    Si el peso acumulado supera el umbral, pausa hasta el siguiente minuto.
    """

    def __init__(self) -> None:
        self._used_weight: int = 0

    def update(self, headers: httpx.Headers) -> None:
        raw = headers.get("X-MBX-USED-WEIGHT-1M")
        if raw:
            self._used_weight = int(raw)
            logger.debug("rate_limit.weight", used=self._used_weight, limit=WEIGHT_LIMIT)

    async def check(self) -> None:
        """Bloquea si estamos cerca del límite, esperando al siguiente minuto."""
        if self._used_weight >= WEIGHT_PAUSE_THRESHOLD:
            now = time.time()
            seconds_into_minute = now % 60
            wait = 60.0 - seconds_into_minute + 1.0  # +1s de margen
            logger.warning(
                "rate_limit.pause",
                used_weight=self._used_weight,
                threshold=WEIGHT_PAUSE_THRESHOLD,
                wait_seconds=round(wait, 1),
            )
            await asyncio.sleep(wait)
            self._used_weight = 0


# ---------------------------------------------------------------------------
# Cliente principal
# ---------------------------------------------------------------------------


class BinanceClient:
    """
    Cliente asíncrono para la API REST de Binance.

    Uso:
        async with BinanceClient(api_key, api_secret) as client:
            balances = await client.get_account()

    El http_client es inyectable para facilitar tests unitarios.
    NUNCA loguear api_key ni api_secret.
    """

    MAX_RETRIES: int = 3
    BASE_BACKOFF: float = 2.0  # segundos

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.binance.com",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        # Las credenciales se guardan en atributos privados y NUNCA se loguean
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._rate_limit = RateLimitManager()
        self._client = http_client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(30.0),
            headers={"X-MBX-APIKEY": self._api_key},
        )

    async def __aenter__(self) -> "BinanceClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    # -----------------------------------------------------------------------
    # Firma HMAC-SHA256
    # -----------------------------------------------------------------------

    def _sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Añade timestamp, recvWindow y firma HMAC-SHA256 a los parámetros.
        Devuelve un nuevo dict para evitar mutaciones inesperadas.
        """
        signed: dict[str, Any] = {
            **params,
            "timestamp": int(time.time() * 1000),
            "recvWindow": 5000,
        }
        query_string = urlencode(signed)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        signed["signature"] = signature
        return signed

    # -----------------------------------------------------------------------
    # Request base con retry y rate limit
    # -----------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        signed: bool = True,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """
        Ejecuta una petición HTTP con:
        - Firma opcional (endpoints privados)
        - Comprobación de rate limit antes de enviar
        - Retry con backoff exponencial en 429/418 y errores de red
        """
        request_params = dict(params or {})
        if signed:
            request_params = self._sign(request_params)

        last_exc: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            await self._rate_limit.check()

            try:
                response = await self._client.request(method, path, params=request_params)
                self._rate_limit.update(response.headers)

                # Rate limit superado — Binance devuelve 429 o 418 (ban)
                if response.status_code in (429, 418):
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        "binance.rate_limit_hit",
                        status=response.status_code,
                        retry_after=retry_after,
                        attempt=attempt,
                        path=path,
                    )
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(retry_after)
                        # Re-firmar con nuevo timestamp tras la espera
                        if signed:
                            request_params = self._sign(dict(params or {}))
                        continue
                    raise BinanceRateLimitError(response.status_code, retry_after)

                # Error de autenticación
                if response.status_code == 401:
                    data = response.json()
                    raise BinanceAuthError(401, data.get("code", -2014), data.get("msg", "Auth error"))

                # Otros errores HTTP
                if response.status_code >= 400:
                    data = response.json()
                    raise BinanceAPIError(
                        response.status_code,
                        data.get("code", -1),
                        data.get("msg", "Unknown error"),
                    )

                return response.json()

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                backoff = self.BASE_BACKOFF ** (attempt + 1)
                logger.warning(
                    "binance.network_error",
                    path=path,
                    attempt=attempt,
                    backoff=backoff,
                    error=str(exc),
                )
                last_exc = exc
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(backoff)

        raise last_exc or RuntimeError(f"Max retries exceeded for {path}")

    # -----------------------------------------------------------------------
    # Endpoints públicos
    # -----------------------------------------------------------------------

    async def get_ticker_price(self, symbol: str) -> dict:
        """GET /api/v3/ticker/price — precio actual de un par."""
        return await self._request("GET", "/api/v3/ticker/price", signed=False, params={"symbol": symbol})

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
    ) -> list[list]:
        """
        GET /api/v3/klines — OHLCV histórico. Endpoint público, sin firma.
        interval: "1d" | "1w" | "1M"
        """
        params: dict[str, Any] = {"symbol": symbol, "interval": interval, "limit": limit}
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        return await self._request("GET", "/api/v3/klines", signed=False, params=params)

    # -----------------------------------------------------------------------
    # Endpoints privados — balances y trades
    # -----------------------------------------------------------------------

    async def get_account(self) -> dict:
        """
        GET /api/v3/account — balances actuales de todos los activos.
        Requiere autenticación HMAC.
        """
        return await self._request("GET", "/api/v3/account")

    async def get_trades(
        self,
        symbol: str,
        from_id: int | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """
        GET /api/v3/myTrades — trades para un par.
        Máximo 1000 por request. Paginar por fromId o ventana startTime/endTime.
        Nota: fromId tiene prioridad y descarta startTime/endTime (API de Binance).
        """
        params: dict[str, Any] = {"symbol": symbol, "limit": limit}
        if from_id is not None:
            params["fromId"] = from_id
        else:
            if start_time is not None:
                params["startTime"] = start_time
            if end_time is not None:
                params["endTime"] = end_time
        return await self._request("GET", "/api/v3/myTrades", params=params)

    async def get_all_trades(
        self,
        symbol: str,
        from_id: int | None = None,
    ) -> AsyncIterator[list[dict]]:
        """
        Paginación incremental por fromId. Usar para syncs posteriores al primero.
        Yield: lotes de hasta 1000 trades.
        """
        current_from_id = from_id
        while True:
            batch = await self.get_trades(symbol, from_id=current_from_id)
            if not batch:
                break
            yield batch
            if len(batch) < 1000:
                break
            current_from_id = int(batch[-1]["id"]) + 1

    async def get_all_trades_by_time(
        self,
        symbol: str,
        start_time_ms: int = 0,
    ) -> AsyncIterator[list[dict]]:
        """
        Descarga todo el historial de trades desde start_time_ms.

        Usa SOLO startTime (sin endTime) para evitar el límite de 24 h de la API
        de Binance (-1127).  Pagina avanzando el startTime al timestamp del último
        trade + 1 ms hasta recibir un lote incompleto (< 1000).
        """
        current_start = start_time_ms
        while True:
            batch = await self.get_trades(symbol, start_time=current_start)
            if not batch:
                break
            yield batch
            if len(batch) < 1000:
                break
            # Avanzar al ms siguiente al último trade del lote
            current_start = int(batch[-1]["time"]) + 1

    # -----------------------------------------------------------------------
    # Endpoints privados — depósitos y retiros de cripto
    # -----------------------------------------------------------------------

    async def get_deposits(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """GET /sapi/v1/capital/deposit/hisrec — depósitos de cripto."""
        params: dict[str, Any] = {"limit": limit}
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        return await self._request("GET", "/sapi/v1/capital/deposit/hisrec", params=params)

    async def get_all_deposits(self, since_ms: int | None = None) -> AsyncIterator[list[dict]]:
        """
        Itera depósitos en ventanas de 90 días (límite de la API).
        desde since_ms (epoch ms) hasta ahora.
        """
        now_ms = int(time.time() * 1000)
        window_start = since_ms if since_ms is not None else 0

        while window_start < now_ms:
            window_end = min(window_start + _90_DAYS_MS, now_ms)
            batch = await self.get_deposits(start_time=window_start, end_time=window_end)
            if batch:
                yield batch
            window_start = window_end + 1

    async def get_withdrawals(
        self,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000,
    ) -> list[dict]:
        """GET /sapi/v1/capital/withdraw/history — retiros de cripto."""
        params: dict[str, Any] = {"limit": limit}
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        return await self._request("GET", "/sapi/v1/capital/withdraw/history", params=params)

    async def get_all_withdrawals(self, since_ms: int | None = None) -> AsyncIterator[list[dict]]:
        """Itera retiros en ventanas de 90 días."""
        now_ms = int(time.time() * 1000)
        window_start = since_ms if since_ms is not None else 0

        while window_start < now_ms:
            window_end = min(window_start + _90_DAYS_MS, now_ms)
            batch = await self.get_withdrawals(start_time=window_start, end_time=window_end)
            if batch:
                yield batch
            window_start = window_end + 1

    # -----------------------------------------------------------------------
    # Endpoints privados — fiat
    # -----------------------------------------------------------------------

    async def get_fiat_orders(
        self,
        transaction_type: int,
        begin_time: int | None = None,
        end_time: int | None = None,
        page: int = 1,
        rows: int = 500,
    ) -> dict:
        """
        GET /sapi/v1/fiat/orders
        transaction_type: 0 = depósito fiat, 1 = retiro fiat
        beginTime/endTime: ventana máxima de 90 días.
        Paginación por page + rows (máx 500 por página).
        Requiere permiso "Enable Fiat" en el API Key.
        """
        params: dict[str, Any] = {
            "transactionType": transaction_type,
            "page": page,
            "rows": rows,
        }
        if begin_time is not None:
            params["beginTime"] = begin_time
        if end_time is not None:
            params["endTime"] = end_time
        return await self._request("GET", "/sapi/v1/fiat/orders", params=params)

    async def get_all_fiat_orders(
        self,
        transaction_type: int,
        since_ms: int | None = None,
    ) -> AsyncIterator[list[dict]]:
        """
        Itera depósitos/retiros fiat en ventanas de 90 días desde since_ms hasta ahora.
        Binance requiere beginTime/endTime para recuperar historial completo.
        Requiere permiso "Enable Fiat" en el API Key; si falta, la llamada lanza
        BinanceAPIError que el caller puede capturar.
        """
        now_ms = int(time.time() * 1000)
        window_start = since_ms if since_ms is not None else 0

        while window_start < now_ms:
            window_end = min(window_start + _90_DAYS_MS, now_ms)
            page = 1
            while True:
                result = await self.get_fiat_orders(
                    transaction_type=transaction_type,
                    begin_time=window_start,
                    end_time=window_end,
                    page=page,
                )
                data: list[dict] = result.get("data", [])
                if not data:
                    break
                yield data
                if len(data) < 500:
                    break
                page += 1
            window_start = window_end + 1
