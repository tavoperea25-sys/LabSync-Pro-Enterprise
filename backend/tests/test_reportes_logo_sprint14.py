"""Pruebas de Sprint 14: logo institucional embebido en el encabezado de
los reportes PDF (RF-CFG-04, `exportadores.py` y
`reporte_service.py::obtener_logo_bytes`)."""

from __future__ import annotations

import io
import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.main import app
from app.modules.auth.domain.entities import Laboratorio
from app.modules.reportes.application.reporte_service import obtener_logo_bytes
from app.modules.reportes.infrastructure.exportadores import exportar_reporte_tabular


def _png_valido() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (40, 40), color=(15, 81, 50)).save(buffer, format="PNG")
    return buffer.getvalue()


# ---- exportar_reporte_tabular con logo_bytes (público, sin red) -------------


def test_exportar_pdf_sin_logo_produce_pdf_valido() -> None:
    contenido = exportar_reporte_tabular("inventario", "pdf", [], datetime.utcnow(), logo_bytes=None)
    assert contenido.startswith(b"%PDF")


def test_exportar_pdf_con_logo_valido_produce_pdf_valido() -> None:
    contenido = exportar_reporte_tabular(
        "inventario", "pdf", [], datetime.utcnow(), logo_bytes=_png_valido()
    )
    assert contenido.startswith(b"%PDF")


def test_exportar_pdf_con_logo_invalido_degrada_sin_lanzar() -> None:
    """Bytes que no son una imagen decodificable no deben tumbar la
    generación completa del reporte — el logo es un adorno del encabezado."""
    contenido = exportar_reporte_tabular(
        "inventario", "pdf", [], datetime.utcnow(), logo_bytes=b"esto no es una imagen"
    )
    assert contenido.startswith(b"%PDF")


# ---- obtener_logo_bytes (repositorio real, MinIO real) ----------------------


class _LaboratorioRepoFalso:
    def __init__(self, laboratorio: Laboratorio | None) -> None:
        self._laboratorio = laboratorio

    def obtener_por_id(self, laboratorio_id: uuid.UUID) -> Laboratorio | None:
        return self._laboratorio

    def existe_activo(self, laboratorio_id: uuid.UUID) -> bool:
        return True

    def resolver_id_por_slug(self, slug: str) -> uuid.UUID | None:
        return None

    def actualizar(self, laboratorio: Laboratorio) -> Laboratorio:
        return laboratorio


class _AlmacenamientoFalso:
    def __init__(self, contenido: bytes | None = None, lanza: bool = False) -> None:
        self._contenido = contenido
        self._lanza = lanza

    def descargar_bytes(self, object_key: str) -> bytes:
        if self._lanza:
            raise RuntimeError("MinIO no disponible (simulado)")
        assert self._contenido is not None
        return self._contenido


def test_obtener_logo_bytes_sin_logo_configurado_devuelve_none() -> None:
    laboratorio_id = uuid.uuid4()
    laboratorio = Laboratorio(id=laboratorio_id, nombre="X", slug="x", logo_object_key=None)
    resultado = obtener_logo_bytes(_LaboratorioRepoFalso(laboratorio), _AlmacenamientoFalso(), laboratorio_id)
    assert resultado is None


def test_obtener_logo_bytes_con_logo_configurado_lo_descarga() -> None:
    laboratorio_id = uuid.uuid4()
    laboratorio = Laboratorio(id=laboratorio_id, nombre="X", slug="x", logo_object_key="logo.png")
    contenido = _png_valido()
    resultado = obtener_logo_bytes(
        _LaboratorioRepoFalso(laboratorio), _AlmacenamientoFalso(contenido=contenido), laboratorio_id
    )
    assert resultado == contenido


def test_obtener_logo_bytes_degrada_a_none_si_falla_la_descarga() -> None:
    """El logo es un adorno del encabezado — un MinIO caído o un objeto
    borrado no debe tumbar la generación completa del reporte."""
    laboratorio_id = uuid.uuid4()
    laboratorio = Laboratorio(id=laboratorio_id, nombre="X", slug="x", logo_object_key="logo.png")
    resultado = obtener_logo_bytes(
        _LaboratorioRepoFalso(laboratorio), _AlmacenamientoFalso(lanza=True), laboratorio_id
    )
    assert resultado is None


# ---- Extremo a extremo, vía API real -----------------------------------------


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-logo14-{sufijo}"
    laboratorio_id, _admin_id, correo, password = crear_laboratorio_con_admin(
        "Lab Logo14", slug, f"admin-{sufijo}@logo14.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {
        "laboratorio_id": laboratorio_id,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def test_generar_reporte_pdf_sin_logo_configurado_funciona(client: TestClient, contexto: dict) -> None:
    respuesta = client.post(
        "/api/v1/reportes/generar",
        json={"tipo": "inventario", "formato": "pdf", "filtros": {}},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["estado"] == "listo"


def test_generar_reporte_pdf_con_logo_configurado_funciona(client: TestClient, contexto: dict) -> None:
    headers = contexto["headers"]

    # Sube el logo directo por MinIO (bypass de la URL prefirmada — en un
    # test de backend no hay navegador que haga el PUT) y lo asocia al
    # laboratorio igual que haría el endpoint real.
    almacenamiento_logos = AlmacenamientoMinIO(get_settings().minio_bucket_logos)
    almacenamiento_logos.asegurar_bucket()
    object_key = f"test-{uuid.uuid4()}.png"
    almacenamiento_logos.subir_bytes(object_key, _png_valido(), "image/png")

    actualizar = client.patch(
        "/api/v1/configuracion/institucion",
        json={"nombre": "Lab Logo14", "logo_object_key": object_key},
        headers=headers,
    )
    assert actualizar.status_code == 200

    respuesta = client.post(
        "/api/v1/reportes/generar",
        json={"tipo": "inventario", "formato": "pdf", "filtros": {}},
        headers=headers,
    )
    assert respuesta.status_code == 201
    reporte = respuesta.json()
    assert reporte["estado"] == "listo"

    descarga = client.get(f"/api/v1/reportes/{reporte['id']}/descargar", headers=headers)
    assert descarga.status_code == 200
    assert descarga.json()["url"].startswith("http")
