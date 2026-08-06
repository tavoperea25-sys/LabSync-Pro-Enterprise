"""Pruebas de Sprint 13: logging estructurado (JSON) con trace_id de
correlación — app/core/logging.py."""

from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from app.core.logging import JsonFormatter, fijar_trace_id, obtener_trace_id
from app.main import app


def test_respuesta_incluye_cabecera_de_trace_id_generada() -> None:
    client = TestClient(app)
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert "x-request-id" in respuesta.headers
    assert len(respuesta.headers["x-request-id"]) > 0


def test_respuesta_respeta_trace_id_entrante() -> None:
    client = TestClient(app)
    respuesta = client.get("/health", headers={"X-Request-ID": "mi-trace-de-prueba"})
    assert respuesta.headers["x-request-id"] == "mi-trace-de-prueba"


def test_dos_peticiones_reciben_trace_ids_distintos() -> None:
    client = TestClient(app)
    primero = client.get("/health").headers["x-request-id"]
    segundo = client.get("/health").headers["x-request-id"]
    assert primero != segundo


def test_json_formatter_incluye_trace_id_y_campos_extra() -> None:
    fijar_trace_id("trace-formatter-test")
    registro = logging.LogRecord(
        name="prueba", level=logging.INFO, pathname=__file__, lineno=1,
        msg="mensaje de prueba", args=(), exc_info=None,
    )
    registro.http_status = 200
    salida = json.loads(JsonFormatter().format(registro))
    assert salida["trace_id"] == "trace-formatter-test"
    assert salida["message"] == "mensaje de prueba"
    assert salida["level"] == "INFO"
    assert salida["http_status"] == 200


def test_trace_id_por_defecto_es_guion() -> None:
    fijar_trace_id("-")
    assert obtener_trace_id() == "-"
