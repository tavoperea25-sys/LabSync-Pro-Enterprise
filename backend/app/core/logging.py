"""Logging estructurado (JSON) con `trace_id` de correlación — Sprint 13,
gate de docs/19-checklist.md ("Logs estructurados (JSON) con trace_id de
correlación") pendiente desde el Sprint 1.

Sin dependencias nuevas: un `Formatter` de la librería estándar basta — no
se necesita `structlog`/`python-json-logger` para un formato de salida tan
simple. El `trace_id` viaja en un `contextvars.ContextVar` (no en un
parámetro explícito) para que cualquier `logging.getLogger(...).info(...)`
en cualquier capa (dominio, aplicación, infraestructura) lo incluya
automáticamente sin tener que pasarlo por cada firma de función."""

from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_logger_acceso = logging.getLogger("acceso")

_CABECERA_TRACE_ID = "X-Request-ID"

_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")

_CAMPOS_ESTANDAR = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


def obtener_trace_id() -> str:
    return _trace_id_var.get()


def fijar_trace_id(valor: str) -> None:
    _trace_id_var.set(valor)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": obtener_trace_id(),
        }
        # Campos pasados vía `extra={...}` en la llamada de logging — p. ej.
        # `logger.info("request", extra={"method": "GET", "status": 200})`.
        for clave, valor in record.__dict__.items():
            if clave not in _CAMPOS_ESTANDAR:
                payload[clave] = valor
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configurar_logging(nivel: int = logging.INFO) -> None:
    """Reemplaza los handlers del logger raíz por uno solo con formato JSON
    — se llama una vez al arrancar el proceso (API o worker), nunca por
    request/ciclo."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    raiz = logging.getLogger()
    raiz.handlers = [handler]
    raiz.setLevel(nivel)


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Toma (o genera) un `trace_id` por petición, lo fija en el
    `ContextVar` para que TODO log emitido durante esa petición lo incluya
    automáticamente, lo devuelve en la cabecera de respuesta para que el
    cliente pueda correlacionar, y deja un log de acceso estructurado con
    método/ruta/status/duración. Convive con el log de acceso en texto
    plano que uvicorn emite por su cuenta (logger `uvicorn.access`,
    configurado aparte) sin intentar silenciarlo ni reemplazarlo."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get(_CABECERA_TRACE_ID) or str(uuid.uuid4())
        fijar_trace_id(trace_id)

        inicio = time.monotonic()
        response = await call_next(request)
        duracion_ms = round((time.monotonic() - inicio) * 1000, 2)

        response.headers[_CABECERA_TRACE_ID] = trace_id
        _logger_acceso.info(
            "request",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duracion_ms": duracion_ms,
            },
        )
        return response
