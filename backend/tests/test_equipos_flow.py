"""Pruebas end-to-end del módulo Equipos vía API real (docs/03-requerimientos-
funcionales.md Módulo 3, RF-EQ-01 a RF-EQ-04, RF-EQ-06, RF-EQ-07)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _crear_equipo(client: TestClient, headers: dict, **campos) -> dict:
    datos = {"codigo_interno": "EQ-000", "nombre": "Equipo de prueba", **campos}
    return client.post("/api/v1/equipos", json=datos, headers=headers).json()


@pytest.fixture
def headers_autenticados(client: TestClient, crear_laboratorio_con_admin):
    # Slug único por invocación — este fixture se usa en varios tests dentro
    # de la misma sesión de pytest, que no hace rollback entre tests (ver
    # tests/conftest.py); reusar un slug fijo colisiona con la restricción
    # de unicidad del segundo test en adelante.
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-equipos-flow-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin(
        "Lab Equipos", slug, f"admin-{sufijo}@lab-equipos-flow.dev"
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": slug, "correo": correo, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_crear_y_obtener_equipo(client: TestClient, headers_autenticados: dict):
    respuesta = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-100", "nombre": "Microscopio Óptico"},
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 201
    equipo = respuesta.json()
    assert equipo["codigo_interno"] == "EQ-100"
    assert equipo["estado_operativo"] == "operativo"

    obtenido = client.get(f"/api/v1/equipos/{equipo['id']}", headers=headers_autenticados)
    assert obtenido.status_code == 200
    assert obtenido.json()["nombre"] == "Microscopio Óptico"


def test_codigo_interno_duplicado_devuelve_409(client: TestClient, headers_autenticados: dict):
    _crear_equipo(client, headers_autenticados, codigo_interno="EQ-200", nombre="Centrífuga")
    respuesta = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-200", "nombre": "Otra Centrífuga"},
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "codigo_interno_duplicado"


def test_estado_operativo_invalido_devuelve_422(client: TestClient, headers_autenticados: dict):
    respuesta = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-300", "nombre": "Analizador", "estado_operativo": "no_existe"},
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 422


def test_listar_filtra_por_busqueda_y_estado(client: TestClient, headers_autenticados: dict):
    _crear_equipo(client, headers_autenticados, codigo_interno="EQ-400", nombre="Espectrofotómetro")
    _crear_equipo(
        client,
        headers_autenticados,
        codigo_interno="EQ-401",
        nombre="Balanza Analítica",
        estado_operativo="fuera_de_servicio",
    )

    resultado_busqueda = client.get("/api/v1/equipos?q=Espectrofotómetro", headers=headers_autenticados)
    assert resultado_busqueda.status_code == 200
    cuerpo = resultado_busqueda.json()
    assert cuerpo["total"] == 1
    assert cuerpo["items"][0]["codigo_interno"] == "EQ-400"

    resultado_estado = client.get(
        "/api/v1/equipos?estado_operativo=fuera_de_servicio", headers=headers_autenticados
    )
    codigos = {e["codigo_interno"] for e in resultado_estado.json()["items"]}
    assert "EQ-401" in codigos
    assert "EQ-400" not in codigos


def test_editar_equipo(client: TestClient, headers_autenticados: dict):
    creado = _crear_equipo(client, headers_autenticados, codigo_interno="EQ-500", nombre="Autoclave")

    editado = client.patch(
        f"/api/v1/equipos/{creado['id']}",
        json={
            "codigo_interno": "EQ-500",
            "nombre": "Autoclave Vertical",
            "estado_operativo": "en_mantenimiento",
        },
        headers=headers_autenticados,
    )
    assert editado.status_code == 200
    assert editado.json()["nombre"] == "Autoclave Vertical"
    assert editado.json()["estado_operativo"] == "en_mantenimiento"


def test_eliminar_equipo_es_soft_delete(client: TestClient, headers_autenticados: dict):
    creado = _crear_equipo(client, headers_autenticados, codigo_interno="EQ-600", nombre="Incubadora")

    eliminado = client.delete(f"/api/v1/equipos/{creado['id']}", headers=headers_autenticados)
    assert eliminado.status_code == 204

    obtenido = client.get(f"/api/v1/equipos/{creado['id']}", headers=headers_autenticados)
    assert obtenido.status_code == 404

    # RN-EQ-01: el registro sigue existiendo en base de datos (soft delete),
    # no aparece en el listado normal.
    listado = client.get("/api/v1/equipos", headers=headers_autenticados)
    codigos = {e["codigo_interno"] for e in listado.json()["items"]}
    assert "EQ-600" not in codigos


def test_equipos_sin_autenticacion_devuelve_401(client: TestClient):
    respuesta = client.get("/api/v1/equipos")
    assert respuesta.status_code == 401


def test_categorias_y_areas_listables(client: TestClient, headers_autenticados: dict):
    categorias = client.get("/api/v1/categorias-equipo", headers=headers_autenticados)
    areas = client.get("/api/v1/areas", headers=headers_autenticados)
    assert categorias.status_code == 200
    assert areas.status_code == 200
