"""RN-DOC-03 (docs/07-reglas-de-negocio.md): un documento en papelera puede
restaurarse dentro de una ventana configurable (por defecto 30 días);
pasado ese plazo, pasa a purga automática programada. Documentada desde el
Sprint 5 pero nunca conectada — `restaurar()` no tenía límite de tiempo y no
existía ningún job de purga (ver Sprint 19, docs/18-sprints.md).

Corre contra Postgres y MinIO reales (mismo criterio que
test_documentos_sprint5.py) — la ventana se simula recorriendo `eliminado_en`
hacia atrás directamente en la base de datos, no esperando días reales."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from minio.error import S3Error
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.database import set_tenant_context
from app.main import app
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.configuracion.infrastructure.repositories import ConfiguracionRepositorySQLAlchemy
from app.modules.documentos.application.documento_service import DocumentoService
from app.modules.documentos.infrastructure.models import Documento
from app.modules.documentos.infrastructure.repositories import (
    CarpetaRepositorySQLAlchemy,
    DocumentoRepositorySQLAlchemy,
    EtiquetaRepositorySQLAlchemy,
    VersionDocumentoRepositorySQLAlchemy,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-doc19-{sufijo}"
    laboratorio_id, _, correo, password = crear_laboratorio_con_admin(
        "Lab Doc19", slug, f"admin-{sufijo}@doc19.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {
        "laboratorio_id": laboratorio_id,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _subir_archivo(client: TestClient, headers: dict, nombre_archivo: str = "manual.pdf") -> dict:
    contenido = b"%PDF-1.4 contenido de prueba RN-DOC-03"
    solicitud = client.post(
        "/api/v1/documentos/upload-url",
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
    assert respuesta_put.status_code in (200, 204)
    return {
        "object_key": datos["object_key"],
        "nombre_archivo": nombre_archivo,
        "tamano_bytes": len(contenido),
        "tipo_mime": "application/pdf",
    }


def _crear_documento(client: TestClient, headers: dict, nombre_archivo: str = "manual.pdf") -> dict:
    archivo = _subir_archivo(client, headers, nombre_archivo)
    respuesta = client.post(
        "/api/v1/documentos", json={"nombre": "Manual de usuario", "archivo": archivo}, headers=headers
    )
    assert respuesta.status_code == 201, respuesta.text
    documento = respuesta.json()
    documento["object_key"] = archivo["object_key"]
    return documento


def _backdate_eliminado_en(
    db: Session, laboratorio_id: uuid.UUID, documento_id: str, dias_atras: int
) -> None:
    set_tenant_context(db, laboratorio_id)
    fecha = datetime.now(UTC) - timedelta(days=dias_atras)
    db.execute(update(Documento).where(Documento.id == uuid.UUID(documento_id)).values(eliminado_en=fecha))
    db.commit()


def _documento_service(db: Session) -> DocumentoService:
    return DocumentoService(
        DocumentoRepositorySQLAlchemy(db),
        VersionDocumentoRepositorySQLAlchemy(db),
        CarpetaRepositorySQLAlchemy(db),
        EtiquetaRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
        AlmacenamientoMinIO(get_settings().minio_bucket_documentos),
        ConfiguracionRepositorySQLAlchemy(db),
    )


def test_no_puede_restaurar_pasada_la_ventana_de_retencion(
    client: TestClient, contexto: dict, db: Session
):
    headers = contexto["headers"]
    documento = _crear_documento(client, headers)
    eliminado = client.delete(f"/api/v1/documentos/{documento['id']}", headers=headers)
    assert eliminado.status_code == 204

    _backdate_eliminado_en(db, contexto["laboratorio_id"], documento["id"], dias_atras=31)

    respuesta = client.post(f"/api/v1/documentos/{documento['id']}/restaurar", headers=headers)

    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json()["error"]["codigo"] == "papelera_ventana_expirada"


def test_puede_restaurar_exactamente_en_el_limite_de_la_ventana(
    client: TestClient, contexto: dict, db: Session
):
    """El límite es inclusivo — 30 días exactos con la retención por
    defecto de 30 todavía debe permitir restaurar."""
    headers = contexto["headers"]
    documento = _crear_documento(client, headers)
    client.delete(f"/api/v1/documentos/{documento['id']}", headers=headers)

    _backdate_eliminado_en(db, contexto["laboratorio_id"], documento["id"], dias_atras=30)

    respuesta = client.post(f"/api/v1/documentos/{documento['id']}/restaurar", headers=headers)
    assert respuesta.status_code == 204, respuesta.text


def test_ventana_de_retencion_es_configurable_por_laboratorio(
    client: TestClient, contexto: dict, db: Session
):
    headers = contexto["headers"]
    configurar = client.patch(
        "/api/v1/configuracion/umbrales",
        json={
            "umbral_alerta_calibracion_dias": 30,
            "umbral_alerta_mantenimiento_dias": 15,
            "umbral_alerta_documento_dias": 30,
            "dias_retencion_papelera_documentos": 5,
        },
        headers=headers,
    )
    assert configurar.status_code == 200, configurar.text

    documento = _crear_documento(client, headers)
    client.delete(f"/api/v1/documentos/{documento['id']}", headers=headers)
    _backdate_eliminado_en(db, contexto["laboratorio_id"], documento["id"], dias_atras=6)

    respuesta = client.post(f"/api/v1/documentos/{documento['id']}/restaurar", headers=headers)
    assert respuesta.status_code == 409, respuesta.text


def test_purga_elimina_expirados_y_preserva_activos_y_recientes(
    client: TestClient, contexto: dict, db: Session
):
    headers = contexto["headers"]
    laboratorio_id = contexto["laboratorio_id"]

    activo = _crear_documento(client, headers, "activo.pdf")

    reciente = _crear_documento(client, headers, "reciente.pdf")
    client.delete(f"/api/v1/documentos/{reciente['id']}", headers=headers)
    _backdate_eliminado_en(db, laboratorio_id, reciente["id"], dias_atras=5)

    expirado = _crear_documento(client, headers, "expirado.pdf")
    client.delete(f"/api/v1/documentos/{expirado['id']}", headers=headers)
    _backdate_eliminado_en(db, laboratorio_id, expirado["id"], dias_atras=31)

    set_tenant_context(db, laboratorio_id)
    purgados = _documento_service(db).purgar_papelera_vencida(laboratorio_id)
    db.commit()
    assert purgados == 1

    # El activo ni el reciente se tocan.
    assert client.get(f"/api/v1/documentos/{activo['id']}", headers=headers).status_code == 200
    assert (
        client.post(f"/api/v1/documentos/{reciente['id']}/restaurar", headers=headers).status_code == 204
    )

    # El expirado ya no existe en absoluto — ni restaurable ni visible.
    assert (
        client.post(f"/api/v1/documentos/{expirado['id']}/restaurar", headers=headers).status_code == 404
    )
    papelera = client.get("/api/v1/documentos/papelera", headers=headers)
    assert expirado["id"] not in {d["id"] for d in papelera.json()}

    almacenamiento = AlmacenamientoMinIO(get_settings().minio_bucket_documentos)
    with pytest.raises(S3Error):
        almacenamiento.descargar_bytes(expirado["object_key"])
