"""Regresión de Fase 0 / C5 (auditoría 2026-07-31) — `/login` y `/refresh`
deben rechazar con 429 el exceso de peticiones desde la misma IP, sin
afectar el flujo normal de autenticación. Ver app/core/rate_limit.py,
app/core/config.py (rate_limit_login/rate_limit_refresh) y
app/modules/auth/presentation/router.py.

Cada test ajusta el límite configurado a un valor chico y predecible vía
`get_settings()` (el mismo objeto cacheado que lee el decorador
`@limiter.limit(lambda: get_settings().rate_limit_login)` en cada petición)
en vez de depender del default de producción — así las pruebas no dependen
de temporización real de un minuto completo."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _login(client: TestClient, slug: str, correo: str, password: str):
    return client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": slug, "correo": correo, "password": password},
    )


def test_login_dentro_del_limite_no_es_bloqueado(
    client: TestClient, crear_laboratorio_con_admin, monkeypatch
):
    """RNF-SEG — el rate limiting no debe interferir con el flujo normal:
    varios logins legítimos seguidos, todos dentro del límite, siguen
    devolviendo 200."""
    monkeypatch.setattr(get_settings(), "rate_limit_login", "5/minute")
    _, _, correo, password = crear_laboratorio_con_admin(
        "Lab RL Dentro", "lab-rl-dentro", "admin@lab-rl-dentro.dev"
    )

    for _ in range(4):
        respuesta = _login(client, "lab-rl-dentro", correo, password)
        assert respuesta.status_code == 200


def test_login_excede_el_limite_devuelve_429(client: TestClient, crear_laboratorio_con_admin, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_login", "3/minute")
    _, _, correo, password = crear_laboratorio_con_admin(
        "Lab RL Excede", "lab-rl-excede", "admin@lab-rl-excede.dev"
    )

    for _ in range(3):
        respuesta = _login(client, "lab-rl-excede", correo, password)
        assert respuesta.status_code == 200

    excedida = _login(client, "lab-rl-excede", correo, password)
    assert excedida.status_code == 429
    # Se distingue del 429 de bloqueo progresivo por intentos fallidos
    # (RF-AUTH-06, `cuenta_bloqueada`) — este es el límite por IP, no por
    # cuenta; no debe traer ese código de error de dominio.
    assert excedida.json().get("error") != {"codigo": "cuenta_bloqueada"}


def test_login_permite_de_nuevo_tras_expirar_la_ventana(
    client: TestClient, crear_laboratorio_con_admin, monkeypatch
):
    monkeypatch.setattr(get_settings(), "rate_limit_login", "2/second")
    _, _, correo, password = crear_laboratorio_con_admin(
        "Lab RL Ventana", "lab-rl-ventana", "admin@lab-rl-ventana.dev"
    )

    assert _login(client, "lab-rl-ventana", correo, password).status_code == 200
    assert _login(client, "lab-rl-ventana", correo, password).status_code == 200
    assert _login(client, "lab-rl-ventana", correo, password).status_code == 429

    time.sleep(1.1)  # la ventana de 1 segundo ya expiró

    assert _login(client, "lab-rl-ventana", correo, password).status_code == 200


def test_refresh_excede_el_limite_devuelve_429(client: TestClient, crear_laboratorio_con_admin, monkeypatch):
    _, _, correo, password = crear_laboratorio_con_admin(
        "Lab RL Refresh", "lab-rl-refresh", "admin@lab-rl-refresh.dev"
    )
    # El propio login (antes de fijar el límite chico) deja la cookie de
    # refresh en el cliente — el límite bajo se aplica solo a partir de acá,
    # sobre /refresh.
    assert _login(client, "lab-rl-refresh", correo, password).status_code == 200

    monkeypatch.setattr(get_settings(), "rate_limit_refresh", "3/minute")

    for _ in range(3):
        respuesta = client.post("/api/v1/auth/refresh")
        assert respuesta.status_code == 200

    excedida = client.post("/api/v1/auth/refresh")
    assert excedida.status_code == 429


def test_refresh_dentro_del_limite_no_es_bloqueado(
    client: TestClient, crear_laboratorio_con_admin, monkeypatch
):
    _, _, correo, password = crear_laboratorio_con_admin(
        "Lab RL Refresh Ok", "lab-rl-refresh-ok", "admin@lab-rl-refresh-ok.dev"
    )
    assert _login(client, "lab-rl-refresh-ok", correo, password).status_code == 200

    monkeypatch.setattr(get_settings(), "rate_limit_refresh", "5/minute")

    for _ in range(4):
        respuesta = client.post("/api/v1/auth/refresh")
        assert respuesta.status_code == 200
