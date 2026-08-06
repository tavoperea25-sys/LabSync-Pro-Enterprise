"""IMP-03 (RC1, docs/24-auditoria-independiente-2026-08-05.md, CRIT-3) —
regresión del XSS almacenado vía Content-Type no vinculado en la subida de
documentos a MinIO.

Reproduce el ataque documentado: el `PUT` real a la URL prefirmada puede
llevar un `Content-Type` distinto del `tipo_mime` declarado/validado, y sin
mitigación MinIO devuelve ese Content-Type real (controlado por el
atacante) al servir la descarga/previsualización. La corrección fuerza
`response-content-type` al valor validado en BD (`documentos_versiones.
tipo_mime`), sin importar qué Content-Type quedó realmente almacenado en el
objeto — ver `app/core/almacenamiento_minio.py::url_descarga/url_vista_previa`.

Corren contra el MinIO real de docker-compose (mismo criterio que el resto
de `test_documentos_sprint*.py`)."""

from __future__ import annotations

import uuid

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
    slug = f"lab-xss-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab XSS", slug, f"admin-{sufijo}@xss.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _subir_con_content_type_real_distinto(
    client: TestClient,
    headers: dict,
    *,
    nombre_archivo: str,
    tipo_mime_declarado: str,
    content_type_real: str,
    contenido: bytes,
) -> dict:
    """Igual que `_subir_archivo` de test_documentos_sprint5.py, salvo que
    permite que el `Content-Type` real del `PUT` difiera del declarado —
    exactamente lo que un atacante controla y la aplicación no puede
    impedir en el momento de la subida (ver análisis de causa raíz)."""
    solicitud = client.post(
        "/api/v1/documentos/upload-url",
        json={
            "nombre_archivo": nombre_archivo,
            "tipo_mime": tipo_mime_declarado,
            "tamano_bytes": len(contenido),
        },
        headers=headers,
    )
    assert solicitud.status_code == 200, solicitud.text
    datos = solicitud.json()

    respuesta_put = httpx.put(
        datos["url_subida"], content=contenido, headers={"Content-Type": content_type_real}
    )
    assert respuesta_put.status_code in (200, 204), respuesta_put.text

    return {
        "object_key": datos["object_key"],
        "nombre_archivo": nombre_archivo,
        "tamano_bytes": len(contenido),
        "tipo_mime": tipo_mime_declarado,
    }


def _crear_documento_con_archivo(client: TestClient, headers: dict, archivo: dict) -> dict:
    respuesta = client.post(
        "/api/v1/documentos", json={"nombre": "Documento de prueba", "archivo": archivo}, headers=headers
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_content_type_servido_es_el_validado_no_el_subido_por_el_atacante(
    client: TestClient, headers_autenticados: dict
):
    """Reproduce el ataque completo: se declara/valida application/pdf, pero
    el PUT real lleva Content-Type: text/html con un payload de script —
    exactamente lo que un atacante haría con una cuenta con permiso
    documentos.crear. La respuesta servida debe llevar SIEMPRE el
    Content-Type validado (application/pdf), nunca text/html, sin importar
    qué quedó realmente almacenado en MinIO."""
    payload_malicioso = b"<script>alert('XSS')</script>"
    archivo = _subir_con_content_type_real_distinto(
        client,
        headers_autenticados,
        nombre_archivo="informe.pdf",
        tipo_mime_declarado="application/pdf",
        content_type_real="text/html",
        contenido=payload_malicioso,
    )
    documento = _crear_documento_con_archivo(client, headers_autenticados, archivo)

    vista_previa = client.get(
        f"/api/v1/documentos/{documento['id']}/vista-previa", headers=headers_autenticados
    )
    assert vista_previa.status_code == 200
    url_vista_previa = vista_previa.json()["url"]
    assert url_vista_previa is not None  # "pdf" está en FORMATOS_CON_PREVISUALIZACION

    respuesta_vista_previa = httpx.get(url_vista_previa)
    assert respuesta_vista_previa.status_code == 200
    # El punto central de la corrección: el Content-Type de la respuesta es
    # el validado por la aplicación, NUNCA el que el atacante puso en el PUT.
    assert respuesta_vista_previa.headers["content-type"].startswith("application/pdf")
    assert "text/html" not in respuesta_vista_previa.headers["content-type"]
    # El binario en sí no se toca (la mitigación es de Content-Type servido,
    # no de escaneo/censura de contenido) — confirma que la corrección actúa
    # exactamente donde se diseñó, no en un punto distinto del flujo.
    assert respuesta_vista_previa.content == payload_malicioso

    descarga = client.get(
        f"/api/v1/documentos/{documento['id']}/versiones/1/download-url", headers=headers_autenticados
    )
    assert descarga.status_code == 200
    respuesta_descarga = httpx.get(descarga.json()["url"])
    assert respuesta_descarga.status_code == 200
    assert respuesta_descarga.headers["content-type"].startswith("application/pdf")
    assert "text/html" not in respuesta_descarga.headers["content-type"]


def test_pdf_legitimo_sigue_sirviendose_correctamente(client: TestClient, headers_autenticados: dict):
    """Caso positivo: cuando el Content-Type real coincide con el declarado
    (el flujo normal, sin ataque), la previsualización y descarga siguen
    funcionando exactamente igual que antes de la corrección."""
    contenido_pdf = b"%PDF-1.4 contenido legitimo de prueba"
    archivo = _subir_con_content_type_real_distinto(
        client,
        headers_autenticados,
        nombre_archivo="manual.pdf",
        tipo_mime_declarado="application/pdf",
        content_type_real="application/pdf",
        contenido=contenido_pdf,
    )
    documento = _crear_documento_con_archivo(client, headers_autenticados, archivo)

    vista_previa = client.get(
        f"/api/v1/documentos/{documento['id']}/vista-previa", headers=headers_autenticados
    )
    assert vista_previa.status_code == 200
    datos_vista_previa = vista_previa.json()
    assert datos_vista_previa["url"] is not None
    assert datos_vista_previa["tipo_mime"] == "application/pdf"

    respuesta = httpx.get(datos_vista_previa["url"])
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("application/pdf")
    assert respuesta.content == contenido_pdf
