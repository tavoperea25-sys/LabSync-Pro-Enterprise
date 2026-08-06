"""Rate limiting compartido — imprescindible en endpoints públicos sin
autenticación (docs/16-seguridad.md sección 6, docs/18-sprints.md riesgo
del Sprint 4: "la vista pública QR requiere endurecer rate limiting antes
de exponerse sin autenticación")."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
