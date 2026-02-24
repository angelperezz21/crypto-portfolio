"""
Helpers para la estructura de respuesta estándar { data, error, meta }.
Todos los endpoints de la API deben usar estas funciones para garantizar
coherencia en el formato de respuesta.
"""

from typing import Any


def ok(data: Any = None, meta: dict | None = None) -> dict:
    """Respuesta exitosa."""
    return {"data": data, "error": None, "meta": meta or {}}


def err(message: str, meta: dict | None = None) -> dict:
    """Respuesta de error (para exception handlers globales)."""
    return {"data": None, "error": message, "meta": meta or {}}
