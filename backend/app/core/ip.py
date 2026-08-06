"""Utilidad compartida para resolver la IP de origen de una petición."""

from __future__ import annotations

import ipaddress


def ip_valida(host: str | None) -> str | None:
    """Las columnas `ip_origen` son INET — un valor no-IP (p. ej. el
    "testclient" que usa Starlette TestClient, o un socket unix en ciertos
    despliegues) no debe tumbar la petición; se descarta en vez de fallar."""
    if not host:
        return None
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return None
    return host
