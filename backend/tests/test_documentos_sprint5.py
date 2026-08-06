"""Pruebas de Sprint 5: subida vía URL prefirmada (RF-DOC-01/02), versionado
(RF-DOC-11), carpetas (RF-DOC-03), etiquetas/favoritos (RF-DOC-04/05),
previsualización/descarga (RF-DOC-07/08), mover/copiar (RF-DOC-09) y
papelera (RF-DOC-10).

Corren contra el MinIO real de docker-compose (mismo criterio que Postgres
en conftest.py: RLS/almacenamiento no se prueban con mocks/SQLite)."""

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
    slug = f"lab-doc5-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab Doc5", slug, f"admin-{sufijo}@doc5.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _subir_archivo(
    client: TestClient,
    headers: dict,
    nombre_archivo: str = "manual.pdf",
    tipo_mime: str = "application/pdf",
    contenido: bytes = b"%PDF-1.4 contenido de prueba",
) -> dict:
    solicitud = client.post(
        "/api/v1/documentos/upload-url",
        json={"nombre_archivo": nombre_archivo, "tipo_mime": tipo_mime, "tamano_bytes": len(contenido)},
        headers=headers,
    )
    assert solicitud.status_code == 200, solicitud.text
    datos = solicitud.json()

    respuesta_put = httpx.put(datos["url_subida"], content=contenido, headers={"Content-Type": tipo_mime})
    assert respuesta_put.status_code in (200, 204), respuesta_put.text

    return {
        "object_key": datos["object_key"],
        "nombre_archivo": nombre_archivo,
        "tamano_bytes": len(contenido),
        "tipo_mime": tipo_mime,
    }


