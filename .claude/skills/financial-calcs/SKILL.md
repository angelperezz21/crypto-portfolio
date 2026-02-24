---
name: financial-calcs
description: >
  Fórmulas y reglas para cálculos financieros del portafolio. Usar cuando se
  implementen o modifiquen cálculos de P&L, VWAP, IRR, ROI, drawdown o FIFO.
  Crítico: NUNCA usar float, siempre Decimal.
---

# Financial Calculations

## Regla de oro
```python
from decimal import Decimal, ROUND_HALF_UP
# MAL: precio = 0.00001234 * 1000  (float)
# BIEN: precio = Decimal("0.00001234") * Decimal("1000")
```

## VWAP (Precio promedio DCA)
suma(precio_i * cantidad_i) / suma(cantidad_i)
Solo incluir transacciones tipo BUY y CRYPTO_DEPOSIT.
Ventas reducen cantidad pero no afectan el coste medio de las unidades restantes.

## P&L No Realizado
(precio_actual * cantidad_actual) - coste_base_total
coste_base_total: calculado por FIFO sobre las unidades en posesión.

## Drawdown Máximo
Para cada día: (valor_dia - max_historico_hasta_ese_dia) / max_historico_hasta_ese_dia
Tomar el mínimo de todos los valores.

## IRR
Usar numpy_financial.irr() con flujos de caja:
- Depósitos fiat: valores negativos (salida de dinero)
- Valor actual del portafolio: valor positivo al final