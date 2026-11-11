"""Accesorios y manuales por tipo de equipo — Fase 2 de hojas de vida
(docs/25-diseno-tecnico-hojas-de-vida.md, migración 0020)."""

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
    slug = f"lab-acc-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab Accesorios", slug, f"admin-{sufijo}@acc.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"headers": {"Authorization": f"Bearer {login.json()['access_token']}"}}


def _crear_equipo(client: TestClient, headers: dict, codigo: str = "EQ-ACC-1") -> str:
    creado = client.post(
        "/api/v1/equipos", json={"codigo_interno": codigo, "nombre": "Autoclave"}, headers=headers
    )
    assert creado.status_code == 201, creado.text
    return creado.json()["id"]


# ---- Accesorios -------------------------------------------------------------------


def test_listar_accesorios_de_equipo_nuevo_vacio(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])
    respuesta = client.get(f"/api/v1/equipos/{equipo_id}/accesorios", headers=contexto["headers"])
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_crear_listar_actualizar_eliminar_accesorio(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])

    creado = client.post(
        f"/api/v1/equipos/{equipo_id}/accesorios",
        json={"cantidad": 2, "descripcion": "Bandeja de esterilización", "observaciones": "Acero inoxidable"},
        headers=contexto["headers"],
    )
    assert creado.status_code == 201, creado.text
    accesorio_id = creado.json()["id"]

    listado = client.get(f"/api/v1/equipos/{equipo_id}/accesorios", headers=contexto["headers"])
    assert len(listado.json()) == 1
    assert listado.json()[0]["descripcion"] == "Bandeja de esterilización"

    editado = client.patch(
        f"/api/v1/equipos/{equipo_id}/accesorios/{accesorio_id}",
        json={"cantidad": 3, "descripcion": "Bandeja de esterilización grande", "observaciones": None},
        headers=contexto["headers"],
    )
    assert editado.status_code == 200
    assert editado.json()["cantidad"] == 3
    assert editado.json()["observaciones"] is None

    eliminado = client.delete(
        f"/api/v1/equipos/{equipo_id}/accesorios/{accesorio_id}", headers=contexto["headers"]
    )
    assert eliminado.status_code == 204

    listado_final = client.get(f"/api/v1/equipos/{equipo_id}/accesorios", headers=contexto["headers"])
    assert listado_final.json() == []


def test_crear_accesorio_sin_descripcion_rechazado(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])
    respuesta = client.post(
        f"/api/v1/equipos/{equipo_id}/accesorios", json={"descripcion": "   "}, headers=contexto["headers"]
    )
    assert respuesta.status_code == 422


def test_crear_accesorio_con_cantidad_invalida_rechazado(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])
    respuesta = client.post(
        f"/api/v1/equipos/{equipo_id}/accesorios",
        json={"cantidad": 0, "descripcion": "Accesorio"},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "cantidad_invalida"


def test_accesorio_de_otro_equipo_404(client: TestClient, contexto: dict):
    equipo_1 = _crear_equipo(client, contexto["headers"], "EQ-ACC-OTRO-1")
    equipo_2 = _crear_equipo(client, contexto["headers"], "EQ-ACC-OTRO-2")

    accesorio = client.post(
        f"/api/v1/equipos/{equipo_1}/accesorios",
        json={"descripcion": "Solo de equipo 1"},
        headers=contexto["headers"],
    ).json()

    respuesta = client.patch(
        f"/api/v1/equipos/{equipo_2}/accesorios/{accesorio['id']}",
        json={"descripcion": "Intento desde otro equipo"},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "accesorio_no_encontrado"


# ---- Manuales ---------------------------------------------------------------------


def test_listar_manuales_de_equipo_nuevo_vacio(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])
    respuesta = client.get(f"/api/v1/equipos/{equipo_id}/manuales", headers=contexto["headers"])
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def _subir_manual_para_equipo(client: TestClient, headers: dict) -> str:
    solicitud = client.post(
        "/api/v1/equipos/upload-url/manual",
        json={"nombre_archivo": "manual.pdf", "tipo_mime": "application/pdf", "tamano_bytes": 100},
        headers=headers,
    )
    assert solicitud.status_code == 200, solicitud.text
    datos = solicitud.json()
    respuesta_put = httpx.put(
        datos["url_subida"], content=b"%PDF-1.4 contenido", headers={"Content-Type": "application/pdf"}
    )
    assert respuesta_put.status_code in (200, 204)
    return datos["object_key"]


def test_guardar_y_listar_manual_por_tipo(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])
    object_key = _subir_manual_para_equipo(client, contexto["headers"])

    guardado = client.put(
        f"/api/v1/equipos/{equipo_id}/manuales/manual_operacion",
        json={"disponible": True, "idioma": "espanol", "object_key": object_key},
        headers=contexto["headers"],
    )
    assert guardado.status_code == 200, guardado.text
    assert guardado.json()["tipo"] == "manual_operacion"
    assert guardado.json()["disponible"] is True
    assert guardado.json()["url"] is not None

    listado = client.get(f"/api/v1/equipos/{equipo_id}/manuales", headers=contexto["headers"])
    assert len(listado.json()) == 1
    assert listado.json()[0]["tipo"] == "manual_operacion"


def test_guardar_manual_dos_veces_mismo_tipo_actualiza_no_duplica(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])

    client.put(
        f"/api/v1/equipos/{equipo_id}/manuales/manual_servicio",
        json={"disponible": True, "idioma": "espanol"},
        headers=contexto["headers"],
    )
    segunda = client.put(
        f"/api/v1/equipos/{equipo_id}/manuales/manual_servicio",
        json={"disponible": True, "idioma": "ingles"},
        headers=contexto["headers"],
    )
    assert segunda.status_code == 200
    assert segunda.json()["idioma"] == "ingles"

    listado = client.get(f"/api/v1/equipos/{equipo_id}/manuales", headers=contexto["headers"])
    assert len(listado.json()) == 1
    assert listado.json()[0]["idioma"] == "ingles"


def test_guardar_manual_tipo_invalido_rechazado(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])
    respuesta = client.put(
        f"/api/v1/equipos/{equipo_id}/manuales/manual_fantasma",
        json={"disponible": True},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "tipo_manual_invalido"


def test_guardar_manual_idioma_invalido_rechazado(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])
    respuesta = client.put(
        f"/api/v1/equipos/{equipo_id}/manuales/manual_partes",
        json={"disponible": True, "idioma": "frances"},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "idioma_manual_invalido"


def test_duplicar_equipo_copia_manuales_comparte_object_key(client: TestClient, contexto: dict):
    """RN-EQ-04 extendida (Fase 2) — el manual describe el MODELO y se
    copia, compartiendo el `object_key` con el original (no se duplica el
    objeto en MinIO — ver el docstring de `EquipoService.duplicar`)."""
    equipo_id = _crear_equipo(client, contexto["headers"], "EQ-MAN-DUP")
    object_key = _subir_manual_para_equipo(client, contexto["headers"])
    client.put(
        f"/api/v1/equipos/{equipo_id}/manuales/manual_instalacion",
        json={"disponible": True, "object_key": object_key},
        headers=contexto["headers"],
    )

    copia = client.post(f"/api/v1/equipos/{equipo_id}/duplicar", headers=contexto["headers"])
    assert copia.status_code == 201, copia.text

    manuales_copia = client.get(
        f"/api/v1/equipos/{copia.json()['id']}/manuales", headers=contexto["headers"]
    ).json()
    assert len(manuales_copia) == 1
    assert manuales_copia[0]["object_key"] == object_key