def _crear_documento(client: TestClient, headers: dict, **overrides) -> dict:
    archivo = _subir_archivo(client, headers)
    payload = {"nombre": "Manual de usuario", "archivo": archivo, **overrides}
    respuesta = client.post("/api/v1/documentos", json=payload, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_flujo_completo_subida_y_lectura(client: TestClient, headers_autenticados: dict):
    documento = _crear_documento(client, headers_autenticados)

    detalle = client.get(f"/api/v1/documentos/{documento['id']}", headers=headers_autenticados)
    assert detalle.status_code == 200
    cuerpo = detalle.json()
    assert len(cuerpo["versiones"]) == 1
    assert cuerpo["versiones"][0]["numero_version"] == 1
    assert cuerpo["es_favorito"] is False

    descarga = client.get(
        f"/api/v1/documentos/{documento['id']}/versiones/1/download-url", headers=headers_autenticados
    )
    assert descarga.status_code == 200
    assert descarga.json()["url"].startswith("http")

    vista_previa = client.get(
        f"/api/v1/documentos/{documento['id']}/vista-previa", headers=headers_autenticados
    )
    assert vista_previa.status_code == 200
    assert vista_previa.json()["url"] is not None  # PDF tiene previsualización nativa


def test_formato_no_permitido_rechaza_url_subida(client: TestClient, headers_autenticados: dict):
    respuesta = client.post(
        "/api/v1/documentos/upload-url",
        json={"nombre_archivo": "virus.exe", "tipo_mime": "application/octet-stream", "tamano_bytes": 100},
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "formato_no_permitido"


def test_archivo_demasiado_grande_rechaza_url_subida(client: TestClient, headers_autenticados: dict):
    respuesta = client.post(
        "/api/v1/documentos/upload-url",
        json={
            "nombre_archivo": "grande.pdf",
            "tipo_mime": "application/pdf",
            "tamano_bytes": 60 * 1024 * 1024,
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "archivo_demasiado_grande"


def test_subir_nueva_version_actualiza_vigente(client: TestClient, headers_autenticados: dict):
    documento = _crear_documento(client, headers_autenticados)
    archivo_v2 = _subir_archivo(client, headers_autenticados, contenido=b"%PDF-1.4 version 2")

    respuesta = client.post(
        f"/api/v1/documentos/{documento['id']}/versiones", json=archivo_v2, headers=headers_autenticados
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["numero_version"] == 2

    detalle = client.get(f"/api/v1/documentos/{documento['id']}", headers=headers_autenticados).json()
    assert len(detalle["versiones"]) == 2
    assert detalle["version_vigente_id"] != documento["version_vigente_id"]


def test_renombrar_y_mover_documento(client: TestClient, headers_autenticados: dict):
    carpeta = client.post("/api/v1/carpetas", json={"nombre": "SOPs"}, headers=headers_autenticados).json()
    documento = _crear_documento(client, headers_autenticados)

    renombrado = client.patch(
        f"/api/v1/documentos/{documento['id']}",
        json={"nombre": "Manual renombrado"},
        headers=headers_autenticados,
    )
    assert renombrado.status_code == 200
    assert renombrado.json()["nombre"] == "Manual renombrado"

    movido = client.patch(
        f"/api/v1/documentos/{documento['id']}",
        json={"mover_a_carpeta": True, "carpeta_id": carpeta["id"]},
        headers=headers_autenticados,
    )
    assert movido.status_code == 200
    assert movido.json()["carpeta_id"] == carpeta["id"]


def test_copiar_documento_genera_version_propia(client: TestClient, headers_autenticados: dict):
    original = _crear_documento(client, headers_autenticados)

    copia = client.post(f"/api/v1/documentos/{original['id']}/copiar", headers=headers_autenticados)
    assert copia.status_code == 201
    cuerpo = copia.json()
    assert cuerpo["id"] != original["id"]
    assert cuerpo["nombre"] == "Manual de usuario (copia)"

    descarga_copia = client.get(
        f"/api/v1/documentos/{cuerpo['id']}/versiones/1/download-url", headers=headers_autenticados
    )
    assert descarga_copia.status_code == 200


def test_papelera_y_restaurar(client: TestClient, headers_autenticados: dict):
    documento = _crear_documento(client, headers_autenticados)

    eliminado = client.delete(f"/api/v1/documentos/{documento['id']}", headers=headers_autenticados)
    assert eliminado.status_code == 204

    tras_eliminar = client.get(f"/api/v1/documentos/{documento['id']}", headers=headers_autenticados)
    assert tras_eliminar.status_code == 404

    restaurado = client.post(f"/api/v1/documentos/{documento['id']}/restaurar", headers=headers_autenticados)
    assert restaurado.status_code == 204

    tras_restaurar = client.get(f"/api/v1/documentos/{documento['id']}", headers=headers_autenticados)
    assert tras_restaurar.status_code == 200


def test_favorito_alterna(client: TestClient, headers_autenticados: dict):
    documento = _crear_documento(client, headers_autenticados)

    primero = client.post(f"/api/v1/documentos/{documento['id']}/favorito", headers=headers_autenticados)
    assert primero.status_code == 200
    assert primero.json()["es_favorito"] is True

    segundo = client.post(f"/api/v1/documentos/{documento['id']}/favorito", headers=headers_autenticados)
    assert segundo.json()["es_favorito"] is False


def test_etiquetas_asignar_y_quitar(client: TestClient, headers_autenticados: dict):
    documento = _crear_documento(client, headers_autenticados)

    creada = client.post(
        f"/api/v1/documentos/{documento['id']}/etiquetas",
        json={"nombre": "ISO 15189"},
        headers=headers_autenticados,
    )
    assert creada.status_code == 201
    etiqueta_id = creada.json()["id"]

    listado = client.get(f"/api/v1/documentos/{documento['id']}/etiquetas", headers=headers_autenticados)
    assert [e["nombre"] for e in listado.json()] == ["ISO 15189"]

    quitada = client.delete(
        f"/api/v1/documentos/{documento['id']}/etiquetas/{etiqueta_id}", headers=headers_autenticados
    )
    assert quitada.status_code == 204
    assert (
        client.get(f"/api/v1/documentos/{documento['id']}/etiquetas", headers=headers_autenticados).json()
        == []
    )


def test_carpetas_rechaza_nombre_duplicado_en_misma_ubicacion(client: TestClient, headers_autenticados: dict):
    client.post("/api/v1/carpetas", json={"nombre": "Calidad"}, headers=headers_autenticados)
    duplicada = client.post("/api/v1/carpetas", json={"nombre": "Calidad"}, headers=headers_autenticados)
    assert duplicada.status_code == 409
    assert duplicada.json()["error"]["codigo"] == "nombre_carpeta_duplicado"


def test_eliminar_carpeta_no_vacia_falla_y_vacia_funciona(client: TestClient, headers_autenticados: dict):
    carpeta = client.post(
        "/api/v1/carpetas", json={"nombre": "Procedimientos"}, headers=headers_autenticados
    ).json()
    documento = _crear_documento(client, headers_autenticados, carpeta_id=carpeta["id"])

    bloqueada = client.delete(f"/api/v1/carpetas/{carpeta['id']}", headers=headers_autenticados)
    assert bloqueada.status_code == 409
    assert bloqueada.json()["error"]["codigo"] == "carpeta_no_vacia"

    # Enviar el documento a la papelera NO libera la carpeta: sigue
    # referenciándola por FK para poder restaurarse en el mismo lugar.
    client.delete(f"/api/v1/documentos/{documento['id']}", headers=headers_autenticados)
    aun_bloqueada = client.delete(f"/api/v1/carpetas/{carpeta['id']}", headers=headers_autenticados)
    assert aun_bloqueada.status_code == 409

    # Solo mover el documento (el único camino disponible en Sprint 5, ya
    # que la purga definitiva de la papelera es un job programado, no una
    # acción de usuario) deja la carpeta realmente vacía.
    client.post(f"/api/v1/documentos/{documento['id']}/restaurar", headers=headers_autenticados)
    client.patch(
        f"/api/v1/documentos/{documento['id']}",
        json={"mover_a_carpeta": True, "carpeta_id": None},
        headers=headers_autenticados,
    )
    vacia = client.delete(f"/api/v1/carpetas/{carpeta['id']}", headers=headers_autenticados)
    assert vacia.status_code == 204


def test_listar_documentos_navega_raiz_por_defecto(client: TestClient, headers_autenticados: dict):
    carpeta = client.post("/api/v1/carpetas", json={"nombre": "Otra"}, headers=headers_autenticados).json()
    _crear_documento(client, headers_autenticados, nombre="En raíz")
    _crear_documento(client, headers_autenticados, nombre="En carpeta", carpeta_id=carpeta["id"])

    raiz = client.get("/api/v1/documentos", headers=headers_autenticados).json()
    assert [d["nombre"] for d in raiz["items"]] == ["En raíz"]

    dentro = client.get(f"/api/v1/documentos?carpeta_id={carpeta['id']}", headers=headers_autenticados).json()
    assert [d["nombre"] for d in dentro["items"]] == ["En carpeta"]


def test_documentos_recientes_incluye_el_recien_creado(client: TestClient, headers_autenticados: dict):
    documento = _crear_documento(client, headers_autenticados, nombre="Reciente")
    recientes = client.get("/api/v1/documentos/recientes", headers=headers_autenticados)
    assert recientes.status_code == 200
    assert documento["id"] in [d["id"] for d in recientes.json()]


def test_papelera_lista_solo_documentos_eliminados(client: TestClient, headers_autenticados: dict):
    activo = _crear_documento(client, headers_autenticados, nombre="Activo")
    eliminado = _crear_documento(client, headers_autenticados, nombre="Eliminado")
    client.delete(f"/api/v1/documentos/{eliminado['id']}", headers=headers_autenticados)

    papelera = client.get("/api/v1/documentos/papelera", headers=headers_autenticados)
    assert papelera.status_code == 200
    ids_en_papelera = [d["id"] for d in papelera.json()]
    assert eliminado["id"] in ids_en_papelera
    assert activo["id"] not in ids_en_papelera


def test_obtener_carpeta_por_id(client: TestClient, headers_autenticados: dict):
    creada = client.post(
        "/api/v1/carpetas", json={"nombre": "Metrología"}, headers=headers_autenticados
    ).json()
    obtenida = client.get(f"/api/v1/carpetas/{creada['id']}", headers=headers_autenticados)
    assert obtenida.status_code == 200
    assert obtenida.json()["nombre"] == "Metrología"
