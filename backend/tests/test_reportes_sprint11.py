"""Pruebas de Sprint 11: módulo Reportes — generación de los 7 tipos
(RF-REP-01 a 07), exportación en cada formato (RF-REP-08), umbral
síncrono/asíncrono (RNF-PERF-04) y aislamiento por permiso.

Corren contra el MinIO real de docker-compose (mismo criterio que
tests/test_documentos_sprint5.py: RLS/almacenamiento no se prueban con
mocks/SQLite)."""

from __future__ import annotations

import uuid
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.database import set_tenant_context
from app.main import app
from app.modules.equipos.infrastructure.models import Equipo

_TIPOS_TABULARES = (
    "inventario",
    "calibraciones",
    "vencidos",
    "cumplimiento",
    "mantenimiento",
    "trazabilidad_documental",
)
_FORMATOS = ("pdf", "xlsx", "csv")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-rep11-{sufijo}"
    laboratorio_id, admin_id, correo, password = crear_laboratorio_con_admin(
        "Lab Rep11", slug, f"admin-{sufijo}@rep11.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {
        "laboratorio_id": laboratorio_id,
        "admin_id": admin_id,
        "slug": slug,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _crear_equipo(client: TestClient, headers: dict, codigo: str = "EQ-REP11", **overrides) -> dict:
    payload = {"codigo_interno": codigo, "nombre": "Equipo reportes", **overrides}
    respuesta = client.post("/api/v1/equipos", json=payload, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _generar(client: TestClient, headers: dict, tipo: str, formato: str, filtros: dict | None = None) -> dict:
    respuesta = client.post(
        "/api/v1/reportes/generar",
        json={"tipo": tipo, "formato": formato, "filtros": filtros or {}},
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _descargar_bytes(client: TestClient, headers: dict, reporte_id: str) -> bytes:
    url_resp = client.get(f"/api/v1/reportes/{reporte_id}/descargar", headers=headers)
    assert url_resp.status_code == 200, url_resp.text
    url = url_resp.json()["url"]
    assert url.startswith("http")
    contenido = httpx.get(url)
    assert contenido.status_code == 200
    return contenido.content


# ---- RF-REP-08 — tipos y formatos disponibles -------------------------------


def test_listar_tipos_reporte(client: TestClient, contexto: dict):
    respuesta = client.get("/api/v1/reportes/tipos", headers=contexto["headers"])
    assert respuesta.status_code == 200
    tipos = {t["tipo"]: t for t in respuesta.json()}
    assert set(tipos) == set(_TIPOS_TABULARES) | {"paquete_auditoria"}
    for tipo in _TIPOS_TABULARES:
        assert set(tipos[tipo]["formatos_disponibles"]) == set(_FORMATOS)
    assert tipos["paquete_auditoria"]["formatos_disponibles"] == ["pdf"]


def test_generar_reporte_tipo_invalido_falla(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/reportes/generar",
        json={"tipo": "no_existe", "formato": "pdf", "filtros": {}},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "tipo_reporte_invalido"


def test_generar_reporte_formato_no_disponible_para_tipo_falla(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/reportes/generar",
        json={"tipo": "paquete_auditoria", "formato": "xlsx", "filtros": {}},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "formato_no_disponible"


# ---- RF-REP-01 a 06 + RF-REP-08 — generación tabular sincrónica -------------


@pytest.mark.parametrize("tipo", _TIPOS_TABULARES)
@pytest.mark.parametrize("formato", _FORMATOS)
def test_generar_y_descargar_reporte_tabular(
    client: TestClient, contexto: dict, tipo: str, formato: str
):
    headers = contexto["headers"]
    _crear_equipo(client, headers, f"EQ-REP11-{tipo[:4]}-{formato}")

    reporte = _generar(client, headers, tipo, formato)
    assert reporte["estado"] == "listo"
    assert reporte["nombre_archivo"].endswith(f".{formato}")
    assert reporte["completado_en"] is not None

    contenido = _descargar_bytes(client, headers, reporte["id"])
    assert len(contenido) > 0
    if formato == "pdf":
        assert contenido.startswith(b"%PDF")
    elif formato == "xlsx":
        assert contenido.startswith(b"PK")  # firma de archivo ZIP (contenedor de .xlsx)


def test_reporte_mantenimiento_pdf_con_caracteres_no_latin1_no_revienta(
    client: TestClient, contexto: dict
):
    """Regresión: fpdf2 solo soporta Latin-1 en la fuente core Helvetica —
    un guion largo ("—") en un campo de texto libre revienta `pdf.cell()`
    con FPDFUnicodeEncodingException si no se sanitiza (ver `_texto_pdf` en
    infrastructure/exportadores.py, encontrado en pruebas manuales de esta
    misma sprint)."""
    headers = contexto["headers"]
    equipo = _crear_equipo(client, headers, "EQ-REP11-EMDASH")
    mant = client.post(
        "/api/v1/mantenimientos",
        json={
            "equipo_id": equipo["id"],
            "tipo": "correctivo",
            "fecha_programada": date.today().isoformat(),
            "tecnico_responsable_id": None,
            "descripcion": "Cambio de filtro — pieza importada, costo elevado",
            "frecuencia_meses": None,
        },
        headers=headers,
    )
    assert mant.status_code == 201, mant.text

    reporte = _generar(client, headers, "mantenimiento", "pdf")
    assert reporte["estado"] == "listo"
    contenido = _descargar_bytes(client, headers, reporte["id"])
    assert contenido.startswith(b"%PDF")


# ---- RF-REP-07 — paquete de auditoría por equipo ----------------------------


def test_generar_paquete_auditoria_sin_equipo_id_falla(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/reportes/generar",
        json={"tipo": "paquete_auditoria", "formato": "pdf", "filtros": {}},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "equipo_id_requerido"


def test_generar_paquete_auditoria_equipo_inexistente_falla(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/reportes/generar",
        json={
            "tipo": "paquete_auditoria",
            "formato": "pdf",
            "filtros": {"equipo_id": str(uuid.uuid4())},
        },
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "equipo_no_encontrado"


def test_generar_paquete_auditoria_completo(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    equipo = _crear_equipo(client, headers, "EQ-REP11-PAQ", marca="Marca—Modelo")

    calibracion = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo["id"],
            "fecha_calibracion": "2026-01-01",
            "frecuencia_meses": 12,
            "resultado": "conforme",
        },
        headers=headers,
    )
    assert calibracion.status_code == 201, calibracion.text

    mant = client.post(
        "/api/v1/mantenimientos",
        json={
            "equipo_id": equipo["id"],
            "tipo": "preventivo",
            "fecha_programada": date.today().isoformat(),
            "tecnico_responsable_id": None,
            "descripcion": "Mantenimiento preventivo anual",
            "frecuencia_meses": None,
        },
        headers=headers,
    )
    assert mant.status_code == 201, mant.text

    reporte = _generar(
        client, headers, "paquete_auditoria", "pdf", filtros={"equipo_id": equipo["id"]}
    )
    assert reporte["estado"] == "listo"
    assert reporte["filtros"] == {"equipo_id": equipo["id"]}

    contenido = _descargar_bytes(client, headers, reporte["id"])
    assert contenido.startswith(b"%PDF")


# ---- Historial y descarga ----------------------------------------------------


def test_historial_lista_reportes_generados_del_tenant(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    _crear_equipo(client, headers, "EQ-REP11-HIST")
    generado = _generar(client, headers, "inventario", "csv")

    historial = client.get("/api/v1/reportes/historial", headers=headers)
    assert historial.status_code == 200
    ids = {r["id"] for r in historial.json()}
    assert generado["id"] in ids


def test_obtener_reporte_inexistente_falla(client: TestClient, contexto: dict):
    respuesta = client.get(f"/api/v1/reportes/{uuid.uuid4()}", headers=contexto["headers"])
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "reporte_no_encontrado"


def test_descargar_reporte_inexistente_falla(client: TestClient, contexto: dict):
    respuesta = client.get(f"/api/v1/reportes/{uuid.uuid4()}/descargar", headers=contexto["headers"])
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "reporte_no_encontrado"


# ---- RNF-PERF-04 — umbral síncrono/asíncrono + worker -----------------------


def test_reporte_grande_es_asincrono_y_el_worker_lo_completa(
    client: TestClient, contexto: dict, db
):
    from app.worker.main import _procesar_reportes_pendientes

    laboratorio_id = contexto["laboratorio_id"]
    headers = contexto["headers"]

    # Se insertan >1000 equipos directamente por SQLAlchemy (bypass de la
    # API): el umbral asíncrono (RNF-PERF-04) es sobre cantidad de filas,
    # no importa cómo llegaron ahí, y hacerlo vía API sería 1001 peticiones
    # HTTP solo para preparar el escenario de la prueba.
    set_tenant_context(db, laboratorio_id)
    for i in range(1001):
        db.add(
            Equipo(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio_id,
                codigo_interno=f"EQ-BULK-{i:04d}",
                nombre=f"Equipo masivo {i}",
                estado_operativo="operativo",
            )
        )
    db.commit()

    generado = _generar(client, headers, "inventario", "csv")
    assert generado["estado"] == "pendiente"
    assert generado["nombre_archivo"] is None
    assert generado["completado_en"] is None

    # Todavía no está listo — no se puede descargar.
    aun_no = client.get(f"/api/v1/reportes/{generado['id']}/descargar", headers=headers)
    assert aun_no.status_code == 404
    assert aun_no.json()["error"]["codigo"] == "reporte_no_disponible"

    # `SET LOCAL` muere con el commit del bulk-insert — se re-fija antes de
    # invocar el mismo procesamiento que corre el proceso `worker` real
    # (ver app/worker/main.py, docstring del módulo).
    set_tenant_context(db, laboratorio_id)
    _procesar_reportes_pendientes(db, laboratorio_id)
    db.commit()

    consulta = client.get(f"/api/v1/reportes/{generado['id']}", headers=headers)
    assert consulta.status_code == 200
    assert consulta.json()["estado"] == "listo"
    assert consulta.json()["nombre_archivo"] is not None

    contenido = _descargar_bytes(client, headers, generado["id"])
    assert len(contenido) > 0


# ---- Permisos ----------------------------------------------------------------


def test_generar_reporte_requiere_permiso(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    password_tecnico = "Cl4veSegura!2026"
    rol_tecnico = next(
        r["id"] for r in client.get("/api/v1/roles", headers=headers).json() if r["nombre"] == "tecnico"
    )
    correo = f"tec-rep11-{uuid.uuid4().hex[:8]}@rep11.dev"
    creado = client.post(
        "/api/v1/usuarios",
        json={
            "nombre_completo": "Técnico sin acceso a reportes",
            "correo": correo,
            "password": password_tecnico,
            "rol_ids": [rol_tecnico],
        },
        headers=headers,
    )
    assert creado.status_code == 201, creado.text

    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": contexto["slug"], "correo": correo, "password": password_tecnico},
    )
    assert login.status_code == 200
    headers_tecnico = {"Authorization": f"Bearer {login.json()['access_token']}"}

    respuesta = client.post(
        "/api/v1/reportes/generar",
        json={"tipo": "inventario", "formato": "csv", "filtros": {}},
        headers=headers_tecnico,
    )
    assert respuesta.status_code == 403

    respuesta_historial = client.get("/api/v1/reportes/historial", headers=headers_tecnico)
    assert respuesta_historial.status_code == 403
