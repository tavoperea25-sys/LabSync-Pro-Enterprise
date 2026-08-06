"""Pruebas de Sprint 6: flujo de aprobación (RF-DOC-12/14, HU-DT-02) y
vigencia por fecha con precedencia sobre el estado manual (RF-DOC-13,
RN-DOC-01/02)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def headers_autenticados(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-doc6-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab Doc6", slug, f"admin-{sufijo}@doc6.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _subir_archivo(client: TestClient, headers: dict, contenido: bytes = b"%PDF-1.4 prueba") -> dict:
    solicitud = client.post(
        "/api/v1/documentos/upload-url",
        json={"nombre_archivo": "doc.pdf", "tipo_mime": "application/pdf", "tamano_bytes": len(contenido)},
        headers=headers,
    )
    assert solicitud.status_code == 200, solicitud.text
    datos = solicitud.json()
    respuesta_put = httpx.put(
        datos["url_subida"], content=contenido, headers={"Content-Type": "application/pdf"}
    )
    assert respuesta_put.status_code in (200, 204)
    return {
        "object_key": datos["object_key"],
        "nombre_archivo": "doc.pdf",
        "tamano_bytes": len(contenido),
        "tipo_mime": "application/pdf",
    }


def _crear_documento(client: TestClient, headers: dict, **overrides) -> dict:
    archivo = _subir_archivo(client, headers)
    payload = {"nombre": "Procedimiento de calidad", "archivo": archivo, **overrides}
    respuesta = client.post("/api/v1/documentos", json=payload, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_documento_nuevo_queda_en_revision(client: TestClient, headers_autenticados: dict):
    documento = _crear_documento(client, headers_autenticados)
    assert documento["estado"] == "en_revision"
    assert documento["estado_efectivo"] == "en_revision"


def test_aprobar_documento_lo_deja_vigente_y_registra_version(client: TestClient, headers_autenticados: dict):
    documento = _crear_documento(client, headers_autenticados)

    aprobado = client.post(f"/api/v1/documentos/{documento['id']}/aprobar", headers=headers_autenticados)
    assert aprobado.status_code == 200
    assert aprobado.json()["estado"] == "vigente"
    assert aprobado.json()["responsable_aprobacion_id"] is not None

    detalle = client.get(f"/api/v1/documentos/{documento['id']}", headers=headers_autenticados).json()
    version_vigente = next(v for v in detalle["versiones"] if v["id"] == detalle["version_vigente_id"])
    assert version_vigente["aprobado_por_id"] is not None
    assert version_vigente["aprobado_en"] is not None


def test_aprobar_documento_que_no_esta_en_revision_falla(client: TestClient, headers_autenticados: dict):
    documento = _crear_documento(client, headers_autenticados)
    client.post(f"/api/v1/documentos/{documento['id']}/aprobar", headers=headers_autenticados)

    segundo_intento = client.post(
        f"/api/v1/documentos/{documento['id']}/aprobar", headers=headers_autenticados
    )
    assert segundo_intento.status_code == 409
    assert segundo_intento.json()["error"]["codigo"] == "documento_no_en_revision"


def test_rechazar_documento_mantiene_en_revision_y_registra_motivo(
    client: TestClient, headers_autenticados: dict
):
    documento = _crear_documento(client, headers_autenticados)

    rechazado = client.post(
        f"/api/v1/documentos/{documento['id']}/rechazar",
        json={"comentario": "Falta la firma del responsable de calidad."},
        headers=headers_autenticados,
    )
    assert rechazado.status_code == 200
    assert rechazado.json()["estado"] == "en_revision"

    detalle = client.get(f"/api/v1/documentos/{documento['id']}", headers=headers_autenticados).json()
    assert detalle["ultimo_rechazo"] is not None
    assert detalle["ultimo_rechazo"]["comentario"] == "Falta la firma del responsable de calidad."


def test_subir_nueva_version_tras_aprobar_vuelve_a_en_revision(
    client: TestClient, headers_autenticados: dict
):
    documento = _crear_documento(client, headers_autenticados)
    client.post(f"/api/v1/documentos/{documento['id']}/aprobar", headers=headers_autenticados)

    archivo_v2 = _subir_archivo(client, headers_autenticados, contenido=b"%PDF-1.4 version 2")
    client.post(
        f"/api/v1/documentos/{documento['id']}/versiones", json=archivo_v2, headers=headers_autenticados
    )

    detalle = client.get(f"/api/v1/documentos/{documento['id']}", headers=headers_autenticados).json()
    assert detalle["estado"] == "en_revision"


def test_documento_vencido_nunca_se_muestra_como_vigente(client: TestClient, headers_autenticados: dict):
    ayer = (date.today() - timedelta(days=1)).isoformat()
    hace_un_anio = (date.today() - timedelta(days=365)).isoformat()
    documento = _crear_documento(
        client, headers_autenticados, fecha_emision=hace_un_anio, fecha_vencimiento=ayer
    )
    client.post(f"/api/v1/documentos/{documento['id']}/aprobar", headers=headers_autenticados)

    detalle = client.get(f"/api/v1/documentos/{documento['id']}", headers=headers_autenticados).json()
    # RN-DOC-01: la fecha de vencimiento tiene precedencia — aunque el
    # estado almacenado sea "vigente" tras la aprobación, el efectivo nunca
    # puede mostrarse como vigente.
    assert detalle["estado"] == "vigente"
    assert detalle["estado_efectivo"] == "vencido"


def test_actualizar_metadatos_valida_fechas(client: TestClient, headers_autenticados: dict):
    documento = _crear_documento(client, headers_autenticados)
    respuesta = client.patch(
        f"/api/v1/documentos/{documento['id']}",
        json={
            "actualizar_metadatos": True,
            "fecha_emision": "2026-06-01",
            "fecha_vencimiento": "2026-05-01",
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "fecha_vencimiento_invalida"


def test_actualizar_metadatos_exitoso(client: TestClient, headers_autenticados: dict):
    documento = _crear_documento(client, headers_autenticados)
    respuesta = client.patch(
        f"/api/v1/documentos/{documento['id']}",
        json={
            "actualizar_metadatos": True,
            "categoria": "Procedimientos",
            "fecha_emision": "2026-01-01",
            "fecha_vencimiento": "2027-01-01",
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["categoria"] == "Procedimientos"
    assert cuerpo["fecha_vencimiento"] == "2027-01-01"
