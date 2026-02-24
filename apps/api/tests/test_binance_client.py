"""
Tests del cliente Binance.
No requieren base de datos ni variables de entorno.
El httpx.AsyncClient se inyecta como mock para aislar la red.
"""

import asyncio
import hashlib
import hmac
import json
import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sync.binance_client import (
    BinanceAPIError,
    BinanceAuthError,
    BinanceClient,
    BinanceRateLimitError,
    RateLimitManager,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

API_KEY = "test_api_key_abc123"
API_SECRET = "test_api_secret_xyz789"
BASE_URL = "https://api.binance.com"


def make_mock_response(
    json_body: object,
    status_code: int = 200,
    headers: dict | None = None,
) -> MagicMock:
    """Crea un MagicMock de httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.headers = httpx.Headers({"X-MBX-USED-WEIGHT-1M": "10", **(headers or {})})
    return resp


def make_client(mock_responses: list) -> tuple[BinanceClient, AsyncMock]:
    """
    Crea un BinanceClient con un http_client mockeado.
    mock_responses: lista de valores que retornará .request() en orden.
    """
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.request = AsyncMock(side_effect=mock_responses)
    mock_http.aclose = AsyncMock()
    client = BinanceClient(
        api_key=API_KEY,
        api_secret=API_SECRET,
        base_url=BASE_URL,
        http_client=mock_http,
    )
    return client, mock_http


# ---------------------------------------------------------------------------
# Tests: firma HMAC
# ---------------------------------------------------------------------------


def test_sign_adds_required_fields():
    """_sign debe añadir timestamp, recvWindow y signature."""
    client = BinanceClient(API_KEY, API_SECRET, base_url=BASE_URL, http_client=AsyncMock())
    params = {"symbol": "BTCUSDT", "limit": 1000}
    signed = client._sign(params)

    assert "timestamp" in signed
    assert "recvWindow" in signed
    assert "signature" in signed
    assert signed["recvWindow"] == 5000
    # El timestamp debe ser un entero reciente (epoch ms)
    assert isinstance(signed["timestamp"], int)
    assert signed["timestamp"] > 1_700_000_000_000


def test_sign_does_not_mutate_original():
    """_sign no debe modificar el dict original."""
    client = BinanceClient(API_KEY, API_SECRET, base_url=BASE_URL, http_client=AsyncMock())
    params = {"symbol": "BTCUSDT"}
    original_keys = set(params.keys())
    client._sign(params)
    assert set(params.keys()) == original_keys


def test_sign_hmac_is_correct():
    """La firma HMAC-SHA256 debe verificarse con la misma clave."""
    client = BinanceClient(API_KEY, API_SECRET, base_url=BASE_URL, http_client=AsyncMock())
    signed = client._sign({"symbol": "BTCUSDT", "limit": 1000})

    # Reconstruir la firma manualmente (sin el campo signature)
    from urllib.parse import urlencode
    params_without_sig = {k: v for k, v in signed.items() if k != "signature"}
    query_string = urlencode(params_without_sig)
    expected_sig = hmac.new(
        API_SECRET.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert signed["signature"] == expected_sig


# ---------------------------------------------------------------------------
# Tests: RateLimitManager
# ---------------------------------------------------------------------------


async def test_rate_limit_manager_updates_from_headers():
    manager = RateLimitManager()
    headers = httpx.Headers({"X-MBX-USED-WEIGHT-1M": "500"})
    manager.update(headers)
    assert manager._used_weight == 500


async def test_rate_limit_manager_no_header_leaves_weight_unchanged():
    manager = RateLimitManager()
    headers = httpx.Headers({})
    manager.update(headers)
    assert manager._used_weight == 0


async def test_rate_limit_check_does_not_sleep_below_threshold():
    manager = RateLimitManager()
    manager._used_weight = 500
    # No debe bloquearse
    await asyncio.wait_for(manager.check(), timeout=0.1)


async def test_rate_limit_check_sleeps_above_threshold(monkeypatch):
    """Cuando el peso supera el umbral, debe pausar."""
    manager = RateLimitManager()
    manager._used_weight = 1150  # > WEIGHT_PAUSE_THRESHOLD (1100)

    sleep_calls = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        manager._used_weight = 0  # simular reset tras espera

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    await manager.check()
    assert len(sleep_calls) == 1
    assert sleep_calls[0] > 0


# ---------------------------------------------------------------------------
# Tests: get_account
# ---------------------------------------------------------------------------


async def test_get_account_success():
    body = {
        "balances": [
            {"asset": "BTC", "free": "0.00100000", "locked": "0.00000000"},
            {"asset": "USDT", "free": "1500.00000000", "locked": "0.00000000"},
        ]
    }
    client, mock_http = make_client([make_mock_response(body)])

    result = await client.get_account()

    assert result["balances"][0]["asset"] == "BTC"
    assert result["balances"][1]["asset"] == "USDT"
    mock_http.request.assert_called_once()
    # El primer arg debe ser el método
    call_args = mock_http.request.call_args
    assert call_args[0][0] == "GET"
    assert "/api/v3/account" in call_args[0][1]


async def test_get_account_is_signed():
    """get_account es un endpoint privado: debe incluir signature en params."""
    body = {"balances": []}
    client, mock_http = make_client([make_mock_response(body)])

    await client.get_account()

    call_kwargs = mock_http.request.call_args[1]
    params = call_kwargs.get("params", {})
    assert "signature" in params
    assert "timestamp" in params


# ---------------------------------------------------------------------------
# Tests: retry en 429
# ---------------------------------------------------------------------------


async def test_request_retries_on_429_then_succeeds(monkeypatch):
    """Tras un 429, debe reintentar y tener éxito en el segundo intento."""
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    rate_limit_resp = make_mock_response(
        {"code": -1003, "msg": "Too many requests"},
        status_code=429,
        headers={"Retry-After": "1"},
    )
    success_resp = make_mock_response({"balances": []})

    client, mock_http = make_client([rate_limit_resp, success_resp])
    result = await client.get_account()

    assert result == {"balances": []}
    assert mock_http.request.call_count == 2


async def test_request_raises_after_max_retries(monkeypatch):
    """Tras MAX_RETRIES intentos con 429, debe lanzar BinanceRateLimitError."""
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    rate_limit_resp = make_mock_response(
        {"code": -1003, "msg": "Too many requests"},
        status_code=429,
        headers={"Retry-After": "1"},
    )
    client, mock_http = make_client([rate_limit_resp] * 10)

    with pytest.raises(BinanceRateLimitError) as exc_info:
        await client.get_account()

    assert exc_info.value.status_code == 429
    assert mock_http.request.call_count == BinanceClient.MAX_RETRIES


async def test_request_raises_api_error_on_4xx():
    """Errores 4xx distintos de 429/418/401 deben lanzar BinanceAPIError."""
    resp = make_mock_response(
        {"code": -1121, "msg": "Invalid symbol."},
        status_code=400,
    )
    client, _ = make_client([resp])

    with pytest.raises(BinanceAPIError) as exc_info:
        await client.get_trades("INVALIDSYMBOL")

    assert exc_info.value.code == -1121
    assert "Invalid symbol" in exc_info.value.msg


async def test_request_raises_auth_error_on_401():
    resp = make_mock_response(
        {"code": -2014, "msg": "API-key format invalid."},
        status_code=401,
    )
    client, _ = make_client([resp])

    with pytest.raises(BinanceAuthError):
        await client.get_account()


async def test_request_retries_on_network_error(monkeypatch):
    """Errores de red deben reintentarse con backoff exponencial."""
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    success_resp = make_mock_response({"balances": []})

    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.request = AsyncMock(
        side_effect=[httpx.TimeoutException("timeout"), success_resp]
    )
    mock_http.aclose = AsyncMock()

    client = BinanceClient(API_KEY, API_SECRET, base_url=BASE_URL, http_client=mock_http)
    result = await client.get_account()

    assert result == {"balances": []}
    assert mock_http.request.call_count == 2


# ---------------------------------------------------------------------------
# Tests: get_trades (paginación por fromId)
# ---------------------------------------------------------------------------


async def test_get_trades_returns_list():
    trades = [{"id": 1, "symbol": "BTCUSDT", "price": "50000", "qty": "0.001",
               "commission": "0.0001", "commissionAsset": "BTC",
               "time": 1700000000000, "isBuyer": True}]
    client, _ = make_client([make_mock_response(trades)])

    result = await client.get_trades("BTCUSDT")
    assert len(result) == 1
    assert result[0]["id"] == 1


async def test_get_all_trades_paginates_by_from_id():
    """get_all_trades debe iterar usando el id del último trade + 1."""
    # Primera página: 2 trades (< 1000, fin)
    page1 = [
        {"id": 100, "symbol": "BTCUSDT", "price": "50000", "qty": "0.001",
         "commission": "0", "commissionAsset": "BTC", "time": 1700000000000, "isBuyer": True},
        {"id": 101, "symbol": "BTCUSDT", "price": "51000", "qty": "0.002",
         "commission": "0", "commissionAsset": "BTC", "time": 1700000001000, "isBuyer": False},
    ]
    client, mock_http = make_client([make_mock_response(page1)])

    batches = []
    async for batch in client.get_all_trades("BTCUSDT", from_id=100):
        batches.append(batch)

    assert len(batches) == 1
    assert len(batches[0]) == 2
    mock_http.request.assert_called_once()


async def test_get_all_trades_stops_when_empty():
    """Si la primera página está vacía, no debe haber más peticiones."""
    client, mock_http = make_client([make_mock_response([])])

    batches = []
    async for batch in client.get_all_trades("BTCUSDT"):
        batches.append(batch)

    assert batches == []
    mock_http.request.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: get_deposits (ventanas de 90 días)
# ---------------------------------------------------------------------------


async def test_get_deposits_with_time_range():
    deposits = [{"id": "dep1", "coin": "BTC", "amount": "0.5",
                 "insertTime": 1700000000000, "status": 1}]
    client, _ = make_client([make_mock_response(deposits)])

    result = await client.get_deposits(start_time=1699999000000, end_time=1700000000000)
    assert result[0]["id"] == "dep1"


async def test_get_all_deposits_uses_90_day_windows():
    """get_all_deposits debe partir el rango temporal en ventanas de 90 días."""
    # Simulamos un since_ms hace 100 días → necesita 2 ventanas
    now_ms = int(time.time() * 1000)
    since_ms = now_ms - (100 * 24 * 60 * 60 * 1000)

    window1 = [{"id": "d1", "coin": "BTC", "amount": "0.1", "insertTime": since_ms + 1000, "status": 1}]
    window2 = [{"id": "d2", "coin": "ETH", "amount": "1.0", "insertTime": now_ms - 1000, "status": 1}]

    client, mock_http = make_client([
        make_mock_response(window1),
        make_mock_response(window2),
    ])

    results = []
    async for batch in client.get_all_deposits(since_ms=since_ms):
        results.extend(batch)

    assert len(results) == 2
    assert mock_http.request.call_count == 2


async def test_get_all_deposits_skips_empty_windows():
    """Ventanas sin datos no deben generar yield."""
    now_ms = int(time.time() * 1000)
    since_ms = now_ms - (100 * 24 * 60 * 60 * 1000)

    client, mock_http = make_client([
        make_mock_response([]),   # ventana 1: vacía
        make_mock_response([]),   # ventana 2: vacía
    ])

    results = []
    async for batch in client.get_all_deposits(since_ms=since_ms):
        results.extend(batch)

    assert results == []


# ---------------------------------------------------------------------------
# Tests: get_fiat_orders (paginación por page)
# ---------------------------------------------------------------------------


async def test_get_all_fiat_orders_paginates():
    """Si la primera página tiene 500 registros, debe pedir la siguiente página."""
    page1_data = [{"orderNo": str(i), "fiatCurrency": "EUR", "amount": "100",
                   "totalFee": "1", "createTime": "2024-01-01T00:00:00Z"} for i in range(500)]
    page2_data = [{"orderNo": "999", "fiatCurrency": "EUR", "amount": "200",
                   "totalFee": "2", "createTime": "2024-02-01T00:00:00Z"}]

    client, mock_http = make_client([
        make_mock_response({"data": page1_data}),
        make_mock_response({"data": page2_data}),
    ])

    results = []
    async for batch in client.get_all_fiat_orders(transaction_type=0):
        results.extend(batch)

    assert len(results) == 501
    assert mock_http.request.call_count == 2


async def test_get_all_fiat_orders_stops_on_empty():
    client, mock_http = make_client([make_mock_response({"data": []})])

    results = []
    async for batch in client.get_all_fiat_orders(transaction_type=1):
        results.extend(batch)

    assert results == []
    mock_http.request.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: get_klines (endpoint público, sin firma)
# ---------------------------------------------------------------------------


async def test_get_klines_success():
    klines = [[1700000000000, "50000", "51000", "49000", "50500", "100.5"]]
    client, _ = make_client([make_mock_response(klines)])

    result = await client.get_klines("BTCUSDT", "1d")
    assert result[0][1] == "50000"  # open price


async def test_get_klines_is_not_signed():
    """get_klines es público: NO debe incluir signature en los params."""
    klines = [[1700000000000, "50000", "51000", "49000", "50500", "100"]]
    client, mock_http = make_client([make_mock_response(klines)])

    await client.get_klines("BTCUSDT", "1d")

    call_kwargs = mock_http.request.call_args[1]
    params = call_kwargs.get("params", {})
    assert "signature" not in params
    assert "timestamp" not in params


# ---------------------------------------------------------------------------
# Tests: context manager
# ---------------------------------------------------------------------------


async def test_client_closes_on_context_exit():
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.aclose = AsyncMock()

    async with BinanceClient(API_KEY, API_SECRET, base_url=BASE_URL, http_client=mock_http):
        pass

    mock_http.aclose.assert_called_once()
