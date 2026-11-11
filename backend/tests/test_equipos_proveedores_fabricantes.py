"""Catálogos de proveedores y fabricantes — Fase 2 de hojas de vida
(docs/24-especificacion-hojas-de-vida-mantenimiento-firmas.md,
docs/25-diseno-tecnico-hojas-de-vida.md)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-prov-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab Proveedores", slug, f"admin-{sufijo}@prov.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"headers": {"Authorization": f"Bearer {login.json()['access_token']}"}}


def _headers_otro_laboratorio(client: TestClient, crear_laboratorio_con_admin, etiqueta: str) -> dict:
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-prov-{etiqueta}-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin(
        f"Lab Proveedores {etiqueta}", slug, f"admin-{sufijo}@prov-{etiqueta}.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


# ---- Proveedores ---------------------------------------------------------------


def test_crear_y_listar_proveedor(client: TestClient, contexto: dict):
    creado = client.post(
        "/api/v1/proveedores",
        json={"nombre": "Fisher Scientific", "pais_ciudad": "USA - Pittsburgh", "email": "ventas@fisher.com"},
        headers=contexto["headers"],
    )
    assert creado.status_code == 201, creado.text
    assert creado.json()["nombre"] == "Fisher Scientific"
    assert creado.json()["pais_ciudad"] == "USA - Pittsburgh"

    listado = client.get("/api/v1/proveedores", headers=contexto["headers"])
    assert listado.status_code == 200
    assert any(p["nombre"] == "Fisher Scientific" for p in listado.json())


def test_crear_proveedor_nombre_duplicado_normalizado_rechazado(client: TestClient, contexto: dict):
    """Mismo criterio de normalización que el backfill de la migración 0018
    (lower+trim): "Fisher Scientific" y "  FISHER SCIENTIFIC  " son el mismo
    proveedor para el catálogo."""
    client.post("/api/v1/proveedores", json={"nombre": "Fisher Scientific"}, headers=contexto["headers"])
    duplicado = client.post(
        "/api/v1/proveedores", json={"nombre": "  FISHER SCIENTIFIC  "}, headers=contexto["headers"]
    )
    assert duplicado.status_code == 409
    assert duplicado.json()["error"]["codigo"] == "proveedor_nombre_duplicado"


def test_actualizar_proveedor(client: TestClient, contexto: dict):
    creado = client.post(
        "/api/v1/proveedores", json={"nombre": "Proveedor Original"}, headers=contexto["headers"]
    ).json()

    editado = client.patch(
        f"/api/v1/proveedores/{creado['id']}",
        json={"nombre": "Proveedor Renombrado", "contacto": "Juan Pérez"},
        headers=contexto["headers"],
    )
    assert editado.status_code == 200
    assert editado.json()["nombre"] == "Proveedor Renombrado"
    assert editado.json()["contacto"] == "Juan Pérez"


def test_eliminar_proveedor_en_uso_rechazado(client: TestClient, contexto: dict):
    proveedor = client.post(
        "/api/v1/proveedores", json={"nombre": "Proveedor en uso"}, headers=contexto["headers"]
    ).json()
    creado = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-PROV-1", "nombre": "Balanza", "proveedor_id": proveedor["id"]},
        headers=contexto["headers"],
    )
    assert creado.status_code == 201, creado.text

    eliminar = client.delete(f"/api/v1/proveedores/{proveedor['id']}", headers=contexto["headers"])
    assert eliminar.status_code == 409
    assert eliminar.json()["error"]["codigo"] == "proveedor_en_uso"


def test_eliminar_proveedor_sin_uso_permitido(client: TestClient, contexto: dict):
    proveedor = client.post(
        "/api/v1/proveedores", json={"nombre": "Proveedor libre"}, headers=contexto["headers"]
    ).json()
    eliminar = client.delete(f"/api/v1/proveedores/{proveedor['id']}", headers=contexto["headers"])
    assert eliminar.status_code == 204


def test_crear_equipo_con_proveedor_de_otro_laboratorio_rechazado(
    client: TestClient, contexto: dict, crear_laboratorio_con_admin
):
    headers_otro = _headers_otro_laboratorio(client, crear_laboratorio_con_admin, "otro")
    proveedor_otro = client.post(
        "/api/v1/proveedores", json={"nombre": "Proveedor del otro lab"}, headers=headers_otro
    ).json()

    creado = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-CRUZADO-1", "nombre": "Balanza", "proveedor_id": proveedor_otro["id"]},
        headers=contexto["headers"],
    )
    assert creado.status_code == 422
    assert creado.json()["error"]["codigo"] == "proveedor_invalido"


# ---- Fabricantes ----------------------------------------------------------------


def test_crear_y_listar_fabricante(client: TestClient, contexto: dict):
    creado = client.post(
        "/api/v1/fabricantes",
        json={"nombre": "Tuttnauer", "contacto": "Soporte técnico"},
        headers=contexto["headers"],
    )
    assert creado.status_code == 201, creado.text

    listado = client.get("/api/v1/fabricantes", headers=contexto["headers"])
    assert any(f["nombre"] == "Tuttnauer" for f in listado.json())


def test_crear_fabricante_nombre_duplicado_normalizado_rechazado(client: TestClient, contexto: dict):
    client.post("/api/v1/fabricantes", json={"nombre": "Tuttnauer"}, headers=contexto["headers"])
    duplicado = client.post("/api/v1/fabricantes", json={"nombre": "tuttnauer "}, headers=contexto["headers"])
    assert duplicado.status_code == 409
    assert duplicado.json()["error"]["codigo"] == "fabricante_nombre_duplicado"


def test_eliminar_fabricante_en_uso_rechazado(client: TestClient, contexto: dict):
    fabricante = client.post(
        "/api/v1/fabricantes", json={"nombre": "Fabricante en uso"}, headers=contexto["headers"]
    ).json()
    client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-FAB-1", "nombre": "Autoclave", "fabricante_id": fabricante["id"]},
        headers=contexto["headers"],
    )

    eliminar = client.delete(f"/api/v1/fabricantes/{fabricante['id']}", headers=contexto["headers"])
    assert eliminar.status_code == 409
    assert eliminar.json()["error"]["codigo"] == "fabricante_en_uso"


def test_actualizar_equipo_con_fabricante_de_otro_laboratorio_rechazado(
    client: TestClient, contexto: dict, crear_laboratorio_con_admin
):
    headers_otro = _headers_otro_laboratorio(client, crear_laboratorio_con_admin, "otrofab")
    fabricante_otro = client.post(
        "/api/v1/fabricantes", json={"nombre": "Fabricante del otro lab"}, headers=headers_otro
    ).json()

    creado = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-CRUZADO-2", "nombre": "Autoclave"},
        headers=contexto["headers"],
    ).json()

    editado = client.patch(
        f"/api/v1/equipos/{creado['id']}",
        json={
            "codigo_interno": "EQ-CRUZADO-2",
            "nombre": "Autoclave",
            "fabricante_id": fabricante_otro["id"],
        },
        headers=contexto["headers"],
    )
    assert editado.status_code == 422
    assert editado.json()["error"]["codigo"] == "fabricante_invalido"
