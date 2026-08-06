"""Pruebas de Sprint 13: exportación/portabilidad de datos del tenant —
GET /api/v1/configuracion/exportar-datos."""

from __future__ import annotations

import io
import uuid
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-exp13-{sufijo}"
    laboratorio_id, admin_id, correo, password = crear_laboratorio_con_admin(
        "Lab Exp13", slug, f"admin-{sufijo}@exp13.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {
        "slug": slug,
        "laboratorio_id": laboratorio_id,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _rol_id(client: TestClient, headers: dict, nombre: str) -> str:
    roles = client.get("/api/v1/roles", headers=headers).json()
    return next(r["id"] for r in roles if r["nombre"] == nombre)


def _zip_de(respuesta) -> zipfile.ZipFile:  # type: ignore[no-untyped-def]
    return zipfile.ZipFile(io.BytesIO(respuesta.content))


def test_exportar_datos_devuelve_zip_con_todas_las_entidades(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    equipo = client.post(
        "/api/v1/equipos", json={"codigo_interno": "EQ-EXP13", "nombre": "Equipo exportado"}, headers=headers
    )
    assert equipo.status_code == 201

    respuesta = client.get("/api/v1/configuracion/exportar-datos", headers=headers)
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/zip"

    zf = _zip_de(respuesta)
    nombres = set(zf.namelist())
    assert nombres == {
        "equipos.csv", "documentos.csv", "calibraciones.csv", "mantenimientos.csv",
        "usuarios.csv", "categorias_equipo.csv", "areas.csv", "README.txt",
    }
    contenido_equipos = zf.read("equipos.csv").decode("utf-8-sig")
    assert "EQ-EXP13" in contenido_equipos


def test_exportar_datos_no_incluye_password_hash(client: TestClient, contexto: dict):
    zf = _zip_de(client.get("/api/v1/configuracion/exportar-datos", headers=contexto["headers"]))
    contenido_usuarios = zf.read("usuarios.csv").decode("utf-8-sig")
    encabezados = contenido_usuarios.splitlines()[0]
    assert "password" not in encabezados.lower()
    assert "intentos_fallidos" not in encabezados.lower()


def test_exportar_datos_aislamiento_entre_tenants(
    client: TestClient, contexto: dict, crear_laboratorio_con_admin
):
    headers_a = contexto["headers"]
    client.post(
        "/api/v1/equipos", json={"codigo_interno": "EQ-EXP13-A", "nombre": "Solo lab A"}, headers=headers_a
    )

    sufijo_b = uuid.uuid4().hex[:8]
    slug_b = f"lab-exp13-b-{sufijo_b}"
    _lab_b_id, _admin_b_id, correo_b, password_b = crear_laboratorio_con_admin(
        "Lab Exp13 B", slug_b, f"admin-b-{sufijo_b}@exp13.dev"
    )
    login_b = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug_b, "correo": correo_b, "password": password_b}
    )
    assert login_b.status_code == 200
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}
    client.post(
        "/api/v1/equipos", json={"codigo_interno": "EQ-EXP13-B", "nombre": "Solo lab B"}, headers=headers_b
    )

    zip_a = _zip_de(client.get("/api/v1/configuracion/exportar-datos", headers=headers_a))
    equipos_a = zip_a.read("equipos.csv").decode("utf-8-sig")
    assert "EQ-EXP13-A" in equipos_a
    assert "EQ-EXP13-B" not in equipos_a

    zip_b = _zip_de(client.get("/api/v1/configuracion/exportar-datos", headers=headers_b))
    equipos_b = zip_b.read("equipos.csv").decode("utf-8-sig")
    assert "EQ-EXP13-B" in equipos_b
    assert "EQ-EXP13-A" not in equipos_b


def test_exportar_datos_requiere_permiso_configuracion_gestionar(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    password_tecnico = "Cl4veSegura!2026"
    correo_tecnico = f"tec-exp13-{uuid.uuid4().hex[:8]}@exp13.dev"
    creado = client.post(
        "/api/v1/usuarios",
        json={
            "nombre_completo": "Técnico sin acceso",
            "correo": correo_tecnico,
            "password": password_tecnico,
            "rol_ids": [_rol_id(client, headers, "tecnico")],
        },
        headers=headers,
    )
    assert creado.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": contexto["slug"], "correo": correo_tecnico, "password": password_tecnico},
    )
    assert login.status_code == 200
    headers_tecnico = {"Authorization": f"Bearer {login.json()['access_token']}"}

    respuesta = client.get("/api/v1/configuracion/exportar-datos", headers=headers_tecnico)
    assert respuesta.status_code == 403


def test_exportar_datos_registra_auditoria(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    client.get("/api/v1/configuracion/exportar-datos", headers=headers)
    auditoria = client.get(
        "/api/v1/auditoria", params={"modulo": "configuracion"}, headers=headers
    ).json()
    assert any(log["accion"] == "exportar_datos_tenant" for log in auditoria["items"])
