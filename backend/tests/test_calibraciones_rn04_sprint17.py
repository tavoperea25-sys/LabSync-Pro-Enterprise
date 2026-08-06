"""RN-CAL-04 (docs/07-reglas-de-negocio.md): un resultado de calibración
'no_conforme' debe generar automáticamente una alerta crítica. La regla
estaba documentada desde el Sprint 7 pero nunca se conectó en el código —
`RESULTADOS_CALIBRACION` incluía "no_conforme" como valor válido, pero
`CalibracionService._crear_fila` no generaba ninguna alerta al recibirlo
(ver Sprint 17, docs/18-sprints.md)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def headers_autenticados(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-rn04-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab RN04", slug, f"admin-{sufijo}@rn04.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _crear_equipo(client: TestClient, headers: dict, codigo: str = "EQ-RN04") -> str:
    respuesta = client.post(
        "/api/v1/equipos", json={"codigo_interno": codigo, "nombre": "Balanza analítica"}, headers=headers
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _crear_calibracion(client: TestClient, headers: dict, equipo_id: str, resultado: str) -> dict:
    respuesta = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": "2026-01-01",
            "frecuencia_meses": 12,
            "resultado": resultado,
        },
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_calibracion_no_conforme_genera_alerta_critica(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados)
    _crear_calibracion(client, headers_autenticados, equipo_id, "no_conforme")

    alertas = client.get("/api/v1/alertas", headers=headers_autenticados)
    assert alertas.status_code == 200
    criticas = [
        a for a in alertas.json()["items"] if a["tipo"] == "critica" and a["origen_tipo"] == "calibracion"
    ]
    assert len(criticas) == 1
    assert "no superó su calibración" in criticas[0]["mensaje"]
    assert criticas[0]["estado"] == "activa"


def test_calibracion_conforme_no_genera_alerta(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados)
    _crear_calibracion(client, headers_autenticados, equipo_id, "conforme")

    alertas = client.get("/api/v1/alertas", headers=headers_autenticados)
    assert alertas.status_code == 200
    assert [a for a in alertas.json()["items"] if a["origen_tipo"] == "calibracion"] == []


def test_alerta_de_no_conforme_no_colisiona_con_alerta_de_vencimiento(
    client: TestClient, headers_autenticados: dict
):
    """Ambas usan `origen_tipo="calibracion"`, pero con `origen_id` distinto
    (la de vencimiento usa `equipo_id`; la de RN-CAL-04 usa el id de la
    calibración puntual) — deben coexistir como dos alertas independientes,
    no colapsar en una sola por deduplicación (RN-ALT-01) ni resolverse
    entre sí por accidente."""
    equipo_id = _crear_equipo(client, headers_autenticados)
    # Calibración ya vencida (frecuencia de 1 mes desde una fecha lejana en
    # el pasado) para que el barrido manual encuentre una condición crítica.
    respuesta = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": "2020-01-01",
            "frecuencia_meses": 1,
            "resultado": "no_conforme",
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 201, respuesta.text

    evaluacion = client.post("/api/v1/alertas/evaluar", headers=headers_autenticados)
    assert evaluacion.status_code == 200

    alertas = client.get("/api/v1/alertas", headers=headers_autenticados).json()["items"]
    criticas_calibracion = [
        a for a in alertas if a["tipo"] == "critica" and a["origen_tipo"] == "calibracion"
    ]
    # Una por RN-CAL-04 (resultado fallido) + una por el barrido de vencimiento.
    assert len(criticas_calibracion) == 2
    origenes = {a["origen_id"] for a in criticas_calibracion}
    assert len(origenes) == 2  # ids distintos: uno es el equipo, otro la calibración


def test_resolver_por_origen_de_equipo_no_resuelve_la_alerta_de_resultado_fallido(
    client: TestClient, headers_autenticados: dict
):
    """Registrar una nueva calibración resuelve la alerta de "vencimiento
    pendiente" (RN-ALT-02, keyed por equipo_id) pero NO debe resolver una
    alerta previa de resultado "no_conforme" (keyed por el id de esa
    calibración puntual) — un resultado fallido requiere revisión manual
    explícita, no se tapa solo porque llegó un registro nuevo."""
    equipo_id = _crear_equipo(client, headers_autenticados)
    _crear_calibracion(client, headers_autenticados, equipo_id, "no_conforme")

    # Una calibración posterior conforme no debe hacer desaparecer la alerta
    # de la anterior fallida.
    _crear_calibracion(client, headers_autenticados, equipo_id, "conforme")

    alertas = client.get("/api/v1/alertas", headers=headers_autenticados).json()["items"]
    activas_no_conforme = [
        a
        for a in alertas
        if a["tipo"] == "critica" and a["origen_tipo"] == "calibracion" and a["estado"] == "activa"
    ]
    assert len(activas_no_conforme) == 1
