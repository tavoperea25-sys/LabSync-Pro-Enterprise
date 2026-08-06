"""Pruebas de Sprint 9: CRUD de eventos manuales (RF-CAL2-03) y fusión con
eventos sintetizados desde calibraciones/mantenimientos/documentos
(RF-CAL2-01)."""

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
    slug = f"lab-cal9-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab Cal9", slug, f"admin-{sufijo}@cal9.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _rango_mes(mes_de: date) -> tuple[str, str]:
    desde = mes_de.replace(day=1)
    hasta = date(mes_de.year + (mes_de.month == 12), mes_de.month % 12 + 1, 1) - timedelta(days=1)
    return f"{desde.isoformat()}T00:00:00Z", f"{hasta.isoformat()}T23:59:59Z"


def _listar(client: TestClient, headers: dict, desde: str, hasta: str, **extra) -> list[dict]:
    respuesta = client.get(
        "/api/v1/calendario/eventos", params={"desde": desde, "hasta": hasta, **extra}, headers=headers
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# ---- CRUD de eventos manuales -----------------------------------------------


def test_crear_evento_institucional_aparece_en_el_listado(client: TestClient, headers_autenticados: dict):
    desde, hasta = _rango_mes(date(2026, 8, 1))
    creado = client.post(
        "/api/v1/calendario/eventos",
        json={"tipo": "institucional", "titulo": "Jornada de bioseguridad", "fecha": "2026-08-10T09:00:00Z"},
        headers=headers_autenticados,
    )
    assert creado.status_code == 201, creado.text
    cuerpo = creado.json()
    assert cuerpo["editable"] is True

    eventos = _listar(client, headers_autenticados, desde, hasta)
    assert any(e["id"] == cuerpo["id"] for e in eventos)


def test_crear_evento_de_tipo_sintetizado_falla(client: TestClient, headers_autenticados: dict):
    respuesta = client.post(
        "/api/v1/calendario/eventos",
        json={"tipo": "calibracion", "titulo": "No debería poder crearse", "fecha": "2026-08-10T09:00:00Z"},
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "tipo_invalido"


def test_actualizar_y_eliminar_evento_manual(client: TestClient, headers_autenticados: dict):
    creado = client.post(
        "/api/v1/calendario/eventos",
        json={"tipo": "capacitacion", "titulo": "Capacitación RCP", "fecha": "2026-08-05T14:00:00Z"},
        headers=headers_autenticados,
    ).json()

    actualizado = client.patch(
        f"/api/v1/calendario/eventos/{creado['id']}",
        json={
            "tipo": "capacitacion",
            "titulo": "Capacitación RCP (reprogramada)",
            "fecha": "2026-08-06T14:00:00Z",
        },
        headers=headers_autenticados,
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["titulo"] == "Capacitación RCP (reprogramada)"

    eliminado = client.delete(f"/api/v1/calendario/eventos/{creado['id']}", headers=headers_autenticados)
    assert eliminado.status_code == 204

    desde, hasta = _rango_mes(date(2026, 8, 1))
    eventos = _listar(client, headers_autenticados, desde, hasta)
    assert all(e["id"] != creado["id"] for e in eventos)


def test_eliminar_evento_inexistente_devuelve_404(client: TestClient, headers_autenticados: dict):
    respuesta = client.delete(f"/api/v1/calendario/eventos/{uuid.uuid4()}", headers=headers_autenticados)
    assert respuesta.status_code == 404


# ---- Fusión con eventos sintetizados (RF-CAL2-01) ---------------------------


def _crear_equipo(client: TestClient, headers: dict, codigo: str) -> str:
    respuesta = client.post(
        "/api/v1/equipos", json={"codigo_interno": codigo, "nombre": "Balanza analítica"}, headers=headers
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def test_calibracion_proxima_aparece_como_evento_sintetizado(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-CAL9-1")
    creada = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": "2026-06-15",
            "frecuencia_meses": 2,
            "resultado": "conforme",
        },
        headers=headers_autenticados,
    )
    assert creada.status_code == 201, creada.text
    assert creada.json()["proxima_fecha"] == "2026-08-15"

    desde, hasta = _rango_mes(date(2026, 8, 1))
    eventos = _listar(client, headers_autenticados, desde, hasta, tipo="calibracion")
    assert len(eventos) == 1
    assert eventos[0]["origen_tipo"] == "equipo"
    assert eventos[0]["origen_id"] == equipo_id
    assert eventos[0]["editable"] is False


def test_mantenimiento_programado_aparece_como_evento_sintetizado(
    client: TestClient, headers_autenticados: dict
):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-CAL9-2")
    mant = client.post(
        "/api/v1/mantenimientos",
        json={
            "equipo_id": equipo_id,
            "tipo": "preventivo",
            "fecha_programada": "2026-08-20",
            "descripcion": "Mantenimiento de calendario Sprint 9",
        },
        headers=headers_autenticados,
    )
    assert mant.status_code == 201, mant.text

    desde, hasta = _rango_mes(date(2026, 8, 1))
    eventos = _listar(client, headers_autenticados, desde, hasta, tipo="mantenimiento")
    assert len(eventos) == 1
    assert eventos[0]["origen_id"] == equipo_id
    assert "Sprint 9" in eventos[0]["descripcion"]


def test_documento_por_vencer_aparece_como_evento_sintetizado(client: TestClient, headers_autenticados: dict):
    contenido = b"%PDF-1.4 prueba calendario"
    solicitud = client.post(
        "/api/v1/documentos/upload-url",
        json={
            "nombre_archivo": "procedimiento.pdf",
            "tipo_mime": "application/pdf",
            "tamano_bytes": len(contenido),
        },
        headers=headers_autenticados,
    )
    datos = solicitud.json()
    httpx.put(datos["url_subida"], content=contenido, headers={"Content-Type": "application/pdf"})
    creado = client.post(
        "/api/v1/documentos",
        json={
            "nombre": "Procedimiento de calendario",
            "fecha_vencimiento": "2026-08-25",
            "archivo": {
                "object_key": datos["object_key"],
                "nombre_archivo": "procedimiento.pdf",
                "tamano_bytes": len(contenido),
                "tipo_mime": "application/pdf",
            },
        },
        headers=headers_autenticados,
    )
    assert creado.status_code == 201, creado.text

    desde, hasta = _rango_mes(date(2026, 8, 1))
    eventos = _listar(client, headers_autenticados, desde, hasta, tipo="vencimiento_documental")
    assert len(eventos) == 1
    assert eventos[0]["origen_tipo"] == "documento"
    assert eventos[0]["origen_id"] == creado.json()["id"]


def test_filtro_por_tipo_excluye_otros_tipos(client: TestClient, headers_autenticados: dict):
    client.post(
        "/api/v1/calendario/eventos",
        json={"tipo": "auditoria", "titulo": "Auditoría externa", "fecha": "2026-08-12T09:00:00Z"},
        headers=headers_autenticados,
    )
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-CAL9-3")
    client.post(
        "/api/v1/mantenimientos",
        json={"equipo_id": equipo_id, "tipo": "preventivo", "fecha_programada": "2026-08-13"},
        headers=headers_autenticados,
    )

    desde, hasta = _rango_mes(date(2026, 8, 1))
    solo_auditoria = _listar(client, headers_autenticados, desde, hasta, tipo="auditoria")
    assert len(solo_auditoria) == 1
    assert solo_auditoria[0]["tipo"] == "auditoria"


def test_listado_sin_filtro_mezcla_eventos_manuales_y_sintetizados(
    client: TestClient, headers_autenticados: dict
):
    """Regresión: la fecha de un evento manual viene de la base de datos con
    huso horario (TIMESTAMPTZ) mientras que la de un evento sintetizado se
    construye en memoria a partir de una `date` — si alguna queda "naive" y
    la otra "aware", ordenarlas juntas revienta con TypeError. Solo se
    reproduce mezclando ambos tipos en la MISMA llamada sin filtro de tipo."""
    client.post(
        "/api/v1/calendario/eventos",
        json={"tipo": "auditoria", "titulo": "Auditoría mixta", "fecha": "2026-08-12T09:00:00Z"},
        headers=headers_autenticados,
    )
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-CAL9-4")
    client.post(
        "/api/v1/mantenimientos",
        json={"equipo_id": equipo_id, "tipo": "preventivo", "fecha_programada": "2026-08-13"},
        headers=headers_autenticados,
    )

    desde, hasta = _rango_mes(date(2026, 8, 1))
    eventos = _listar(client, headers_autenticados, desde, hasta)
    tipos = {e["tipo"] for e in eventos}
    assert {"auditoria", "mantenimiento"} <= tipos
    fechas = [e["fecha"] for e in eventos]
    assert fechas == sorted(fechas)
