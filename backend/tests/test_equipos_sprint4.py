"""Pruebas de Sprint 4: duplicar (RF-EQ-05), historial (RF-EQ-09),
exportación (RF-EQ-08) y KPIs del Dashboard."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def headers_autenticados(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-sprint4-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab Sprint4", slug, f"admin-{sufijo}@sprint4.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_duplicar_equipo_genera_codigo_nuevo_y_no_copia_serie(client: TestClient, headers_autenticados: dict):
    original = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-D1", "nombre": "Centrífuga", "numero_serie": "SN-001"},
        headers=headers_autenticados,
    ).json()

    copia = client.post(f"/api/v1/equipos/{original['id']}/duplicar", headers=headers_autenticados)
    assert copia.status_code == 201
    cuerpo = copia.json()
    assert cuerpo["codigo_interno"] != original["codigo_interno"]
    assert cuerpo["nombre"] == "Centrífuga (copia)"
    assert cuerpo["numero_serie"] is None  # RN-EQ-04 — no se copia el n° de serie


def test_duplicar_equipo_tambien_genera_su_propio_qr(client: TestClient, headers_autenticados: dict):
    original = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-D2", "nombre": "Autoclave"},
        headers=headers_autenticados,
    ).json()
    copia = client.post(f"/api/v1/equipos/{original['id']}/duplicar", headers=headers_autenticados).json()

    qr_original = client.get(f"/api/v1/equipos/{original['id']}/qr", headers=headers_autenticados)
    qr_copia = client.get(f"/api/v1/equipos/{copia['id']}/qr", headers=headers_autenticados)
    assert qr_original.status_code == 200
    assert qr_copia.status_code == 200
    assert qr_original.json()["token"] != qr_copia.json()["token"]


def test_historial_registra_crear_actualizar_eliminar(client: TestClient, headers_autenticados: dict):
    creado = client.post(
        "/api/v1/equipos", json={"codigo_interno": "EQ-H1", "nombre": "Balanza"}, headers=headers_autenticados
    ).json()
    client.patch(
        f"/api/v1/equipos/{creado['id']}",
        json={"codigo_interno": "EQ-H1", "nombre": "Balanza Analítica", "estado_operativo": "operativo"},
        headers=headers_autenticados,
    )
    client.delete(f"/api/v1/equipos/{creado['id']}", headers=headers_autenticados)

    historial = client.get(f"/api/v1/equipos/{creado['id']}/historial", headers=headers_autenticados)
    assert historial.status_code == 200
    acciones = [h["accion"] for h in historial.json()]
    # más reciente primero
    assert acciones == ["eliminar", "actualizar", "crear"]
    assert historial.json()[0]["valor_anterior"]["nombre"] == "Balanza Analítica"


def test_historial_de_equipo_inexistente_devuelve_404(client: TestClient, headers_autenticados: dict):
    respuesta = client.get(f"/api/v1/equipos/{uuid.uuid4()}/historial", headers=headers_autenticados)
    assert respuesta.status_code == 404


def test_exportar_equipos_devuelve_xlsx(client: TestClient, headers_autenticados: dict):
    client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-X1", "nombre": "Espectrofotómetro"},
        headers=headers_autenticados,
    )
    respuesta = client.get("/api/v1/equipos/export", headers=headers_autenticados)
    assert respuesta.status_code == 200
    assert "spreadsheetml" in respuesta.headers["content-type"]
    assert len(respuesta.content) > 0


def test_exportar_formato_no_soportado_devuelve_422(client: TestClient, headers_autenticados: dict):
    respuesta = client.get("/api/v1/equipos/export?formato=pdf", headers=headers_autenticados)
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "formato_no_soportado"


def test_dashboard_kpis_reflejan_estados_reales(client: TestClient, headers_autenticados: dict):
    client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-K1", "nombre": "Equipo A", "estado_operativo": "operativo"},
        headers=headers_autenticados,
    )
    client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-K2", "nombre": "Equipo B", "estado_operativo": "fuera_de_servicio"},
        headers=headers_autenticados,
    )

    kpis = client.get("/api/v1/dashboard/kpis", headers=headers_autenticados)
    assert kpis.status_code == 200
    cuerpo = kpis.json()
    assert cuerpo["equipos_operativos"] >= 1
    assert cuerpo["equipos_fuera_de_servicio"] >= 1
    assert cuerpo["equipos_total"] >= 2
