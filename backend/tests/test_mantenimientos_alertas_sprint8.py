"""Pruebas de Sprint 8: máquina de estados de Mantenimientos (RN-MANT-01/02),
recurrencia (RF-MANT-02), y el módulo Alertas (RF-ALT-01/02, RN-ALT-01/02)."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def headers_autenticados(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-mant8-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab Mant8", slug, f"admin-{sufijo}@mant8.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _crear_equipo(client: TestClient, headers: dict, codigo: str = "EQ-MANT1") -> str:
    respuesta = client.post(
        "/api/v1/equipos", json={"codigo_interno": codigo, "nombre": "Autoclave"}, headers=headers
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _estado_equipo(client: TestClient, headers: dict, equipo_id: str) -> str:
    respuesta = client.get(f"/api/v1/equipos/{equipo_id}", headers=headers)
    assert respuesta.status_code == 200
    return respuesta.json()["estado_operativo"]


def _crear_mantenimiento(
    client: TestClient, headers: dict, equipo_id: str, tipo: str = "correctivo", **overrides
) -> dict:
    payload = {
        "equipo_id": equipo_id,
        "tipo": tipo,
        "fecha_programada": date.today().isoformat(),
        "tecnico_responsable_id": None,
        "descripcion": "prueba",
        "frecuencia_meses": None,
        **overrides,
    }
    respuesta = client.post("/api/v1/mantenimientos", json=payload, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# ---- RN-MANT-01 ------------------------------------------------------------


def test_iniciar_correctivo_pone_equipo_fuera_de_servicio_y_cerrar_lo_revierte(
    client: TestClient, headers_autenticados: dict
):
    equipo_id = _crear_equipo(client, headers_autenticados)
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id, tipo="correctivo")

    iniciado = client.post(f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers_autenticados)
    assert iniciado.status_code == 200
    assert iniciado.json()["estado"] == "en_ejecucion"
    assert _estado_equipo(client, headers_autenticados, equipo_id) == "fuera_de_servicio"

    cerrado = client.post(
        f"/api/v1/mantenimientos/{mant['id']}/cerrar",
        json={"fecha_ejecutada": date.today().isoformat()},
        headers=headers_autenticados,
    )
    assert cerrado.status_code == 200
    assert cerrado.json()["estado"] == "completado"
    assert _estado_equipo(client, headers_autenticados, equipo_id) == "operativo"


def test_preventivo_pone_equipo_en_mantenimiento_no_fuera_de_servicio(
    client: TestClient, headers_autenticados: dict
):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT-PREV")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id, tipo="preventivo")
    client.post(f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers_autenticados)
    assert _estado_equipo(client, headers_autenticados, equipo_id) == "en_mantenimiento"


def test_no_revierte_a_operativo_si_quedan_otros_mantenimientos_abiertos(
    client: TestClient, headers_autenticados: dict
):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT-CONCURR")
    mant1 = _crear_mantenimiento(client, headers_autenticados, equipo_id, tipo="correctivo")
    mant2 = _crear_mantenimiento(client, headers_autenticados, equipo_id, tipo="correctivo")

    client.post(f"/api/v1/mantenimientos/{mant1['id']}/iniciar", headers=headers_autenticados)
    client.post(f"/api/v1/mantenimientos/{mant2['id']}/iniciar", headers=headers_autenticados)

    cerrado1 = client.post(
        f"/api/v1/mantenimientos/{mant1['id']}/cerrar",
        json={"fecha_ejecutada": date.today().isoformat()},
        headers=headers_autenticados,
    )
    assert cerrado1.status_code == 200
    # mant2 sigue en_ejecucion — el equipo NO debe volver a operativo todavía.
    assert _estado_equipo(client, headers_autenticados, equipo_id) == "fuera_de_servicio"

    client.post(
        f"/api/v1/mantenimientos/{mant2['id']}/cerrar",
        json={"fecha_ejecutada": date.today().isoformat()},
        headers=headers_autenticados,
    )
    assert _estado_equipo(client, headers_autenticados, equipo_id) == "operativo"


# ---- RN-MANT-02 / RF-MANT-02 ------------------------------------------------


def test_cerrar_sin_fecha_ejecutada_falla_validacion(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT-FECHA")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id)
    respuesta = client.post(
        f"/api/v1/mantenimientos/{mant['id']}/cerrar", json={}, headers=headers_autenticados
    )
    assert respuesta.status_code == 422


def test_cerrar_preventivo_con_frecuencia_genera_el_siguiente(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT-RECUR")
    mant = _crear_mantenimiento(
        client, headers_autenticados, equipo_id, tipo="preventivo", frecuencia_meses=6
    )
    fecha_cierre = date.today()
    cerrado = client.post(
        f"/api/v1/mantenimientos/{mant['id']}/cerrar",
        json={"fecha_ejecutada": fecha_cierre.isoformat()},
        headers=headers_autenticados,
    )
    assert cerrado.status_code == 200

    listado = client.get(f"/api/v1/mantenimientos?equipo_id={equipo_id}", headers=headers_autenticados)
    items = listado.json()["items"]
    assert len(items) == 2
    siguiente = next(m for m in items if m["id"] != mant["id"])
    assert siguiente["estado"] == "programado"
    assert siguiente["generado_de_id"] == mant["id"]
    # La fecha exacta depende de `calcular_proxima_fecha`, ya probado en
    # Sprint 7 — aquí solo importa que quedó DESPUÉS del cierre.
    assert date.fromisoformat(siguiente["fecha_programada"]) > fecha_cierre


def test_cancelar_mantenimiento_programado_no_toca_el_equipo(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT-CANCEL")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id)
    cancelado = client.post(
        f"/api/v1/mantenimientos/{mant['id']}/cancelar",
        json={"motivo": "Ya no aplica"},
        headers=headers_autenticados,
    )
    assert cancelado.status_code == 200
    assert cancelado.json()["estado"] == "cancelado"
    assert _estado_equipo(client, headers_autenticados, equipo_id) == "operativo"


# ---- RF-ALT-01 / RN-ALT-02 (equipo fuera de servicio) -----------------------


def test_iniciar_correctivo_genera_alerta_critica_y_cerrar_la_resuelve(
    client: TestClient, headers_autenticados: dict
):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT-ALERTA")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id, tipo="correctivo")

    client.post(f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers_autenticados)

    activas = client.get("/api/v1/alertas?estado=activa", headers=headers_autenticados).json()["items"]
    alertas_equipo = [a for a in activas if a["origen_tipo"] == "equipo" and a["origen_id"] == equipo_id]
    assert len(alertas_equipo) == 1
    assert alertas_equipo[0]["tipo"] == "critica"

    client.post(
        f"/api/v1/mantenimientos/{mant['id']}/cerrar",
        json={"fecha_ejecutada": date.today().isoformat()},
        headers=headers_autenticados,
    )

    activas_tras_cerrar = client.get(
        "/api/v1/alertas?estado=activa", headers=headers_autenticados
    ).json()["items"]
    alertas_equipo_tras_cerrar = [
        a for a in activas_tras_cerrar if a["origen_tipo"] == "equipo" and a["origen_id"] == equipo_id
    ]
    assert alertas_equipo_tras_cerrar == []


# ---- RN-ALT-01 (deduplicación) ----------------------------------------------


def test_evaluar_no_duplica_alertas_activas_para_el_mismo_origen(
    client: TestClient, headers_autenticados: dict
):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT-DEDUP")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id, tipo="correctivo")
    client.post(f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers_autenticados)

    primero = client.get("/api/v1/alertas/contar-activas", headers=headers_autenticados)
    assert primero.json()["activas"] == 1

    evaluar = client.post("/api/v1/alertas/evaluar", headers=headers_autenticados)
    assert evaluar.status_code == 200
    # El barrido no debe crear una segunda alerta "critica"/"equipo" mientras
    # la primera siga activa (índice único parcial + chequeo de aplicación).
    segundo = client.get("/api/v1/alertas/contar-activas", headers=headers_autenticados)
    assert segundo.json()["activas"] == 1


def test_marcar_leida_y_resolver_manual(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT-RESOLVER")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id, tipo="correctivo")
    client.post(f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers_autenticados)

    alerta = client.get("/api/v1/alertas?estado=activa", headers=headers_autenticados).json()["items"][0]

    leida = client.post(f"/api/v1/alertas/{alerta['id']}/leer", headers=headers_autenticados)
    assert leida.status_code == 200
    assert leida.json()["leida_en"] is not None

    resuelta = client.post(f"/api/v1/alertas/{alerta['id']}/resolver", headers=headers_autenticados)
    assert resuelta.status_code == 200
    assert resuelta.json()["estado"] == "resuelta"

    assert client.get("/api/v1/alertas/contar-activas", headers=headers_autenticados).json()["activas"] == 0


def test_resolver_alerta_ya_resuelta_falla(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT-RERESOLVER")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id, tipo="correctivo")
    client.post(f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers_autenticados)
    alerta_id = client.get(
        "/api/v1/alertas?estado=activa", headers=headers_autenticados
    ).json()["items"][0]["id"]

    client.post(f"/api/v1/alertas/{alerta_id}/resolver", headers=headers_autenticados)
    segunda_vez = client.post(f"/api/v1/alertas/{alerta_id}/resolver", headers=headers_autenticados)
    assert segunda_vez.status_code == 409
    assert segunda_vez.json()["error"]["codigo"] == "alerta_ya_resuelta"
