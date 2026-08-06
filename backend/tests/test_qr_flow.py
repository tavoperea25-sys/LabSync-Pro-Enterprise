"""Pruebas del módulo QR (RF-QR-01 a 04) — incluida la mitigación de rate
limiting que Sprint 4 exigía antes de exponer la vista pública sin
autenticación (docs/18-sprints.md, riesgo del Sprint 4)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def equipo_con_qr(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-qr-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab QR", slug, f"admin-{sufijo}@qr.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    equipo = client.post(
        "/api/v1/equipos", json={"codigo_interno": "EQ-QR1", "nombre": "Microscopio"}, headers=headers
    ).json()
    qr_info = client.get(f"/api/v1/equipos/{equipo['id']}/qr", headers=headers).json()
    return equipo, qr_info["token"], headers


def test_qr_se_genera_automaticamente_al_crear_equipo(equipo_con_qr):
    _, token, _ = equipo_con_qr
    assert len(token) >= 32  # alta entropía — RN-QR-01


def test_obtener_imagen_qr_devuelve_un_png_real(client: TestClient, equipo_con_qr):
    """Fase 1/I12 — la generación de la imagen (`qrcode.make` + PNG en
    memoria) no tenía ninguna prueba; solo se probaba `/qr` (el token/URL),
    nunca `/qr-imagen` (el binario)."""
    equipo, _, headers = equipo_con_qr
    respuesta = client.get(f"/api/v1/equipos/{equipo['id']}/qr-imagen", headers=headers)
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "image/png"
    # Firma de archivo PNG real (8 bytes) — confirma que el cuerpo es una
    # imagen válida, no solo que el content-type está bien declarado.
    assert respuesta.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_ver_equipo_por_qr_sin_autenticacion(client: TestClient, equipo_con_qr):
    equipo, token, _ = equipo_con_qr
    # Deliberadamente SIN header Authorization — RF-QR-02 es público.
    respuesta = client.get(f"/api/v1/publico/qr/{token}")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["codigo_interno"] == equipo["codigo_interno"]
    # RF-QR-02: solo campos públicos — nunca observaciones/proveedor/responsable.
    assert "observaciones" not in cuerpo
    assert "proveedor" not in cuerpo


def test_ver_equipo_por_qr_token_invalido_devuelve_404(client: TestClient):
    respuesta = client.get("/api/v1/publico/qr/token-que-no-existe")
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "token_qr_invalido"


def test_reportar_incidencia_sin_autenticacion(client: TestClient, equipo_con_qr):
    _, token, _ = equipo_con_qr
    respuesta = client.post(
        f"/api/v1/publico/qr/{token}/incidencias",
        json={"descripcion": "El equipo hace ruido extraño.", "contacto_nombre": "Juan Pérez"},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "pendiente"


def test_reportar_incidencia_token_invalido_devuelve_404(client: TestClient):
    respuesta = client.post(
        "/api/v1/publico/qr/token-invalido/incidencias", json={"descripcion": "Prueba"}
    )
    assert respuesta.status_code == 404


def test_reportar_incidencia_tiene_rate_limiting(client: TestClient, equipo_con_qr):
    """RF-QR-03 es la superficie más expuesta a abuso (escribe sin
    autenticación) — debe existir un límite real, no solo documentado."""
    _, token, _ = equipo_con_qr

    codigos = [
        client.post(
            f"/api/v1/publico/qr/{token}/incidencias", json={"descripcion": f"Reporte {i}"}
        ).status_code
        for i in range(15)
    ]

    assert 429 in codigos, "Se esperaba que el rate limit (5/min) se activara en algún punto de 15 intentos."
