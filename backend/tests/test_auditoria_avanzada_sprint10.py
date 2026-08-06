"""Pruebas de Sprint 10: pantalla de auditoría avanzada — filtros y
exportación (RF-AUD-02/03, HU-ADMIN-03)."""

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
    slug = f"lab-aud10-{sufijo}"
    laboratorio_id, admin_id, correo, password = crear_laboratorio_con_admin(
        "Lab Aud10", slug, f"admin-{sufijo}@aud10.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {
        "admin_id": admin_id,
        "slug": slug,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _crear_equipo(client: TestClient, headers: dict, codigo: str) -> dict:
    respuesta = client.post(
        "/api/v1/equipos", json={"codigo_interno": codigo, "nombre": "Equipo auditado"}, headers=headers
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_filtrar_por_modulo(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    _crear_equipo(client, headers, "EQ-AUD10-1")

    solo_equipos = client.get("/api/v1/auditoria", params={"modulo": "equipos"}, headers=headers)
    assert solo_equipos.status_code == 200
    assert len(solo_equipos.json()["items"]) > 0
    assert all(log["modulo"] == "equipos" for log in solo_equipos.json()["items"])

    solo_documentos = client.get("/api/v1/auditoria", params={"modulo": "documentos"}, headers=headers)
    assert all(log["modulo"] == "documentos" for log in solo_documentos.json()["items"])


def test_filtrar_por_usuario(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    _crear_equipo(client, headers, "EQ-AUD10-2")

    resultado = client.get(
        "/api/v1/auditoria", params={"usuario_id": str(contexto["admin_id"])}, headers=headers
    )
    assert resultado.status_code == 200
    assert all(log["usuario_id"] == str(contexto["admin_id"]) for log in resultado.json()["items"])
    assert any(log["modulo"] == "equipos" for log in resultado.json()["items"])


def test_filtrar_por_rango_de_fechas_futuro_no_devuelve_nada(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    _crear_equipo(client, headers, "EQ-AUD10-3")

    resultado = client.get(
        "/api/v1/auditoria", params={"desde": "2099-01-01T00:00:00Z"}, headers=headers
    )
    assert resultado.status_code == 200
    assert resultado.json()["items"] == []
    assert resultado.json()["total"] == 0


def test_valores_filtro_refleja_datos_reales(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    _crear_equipo(client, headers, "EQ-AUD10-4")

    valores = client.get("/api/v1/auditoria/valores-filtro", headers=headers)
    assert valores.status_code == 200
    assert "equipos" in valores.json()["modulos"]
    assert "crear" in valores.json()["acciones"]


@pytest.mark.parametrize(
    ("formato", "content_type_esperado"),
    [
        ("csv", "text/csv"),
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("pdf", "application/pdf"),
    ],
)
def test_exportar_en_cada_formato(
    client: TestClient, contexto: dict, formato: str, content_type_esperado: str
):
    headers = contexto["headers"]
    _crear_equipo(client, headers, f"EQ-AUD10-EXPORT-{formato}")

    respuesta = client.get("/api/v1/auditoria/export", params={"formato": formato}, headers=headers)
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith(content_type_esperado)
    assert len(respuesta.content) > 0


def test_exportar_formato_no_soportado_falla(client: TestClient, contexto: dict):
    respuesta = client.get(
        "/api/v1/auditoria/export", params={"formato": "docx"}, headers=contexto["headers"]
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "formato_no_soportado"


def test_consulta_a_auditoria_requiere_permiso(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    tecnico_password = "Cl4veSegura!2026"
    rol_tecnico = next(
        r["id"] for r in client.get("/api/v1/roles", headers=headers).json() if r["nombre"] == "tecnico"
    )
    correo = f"tec-aud-{uuid.uuid4().hex[:8]}@aud10.dev"
    client.post(
        "/api/v1/usuarios",
        json={
            "nombre_completo": "Técnico sin acceso a auditoría",
            "correo": correo,
            "password": tecnico_password,
            "rol_ids": [rol_tecnico],
        },
        headers=headers,
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": contexto["slug"], "correo": correo, "password": tecnico_password},
    )
    assert login.status_code == 200
    headers_tecnico = {"Authorization": f"Bearer {login.json()['access_token']}"}

    respuesta = client.get("/api/v1/auditoria", headers=headers_tecnico)
    assert respuesta.status_code == 403
