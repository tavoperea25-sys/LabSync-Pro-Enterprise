"""Fase 2 / M5 (planificación 2026-08-04, docs/22) — el token de
`/ws/v1/notificaciones` viaja ahora como subprotocolo del handshake
(`Sec-WebSocket-Protocol`), no como query param. Sin tests previos para este
endpoint (residual documentado en el informe de auditoría: no había
pytest-asyncio configurado) — `TestClient.websocket_connect` es síncrono,
no lo necesita, así que quedan cubiertos aquí por primera vez."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-ws-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab WS", slug, f"admin-{sufijo}@ws.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"token": login.json()["access_token"]}


def test_conecta_con_token_valido_en_el_subprotocolo(client: TestClient, contexto: dict):
    with client.websocket_connect(
        "/ws/v1/notificaciones", subprotocols=["access_token", contexto["token"]]
    ) as ws:
        # Si el servidor hubiera rechazado el handshake, entrar al `with`
        # ya habría lanzado `WebSocketDisconnect` — llegar aquí prueba que
        # `_extraer_token` leyó el subprotocolo correctamente.
        ws.close()


def test_rechaza_conexion_sin_ningun_subprotocolo(client: TestClient):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/v1/notificaciones"):
            pass
    assert exc_info.value.code == 4401


def test_rechaza_token_invalido(client: TestClient):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws/v1/notificaciones", subprotocols=["access_token", "token-falso-no-es-un-jwt"]
        ):
            pass
    assert exc_info.value.code == 4401


def test_rechaza_subprotocolo_sin_el_marcador_esperado(client: TestClient, contexto: dict):
    """El token va en la segunda posición SOLO si la primera es exactamente
    "access_token" — cualquier otra forma se trata como ausente, no se
    intenta adivinar cuál de las partes es el token real."""
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws/v1/notificaciones", subprotocols=["otro-marcador", contexto["token"]]
        ):
            pass
    assert exc_info.value.code == 4401


def test_rechaza_el_refresh_token_por_ser_de_otro_tipo(client: TestClient, contexto: dict):
    """El refresh token real (cookie httpOnly puesta en el login, distinta
    del access token) no debe servir para autenticar el WebSocket — mismo
    chequeo `tipo == "access"` que ya usa `decodificar_access_token` para la
    ruta REST (app/core/security.py), sin duplicar la regla aquí."""
    refresh_token = client.cookies.get("refresh_token")
    assert refresh_token  # confirma que el login sí dejó la cookie

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(
            "/ws/v1/notificaciones", subprotocols=["access_token", refresh_token]
        ):
            pass
    assert exc_info.value.code == 4401
