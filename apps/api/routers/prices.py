"""
Router: /api/v1/prices
GET /live  → precio BTC en tiempo real en EUR y USD.

Fuentes (en orden de prioridad):
  1. CoinGecko  — free tier, sin API key, /simple/price
  2. Kraken     — fallback, par XBTEUR/XBTUSD
"""

import httpx
from fastapi import APIRouter

from core.responses import ok

router = APIRouter()

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
KRAKEN_URL    = "https://api.kraken.com/0/public/Ticker"

_TIMEOUT = httpx.Timeout(6.0)


async def _fetch_coingecko(client: httpx.AsyncClient) -> tuple[str, str] | None:
    """Devuelve (btc_eur, btc_usd) o None si falla."""
    resp = await client.get(
        COINGECKO_URL,
        params={"ids": "bitcoin", "vs_currencies": "eur,usd"},
    )
    resp.raise_for_status()
    data = resp.json()
    bitcoin = data.get("bitcoin", {})
    eur = bitcoin.get("eur")
    usd = bitcoin.get("usd")
    if eur is None or usd is None:
        return None
    return str(eur), str(usd)


async def _fetch_kraken(client: httpx.AsyncClient) -> tuple[str, str] | None:
    """Devuelve (btc_eur, btc_usd) o None si falla."""
    resp = await client.get(KRAKEN_URL, params={"pair": "XBTEUR,XBTUSD"})
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        return None
    result = data.get("result", {})
    # Kraken usa claves como "XXBTZEUR" y "XXBTZUSD"; buscamos por sufijo
    eur_key = next((k for k in result if "EUR" in k), None)
    usd_key = next((k for k in result if "USD" in k), None)
    if not eur_key or not usd_key:
        return None
    # "c" = [last_trade_price, lot_volume]
    btc_eur = result[eur_key]["c"][0]
    btc_usd = result[usd_key]["c"][0]
    return btc_eur, btc_usd


@router.get("/live")
async def get_live_prices() -> dict:
    """
    Precio BTC en tiempo real en EUR y USD.
    Intenta CoinGecko primero; si falla usa Kraken.
    Si ambos fallan devuelve null (la UI usa el precio del día anterior).
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        # 1. CoinGecko
        try:
            result = await _fetch_coingecko(client)
            if result:
                btc_eur, btc_usd = result
                return ok(
                    data={"btc_eur": btc_eur, "btc_usd": btc_usd},
                    meta={"source": "coingecko"},
                )
        except Exception:
            pass

        # 2. Kraken
        try:
            result = await _fetch_kraken(client)
            if result:
                btc_eur, btc_usd = result
                return ok(
                    data={"btc_eur": btc_eur, "btc_usd": btc_usd},
                    meta={"source": "kraken"},
                )
        except Exception:
            pass

    return ok(
        data={"btc_eur": None, "btc_usd": None},
        meta={"source": "unavailable"},
    )
