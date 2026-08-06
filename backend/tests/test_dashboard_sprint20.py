"""Pruebas del rediseño del Dashboard (Sprint 20, docs/18-sprints.md):
`DashboardService` agrega Equipos, Calibraciones, Documentos, Mantenimientos
y Auditoría en un único resumen operativo."""

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
    slug = f"lab-dash20-{sufijo}"
    laboratorio_id, _, correo, password = crear_laboratorio_con_admin(
        "Lab Dash20", slug, f"admin-{sufijo}@dash20.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {
        "slug": slug,
        "laboratorio_id": laboratorio_id,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _rol_id(client: TestClient, headers: dict, nombre: str) -> str:
    roles = client.get("/api/v1/roles", headers=headers).json()
    return next(r["id"] for r in roles if r["nombre"] == nombre)


def _crear_tecnico(client: TestClient, headers: dict) -> dict:
    password = "Cl4veSegura!2026"
    correo = f"tec-{uuid.uuid4().hex[:8]}@dash20.dev"
    creado = client.post(
        "/api/v1/usuarios",
        json={
            "nombre_completo": "Técnico Dash20",
            "correo": correo,
            "password": password,
            "rol_ids": [_rol_id(client, headers, "tecnico")],
        },
        headers=headers,
    )
    assert creado.status_code == 201, creado.text
    return {"correo": correo, "password": password}


def _crear_equipo(client: TestClient, headers: dict, codigo: str = "EQ-DASH20", **overrides) -> dict:
    payload = {"codigo_interno": codigo, "nombre": "Equipo Dashboard", **overrides}
    respuesta = client.post("/api/v1/equipos", json=payload, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_kpis_en_laboratorio_vacio_no_falla_y_no_inventa_cumplimiento(
    client: TestClient, contexto: dict
):
    respuesta = client.get("/api/v1/dashboard/kpis", headers=contexto["headers"])
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["equipos_total"] == 0
    assert cuerpo["calibraciones_semaforo"] == "normal"
    assert cuerpo["documentos_vencidos"] == 0
    # Sin documentos todavía: un % de cumplimiento sobre cero sería ruido,
    # no información — debe ser None, no 0 ni 100.
    assert cuerpo["cumplimiento_documental_pct"] is None


def test_kpis_reflejan_calibracion_vencida_como_semaforo_critico(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    equipo = _crear_equipo(client, headers)
    vencida = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo["id"],
            "fecha_calibracion": "2020-01-01",
            "frecuencia_meses": 1,
            "resultado": "conforme",
        },
        headers=headers,
    )
    assert vencida.status_code == 201, vencida.text

    respuesta = client.get("/api/v1/dashboard/kpis", headers=headers)
    cuerpo = respuesta.json()
    assert cuerpo["calibraciones_semaforo"] == "critico"


def test_kpis_calculan_cumplimiento_documental_sobre_documentos_activos(
    client: TestClient, contexto: dict
):
    headers = contexto["headers"]
    # Un documento vigente (sin vencimiento) y uno vencido -> 50% de cumplimiento.
    for nombre, fecha_vencimiento in (("Vigente", None), ("Vencido", "2020-01-01")):
        solicitud = client.post(
            "/api/v1/documentos/upload-url",
            json={"nombre_archivo": f"{nombre}.pdf", "tipo_mime": "application/pdf", "tamano_bytes": 10},
            headers=headers,
        )
        assert solicitud.status_code == 200
        datos = solicitud.json()
        httpx.put(datos["url_subida"], content=b"x", headers={"Content-Type": "application/pdf"})
        payload = {
            "nombre": nombre,
            "archivo": {
                "object_key": datos["object_key"],
                "nombre_archivo": f"{nombre}.pdf",
                "tamano_bytes": 1,
                "tipo_mime": "application/pdf",
            },
        }
        if fecha_vencimiento:
            payload["fecha_vencimiento"] = fecha_vencimiento
            payload["fecha_emision"] = "2019-01-01"
        creado = client.post("/api/v1/documentos", json=payload, headers=headers)
        assert creado.status_code == 201, creado.text
        # `crear_documento` deja el documento en "en_revision" (RF-DOC-12) —
        # sin aprobar, ninguno de los dos contaría como "vigente" y el
        # cumplimiento sería 0% para ambos casos, no la comparación que
        # esta prueba busca verificar.
        aprobado = client.post(f"/api/v1/documentos/{creado.json()['id']}/aprobar", headers=headers)
        assert aprobado.status_code == 200, aprobado.text

    respuesta = client.get("/api/v1/dashboard/kpis", headers=headers)
    cuerpo = respuesta.json()
    assert cuerpo["documentos_vencidos"] == 1
    assert cuerpo["cumplimiento_documental_pct"] == 50.0


def test_equipos_criticos_incluye_fuera_de_servicio_y_calibracion_vencida(
    client: TestClient, contexto: dict
):
    headers = contexto["headers"]
    operativo = _crear_equipo(client, headers, "EQ-DASH20-A")
    fuera_servicio = _crear_equipo(client, headers, "EQ-DASH20-B")
    client.patch(
        f"/api/v1/equipos/{fuera_servicio['id']}",
        json={
            "codigo_interno": "EQ-DASH20-B",
            "nombre": "Equipo Dashboard",
            "estado_operativo": "fuera_de_servicio",
        },
        headers=headers,
    )
    vencido = _crear_equipo(client, headers, "EQ-DASH20-C")
    client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": vencido["id"],
            "fecha_calibracion": "2020-01-01",
            "frecuencia_meses": 1,
            "resultado": "conforme",
        },
        headers=headers,
    )

    respuesta = client.get("/api/v1/dashboard/equipos-criticos", headers=headers)
    assert respuesta.status_code == 200, respuesta.text
    ids = {f["equipo_id"] for f in respuesta.json()}

    assert fuera_servicio["id"] in ids
    assert vencido["id"] in ids
    assert operativo["id"] not in ids  # operativo y sin calibración vencida: no requiere atención

    fila_vencido = next(f for f in respuesta.json() if f["equipo_id"] == vencido["id"])
    assert fila_vencido["semaforo_calibracion"] == "rojo"
    assert fila_vencido["ultima_calibracion_fecha"] == "2020-01-01"


def test_actividad_reciente_requiere_permiso_de_auditoria(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    tecnico = _crear_tecnico(client, headers)
    login_tecnico = client.post(
        "/api/v1/auth/login",
        json={
            "laboratorio_slug": contexto["slug"],
            "correo": tecnico["correo"],
            "password": tecnico["password"],
        },
    )
    assert login_tecnico.status_code == 200
    headers_tecnico = {"Authorization": f"Bearer {login_tecnico.json()['access_token']}"}

    denegado = client.get("/api/v1/dashboard/actividad-reciente", headers=headers_tecnico)
    assert denegado.status_code == 403

    _crear_equipo(client, headers)  # genera al menos un registro de auditoría
    permitido = client.get("/api/v1/dashboard/actividad-reciente", headers=headers)
    assert permitido.status_code == 200, permitido.text
    cuerpo = permitido.json()
    assert len(cuerpo) >= 1
    assert cuerpo[0]["usuario_nombre"] is not None
    assert cuerpo[0]["modulo"] == "equipos"
