"""RF-EQ-01 (docs/03-requerimientos-funcionales.md, Módulo 3): "manual de
usuario (archivo)" es un campo explícito de la ficha técnica desde el propio
primer requisito del módulo (Sprint 3), con validación de tipo ("manual
(PDF)") descrita en el propio requisito — igual que "fotografía" (cerrada en
el Sprint 24), no tenía columna en base de datos ni ningún camino de
subida/descarga. Ver Sprint 26, docs/18-sprints.md."""

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
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-manual26-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin(
        "Lab Manual26", slug, f"admin-{sufijo}@manual26.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"headers": {"Authorization": f"Bearer {login.json()['access_token']}"}}


def _subir_manual(
    client: TestClient,
    headers: dict,
    nombre_archivo: str = "manual.pdf",
    contenido: bytes = b"%PDF-1.4 contenido de prueba",
) -> str:
    solicitud = client.post(
        "/api/v1/equipos/upload-url/manual",
        json={
            "nombre_archivo": nombre_archivo,
            "tipo_mime": "application/pdf",
            "tamano_bytes": len(contenido),
        },
        headers=headers,
    )
    assert solicitud.status_code == 200, solicitud.text
    datos = solicitud.json()

    respuesta_put = httpx.put(
        datos["url_subida"], content=contenido, headers={"Content-Type": "application/pdf"}
    )
    assert respuesta_put.status_code in (200, 204), respuesta_put.text

    return datos["object_key"]


def test_solicitar_url_manual_formato_no_permitido(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/equipos/upload-url/manual",
        json={"nombre_archivo": "foto.jpg", "tipo_mime": "image/jpeg", "tamano_bytes": 100},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "formato_manual_no_soportado"


def test_solicitar_url_manual_demasiado_grande(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/equipos/upload-url/manual",
        json={
            "nombre_archivo": "grande.pdf",
            "tipo_mime": "application/pdf",
            "tamano_bytes": 25 * 1024 * 1024,
        },
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "manual_demasiado_grande"


def test_crear_equipo_con_manual_expone_url_de_descarga(client: TestClient, contexto: dict):
    object_key = _subir_manual(client, contexto["headers"])

    creado = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-MAN-1", "nombre": "Balanza", "manual_object_key": object_key},
        headers=contexto["headers"],
    )
    assert creado.status_code == 201, creado.text
    assert creado.json()["manual_url"] is not None
    assert creado.json()["manual_object_key"] == object_key


def test_equipo_sin_manual_expone_manual_url_null(client: TestClient, contexto: dict):
    creado = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-MAN-2", "nombre": "Centrífuga"},
        headers=contexto["headers"],
    )
    assert creado.status_code == 201
    assert creado.json()["manual_url"] is None
    assert creado.json()["manual_object_key"] is None


def test_actualizar_otro_campo_sin_reenviar_manual_no_lo_borra(client: TestClient, contexto: dict):
    """Mismo bug de regresión ya corregido para la foto (Sprint 25): el
    cliente debe reenviar el object_key estable, no omitirlo."""
    object_key = _subir_manual(client, contexto["headers"])
    creado = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-MAN-3", "nombre": "Termómetro", "manual_object_key": object_key},
        headers=contexto["headers"],
    ).json()

    editado = client.patch(
        f"/api/v1/equipos/{creado['id']}",
        json={
            "codigo_interno": "EQ-MAN-3",
            "nombre": "Termómetro Digital",
            "manual_object_key": creado["manual_object_key"],
        },
        headers=contexto["headers"],
    )
    assert editado.status_code == 200
    assert editado.json()["manual_url"] is not None
    assert editado.json()["manual_object_key"] == object_key


def test_duplicar_equipo_si_copia_el_manual(client: TestClient, contexto: dict):
    """A diferencia de la foto (RN-EQ-04, Sprint 24): el manual describe el
    modelo, no una unidad física — es válido para la copia."""
    object_key = _subir_manual(client, contexto["headers"])
    original = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-MAN-4", "nombre": "Autoclave", "manual_object_key": object_key},
        headers=contexto["headers"],
    )

    copia = client.post(f"/api/v1/equipos/{original.json()['id']}/duplicar", headers=contexto["headers"])
    assert copia.status_code == 201
    assert copia.json()["manual_object_key"] == object_key
    assert copia.json()["manual_url"] is not None
