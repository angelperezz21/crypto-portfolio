---
name: binance-client
description: >
  Guía para implementar el cliente de la API de Binance. Usar cuando se trabaje
  en apps/api/sync/, cuando se implementen nuevos endpoints de Binance, o cuando
  haya errores de rate limit, paginación o autenticación HMAC.
---

# Binance API Client

## Autenticación
Todos los endpoints privados requieren firma HMAC-SHA256:
- Parámetros: timestamp + recvWindow
- Firma: HMAC-SHA256(query_string, api_secret)
- Header: X-MBX-APIKEY: {api_key}

## Rate Limiting
- Respetar X-MBX-USED-WEIGHT-1M en cada respuesta
- Si usado_weight > 1100 (de 1200 límite), pausar hasta el siguiente minuto
- Backoff exponencial en errores 429 y 418
- Leer Retry-After header cuando esté presente

## Endpoints con paginación especial
- /api/v3/myTrades: máx 1000 por request, iterar por fromId
- /sapi/v1/capital/deposit/hisrec: iterar por ventanas de tiempo de 90 días
- /sapi/v1/fiat/orders: parámetro page + rows (máx 500)

## Sincronización incremental
Siempre consultar el último timestamp en BD antes de llamar a Binance.
Guardar fromId o endTime del último registro para la siguiente sync.