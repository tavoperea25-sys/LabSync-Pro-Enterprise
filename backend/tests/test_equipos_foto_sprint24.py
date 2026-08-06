"""RF-EQ-01 (docs/03-requerimientos-funcionales.md, Módulo 3): registrar un
equipo con "fotografía" es un campo explícito desde el propio primer
requisito del módulo (Sprint 3) — la columna `foto_url` existe en la base de
datos desde la migración 0002, pero nunca se conectó a ningún endpoint,
servicio ni pantalla: quedó huérfana durante ~20 sprints. RF-QR-02 también
exige mostrar "foto" en la vista pública de QR, y tampoco estaba conectada.
Ver Sprint 24, docs/18-sprints.md."""

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
    slug = f"lab-foto24-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab Foto24", slug, f"admin-{sufijo}@foto24.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"slug": slug, "headers": {"Authorization": f"Bearer {login.json()['access_token']}"}}


def _subir_foto(
    client: TestClient, headers: dict, nombre_archivo: str = "equipo.jpg", contenido: bytes = b"\xff\xd8\xff"
) -> str:
    solicitud = client.post(
        "/api/v1/equipos/upload-url/foto",
        json={"nombre_archivo": nombre_archivo, "tipo_mime": "image/jpeg", "tamano_bytes": len(contenido)},
        headers=headers,
    )
    assert solicitud.status_code == 200, solicitud.text
    datos = solicitud.json()

    respuesta_put = httpx.put(datos["url_subida"], content=contenido, headers={"Content-Type": "image/jpeg"})
    assert respuesta_put.status_code in (200, 204), respuesta_put.text

    return datos["object_key"]


def test_solicitar_url_foto_formato_no_permitido(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/equipos/upload-url/foto",
        json={"nombre_archivo": "manual.pdf", "tipo_mime": "application/pdf", "tamano_bytes": 100},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "formato_foto_no_soportado"


def test_solicitar_url_foto_demasiado_grande(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/equipos/upload-url/foto",
        json={"nombre_archivo": "grande.jpg", "tipo_mime": "image/jpeg", "tamano_bytes": 6 * 1024 * 1024},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "foto_demasiado_grande"


def test_crear_equipo_con_foto_expone_url_resuelta(client: TestClient, contexto: dict):
    object_key = _subir_foto(client, contexto["headers"])

    creado = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-FOTO-1", "nombre": "Balanza", "foto_object_key": object_key},
        headers=contexto["headers"],
    )
    assert creado.status_code == 201, creado.text
    assert creado.json()["foto_url"] is not None
    assert object_key in creado.json()["foto_url"] or "X-Amz-Signature" in creado.json()["foto_url"]

    obtenido = client.get(f"/api/v1/equipos/{creado.json()['id']}", headers=contexto["headers"])
    assert obtenido.json()["foto_url"] is not None


def test_equipo_sin_foto_expone_foto_url_null(client: TestClient, contexto: dict):
    creado = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-FOTO-2", "nombre": "Centrífuga"},
        headers=contexto["headers"],
    )
    assert creado.status_code == 201
    assert creado.json()["foto_url"] is None


def test_actualizar_equipo_puede_agregar_foto(client: TestClient, contexto: dict):
    creado = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-FOTO-3", "nombre": "Microscopio"},
        headers=contexto["headers"],
    )
    assert creado.json()["foto_url"] is None

    object_key = _subir_foto(client, contexto["headers"])
    actualizado = client.patch(
        f"/api/v1/equipos/{creado.json()['id']}",
        json={"codigo_interno": "EQ-FOTO-3", "nombre": "Microscopio", "foto_object_key": object_key},
        headers=contexto["headers"],
    )
    assert actualizado.status_code == 200, actualizado.text
    assert actualizado.json()["foto_url"] is not None


def test_actualizar_otro_campo_sin_reenviar_foto_no_la_borra(client: TestClient, contexto: dict):
    """Regresión: el payload del formulario del frontend solo incluye
    `foto_object_key` cuando el usuario sube una foto nueva en esa misma
    edición — si el cliente lo omite (p. ej. porque el usuario editó otro
    campo sin tocar la foto), FastAPI/Pydantic completa `None` por defecto,
    y un `actualizar()` ingenuo la borraría en cada edición no relacionada.
    Mismo criterio ya aplicado al logo institucional
    (`InstitucionOut.logo_object_key`, Sprint 12) — el cliente necesita el
    object_key estable para poder "no tocar la foto actual"."""
    object_key = _subir_foto(client, contexto["headers"])
    creado = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-FOTO-7", "nombre": "Termómetro", "foto_object_key": object_key},
        headers=contexto["headers"],
    ).json()
    assert creado["foto_url"] is not None
    assert creado["foto_object_key"] == object_key

    # El cliente reenvía el object_key que YA tenía (obtenido de la propia
    # respuesta anterior), no lo omite — esto es lo que EquipoFormPage.tsx
    # debe hacer también en el frontend.
    editado = client.patch(
        f"/api/v1/equipos/{creado['id']}",
        json={
            "codigo_interno": "EQ-FOTO-7",
            "nombre": "Termómetro Digital",
            "foto_object_key": creado["foto_object_key"],
        },
        headers=contexto["headers"],
    )
    assert editado.status_code == 200
    assert editado.json()["foto_url"] is not None
    assert editado.json()["foto_object_key"] == object_key


def test_duplicar_equipo_no_copia_la_foto(client: TestClient, contexto: dict):
    """RN-EQ-04 — la fotografía es de la unidad física original, mismo
    criterio ya aplicado a `numero_serie`."""
    object_key = _subir_foto(client, contexto["headers"])
    original = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-FOTO-4", "nombre": "Autoclave", "foto_object_key": object_key},
        headers=contexto["headers"],
    )
    assert original.json()["foto_url"] is not None

    copia = client.post(f"/api/v1/equipos/{original.json()['id']}/duplicar", headers=contexto["headers"])
    assert copia.status_code == 201
    assert copia.json()["foto_url"] is None


def test_vista_publica_qr_incluye_foto_cuando_el_equipo_tiene(client: TestClient, contexto: dict):
    object_key = _subir_foto(client, contexto["headers"])
    equipo = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-FOTO-5", "nombre": "Espectrofotómetro", "foto_object_key": object_key},
        headers=contexto["headers"],
    ).json()
    token = client.get(f"/api/v1/equipos/{equipo['id']}/qr", headers=contexto["headers"]).json()["token"]

    publico = client.get(f"/api/v1/publico/qr/{token}")
    assert publico.status_code == 200
    assert publico.json()["foto_url"] is not None


def test_vista_publica_qr_foto_null_sin_foto(client: TestClient, contexto: dict):
    equipo = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-FOTO-6", "nombre": "pHmetro"},
        headers=contexto["headers"],
    ).json()
    token = client.get(f"/api/v1/equipos/{equipo['id']}/qr", headers=contexto["headers"]).json()["token"]

    publico = client.get(f"/api/v1/publico/qr/{token}")
    assert publico.status_code == 200
    assert publico.json()["foto_url"] is None
