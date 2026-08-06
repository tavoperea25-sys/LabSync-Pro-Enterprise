"""Pruebas end-to-end del módulo Auth vía API real (docs/09-user-flows.md Flow 1)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    # Un cliente nuevo por prueba: evita que las cookies de sesión de una
    # prueba se filtren a otra (TestClient conserva su cookie jar mientras
    # viva la instancia).
    return TestClient(app)


def test_login_exitoso_emite_access_token_y_cookie(client: TestClient, crear_laboratorio_con_admin):
    _, _, correo, password = crear_laboratorio_con_admin("Lab Login", "lab-login", "user@lab-login.dev")

    respuesta = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-login", "correo": correo, "password": password},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["usuario"]["correo"] == correo
    assert "administrador" in cuerpo["usuario"]["roles"]
    assert cuerpo["access_token"]
    assert "refresh_token" in respuesta.cookies


def test_login_password_incorrecto_no_revela_informacion(client: TestClient, crear_laboratorio_con_admin):
    _, _, correo, _ = crear_laboratorio_con_admin("Lab Fail", "lab-fail", "user@lab-fail.dev")

    respuesta = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-fail", "correo": correo, "password": "password-incorrecta"},
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["codigo"] == "credenciales_invalidas"


def test_login_con_slug_de_otro_tenant_falla(client: TestClient, crear_laboratorio_con_admin):
    """El usuario existe, pero no en el laboratorio indicado — RN-TEN-01."""
    crear_laboratorio_con_admin("Lab X", "lab-x", "user@lab-x.dev", "Passw0rd!Segura")
    crear_laboratorio_con_admin("Lab Y", "lab-y", "otro@lab-y.dev", "Passw0rd!Segura")

    respuesta = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-y", "correo": "user@lab-x.dev", "password": "Passw0rd!Segura"},
    )

    assert respuesta.status_code == 401


def test_me_sin_token_devuelve_401(client: TestClient):
    respuesta = client.get("/api/v1/auth/me")
    assert respuesta.status_code == 401


def test_flujo_completo_login_me_refresh_logout(client: TestClient, crear_laboratorio_con_admin):
    _, _, correo, password = crear_laboratorio_con_admin("Lab Flow", "lab-flow", "user@lab-flow.dev")

    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-flow", "correo": correo, "password": password},
    )
    access_token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json()["correo"] == correo

    refresh_token_original = client.cookies.get("refresh_token")

    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200

    nuevo_access_token = refresh.json()["access_token"]
    me_tras_refresh = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {nuevo_access_token}"})
    assert me_tras_refresh.status_code == 200

    # Detección de reuso (docs/16-seguridad.md): el refresh token original
    # ya fue rotado — volver a presentarlo debe fallar, no solo por estar
    # "viejo" sino porque su reuso es indicio de robo.
    client.cookies.jar.clear()
    client.cookies.set("refresh_token", refresh_token_original, path="/api/v1/auth")
    reuso = client.post("/api/v1/auth/refresh")
    assert reuso.status_code == 401

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    refresh_tras_logout = client.post("/api/v1/auth/refresh")
    assert refresh_tras_logout.status_code == 401


def test_bloqueo_progresivo_tras_intentos_fallidos(client: TestClient, crear_laboratorio_con_admin):
    _, _, correo, _ = crear_laboratorio_con_admin("Lab Bloqueo", "lab-bloqueo", "user@lab-bloqueo.dev")

    for _ in range(5):
        client.post(
            "/api/v1/auth/login",
            json={"laboratorio_slug": "lab-bloqueo", "correo": correo, "password": "incorrecta"},
        )

    respuesta = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-bloqueo", "correo": correo, "password": "incorrecta"},
    )

    assert respuesta.status_code == 429
    assert respuesta.json()["error"]["codigo"] == "cuenta_bloqueada"
