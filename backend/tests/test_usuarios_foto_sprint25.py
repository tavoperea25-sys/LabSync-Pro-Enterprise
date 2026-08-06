"""RF-CFG-01 (docs/03-requerimientos-funcionales.md, Módulo 14): "Editar
datos de perfil propio (nombre, correo, contraseña, foto)". Nombre, correo y
contraseña ya estaban conectados desde el Sprint 12 — "foto" no tenía ni
columna en base de datos, a diferencia del logo institucional
(`laboratorios.logo_object_key`) o la fotografía de equipos
(`equipos.foto_url`, Sprint 24). Ver Sprint 25, docs/18-sprints.md."""

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
    slug = f"lab-foto25-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab Foto25", slug, f"admin-{sufijo}@foto25.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {
        "slug": slug,
        "correo": correo,
        "password": password,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _subir_foto(
    client: TestClient, headers: dict, nombre_archivo: str = "perfil.jpg", contenido: bytes = b"\xff\xd8\xff"
) -> str:
    solicitud = client.post(
        "/api/v1/usuarios/me/upload-url/foto",
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
        "/api/v1/usuarios/me/upload-url/foto",
        json={"nombre_archivo": "documento.pdf", "tipo_mime": "application/pdf", "tamano_bytes": 100},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "formato_foto_no_soportado"


def test_solicitar_url_foto_demasiado_grande(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/usuarios/me/upload-url/foto",
        json={"nombre_archivo": "grande.jpg", "tipo_mime": "image/jpeg", "tamano_bytes": 3 * 1024 * 1024},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "foto_demasiado_grande"


def test_perfil_sin_foto_expone_foto_url_null(client: TestClient, contexto: dict):
    perfil = client.get("/api/v1/auth/me", headers=contexto["headers"])
    assert perfil.status_code == 200
    assert perfil.json()["foto_url"] is None


def test_actualizar_perfil_con_foto_expone_url_resuelta(client: TestClient, contexto: dict):
    object_key = _subir_foto(client, contexto["headers"])

    actualizado = client.patch(
        "/api/v1/usuarios/me",
        json={
            "nombre_completo": "Admin Con Foto",
            "correo": contexto["correo"],
            "foto_object_key": object_key,
        },
        headers=contexto["headers"],
    )
    assert actualizado.status_code == 200, actualizado.text
    assert actualizado.json()["foto_url"] is not None

    perfil = client.get("/api/v1/auth/me", headers=contexto["headers"])
    assert perfil.json()["foto_url"] is not None


def test_login_y_refresh_exponen_foto_url_actualizada(client: TestClient, contexto: dict):
    object_key = _subir_foto(client, contexto["headers"])
    client.patch(
        "/api/v1/usuarios/me",
        json={
            "nombre_completo": "Admin Con Foto",
            "correo": contexto["correo"],
            "foto_object_key": object_key,
        },
        headers=contexto["headers"],
    )

    login = client.post(
        "/api/v1/auth/login",
        json={
            "laboratorio_slug": contexto["slug"],
            "correo": contexto["correo"],
            "password": contexto["password"],
        },
    )
    assert login.status_code == 200
    assert login.json()["usuario"]["foto_url"] is not None


def test_actualizar_perfil_sin_tocar_foto_la_conserva(client: TestClient, contexto: dict):
    """Guardar el formulario sin subir una foto nueva no debe borrar la
    existente — mismo criterio ya aplicado al logo institucional."""
    object_key = _subir_foto(client, contexto["headers"])
    client.patch(
        "/api/v1/usuarios/me",
        json={
            "nombre_completo": "Admin Con Foto",
            "correo": contexto["correo"],
            "foto_object_key": object_key,
        },
        headers=contexto["headers"],
    )

    segunda_edicion = client.patch(
        "/api/v1/usuarios/me",
        json={
            "nombre_completo": "Admin Con Foto Editado Otra Vez",
            "correo": contexto["correo"],
            "foto_object_key": object_key,
        },
        headers=contexto["headers"],
    )
    assert segunda_edicion.status_code == 200
    assert segunda_edicion.json()["foto_url"] is not None


def test_respuestas_exponen_foto_object_key_estable(client: TestClient, contexto: dict):
    """Regresión (mismo patrón detectado en Equipos, Sprint 24): sin
    `foto_object_key` expuesto junto a `foto_url` (que expira), el frontend
    no tiene forma de reenviar "la foto actual sin tocarla" en un PATCH que
    edita otro campo — terminaría omitiendo el campo, y el backend lo
    interpretaría como "borrar la foto"."""
    object_key = _subir_foto(client, contexto["headers"])
    actualizado = client.patch(
        "/api/v1/usuarios/me",
        json={
            "nombre_completo": "Admin Con Foto",
            "correo": contexto["correo"],
            "foto_object_key": object_key,
        },
        headers=contexto["headers"],
    )
    assert actualizado.json()["foto_object_key"] == object_key

    perfil = client.get("/api/v1/auth/me", headers=contexto["headers"])
    assert perfil.json()["foto_object_key"] == object_key

    login = client.post(
        "/api/v1/auth/login",
        json={
            "laboratorio_slug": contexto["slug"],
            "correo": contexto["correo"],
            "password": contexto["password"],
        },
    )
    assert login.json()["usuario"]["foto_object_key"] == object_key
