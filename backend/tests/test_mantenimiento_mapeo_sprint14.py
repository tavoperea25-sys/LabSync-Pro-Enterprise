"""Pruebas de Sprint 14: mapeo configurable tipo de mantenimiento -> estado
operativo (RN-MANT-01, "configurable por tipo")."""

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
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-mant14-{sufijo}"
    laboratorio_id, admin_id, correo, password = crear_laboratorio_con_admin(
        "Lab Mant14", slug, f"admin-{sufijo}@mant14.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {
        "slug": slug,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _rol_id(client: TestClient, headers: dict, nombre: str) -> str:
    roles = client.get("/api/v1/roles", headers=headers).json()
    return next(r["id"] for r in roles if r["nombre"] == nombre)


def _crear_equipo(client: TestClient, headers: dict, codigo: str = "EQ-MANT14") -> str:
    respuesta = client.post(
        "/api/v1/equipos", json={"codigo_interno": codigo, "nombre": "Equipo Mant14"}, headers=headers
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _crear_mantenimiento(client: TestClient, headers: dict, equipo_id: str, tipo: str) -> dict:
    payload = {
        "equipo_id": equipo_id,
        "tipo": tipo,
        "fecha_programada": date.today().isoformat(),
        "tecnico_responsable_id": None,
        "descripcion": "prueba",
        "frecuencia_meses": None,
    }
    respuesta = client.post("/api/v1/mantenimientos", json=payload, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _estado_equipo(client: TestClient, headers: dict, equipo_id: str) -> str:
    return client.get(f"/api/v1/equipos/{equipo_id}", headers=headers).json()["estado_operativo"]


def test_sin_configuracion_usa_la_asignacion_por_defecto(client: TestClient, contexto: dict) -> None:
    headers = contexto["headers"]
    equipo_id = _crear_equipo(client, headers, "EQ-MANT14-DEFECTO")
    mant = _crear_mantenimiento(client, headers, equipo_id, "correctivo")

    client.post(f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers)
    assert _estado_equipo(client, headers, equipo_id) == "fuera_de_servicio"


def test_mapeo_configurado_sobrescribe_la_asignacion_por_defecto(client: TestClient, contexto: dict) -> None:
    headers = contexto["headers"]
    configurar = client.patch(
        "/api/v1/configuracion/mapeo-estados-mantenimiento",
        json={"mapeo_estados_mantenimiento": {"correctivo": "en_mantenimiento"}},
        headers=headers,
    )
    assert configurar.status_code == 200
    assert configurar.json()["mapeo_estados_mantenimiento"] == {"correctivo": "en_mantenimiento"}

    equipo_id = _crear_equipo(client, headers, "EQ-MANT14-OVERRIDE")
    mant = _crear_mantenimiento(client, headers, equipo_id, "correctivo")
    client.post(f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers)

    # Sin la configuración sería "fuera_de_servicio" (ver el test anterior)
    # — con el override, el mismo tipo "correctivo" ahora deja el equipo
    # "en_mantenimiento".
    assert _estado_equipo(client, headers, equipo_id) == "en_mantenimiento"


def test_mapeo_configurado_no_afecta_tipos_no_incluidos(client: TestClient, contexto: dict) -> None:
    """Un override parcial (solo 'correctivo') no debe tocar 'preventivo',
    que sigue cayendo al valor por defecto."""
    headers = contexto["headers"]
    client.patch(
        "/api/v1/configuracion/mapeo-estados-mantenimiento",
        json={"mapeo_estados_mantenimiento": {"correctivo": "en_mantenimiento"}},
        headers=headers,
    )

    equipo_id = _crear_equipo(client, headers, "EQ-MANT14-PREVENTIVO")
    mant = _crear_mantenimiento(client, headers, equipo_id, "preventivo")
    client.post(f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers)

    assert (
        _estado_equipo(client, headers, equipo_id) == "en_mantenimiento"
    )  # ya era el default para preventivo


def test_mapeo_tipo_desconocido_falla(client: TestClient, contexto: dict) -> None:
    respuesta = client.patch(
        "/api/v1/configuracion/mapeo-estados-mantenimiento",
        json={"mapeo_estados_mantenimiento": {"tipo_inventado": "fuera_de_servicio"}},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "mapeo_estados_mantenimiento_invalido"


def test_mapeo_estado_invalido_falla(client: TestClient, contexto: dict) -> None:
    respuesta = client.patch(
        "/api/v1/configuracion/mapeo-estados-mantenimiento",
        json={"mapeo_estados_mantenimiento": {"correctivo": "de_baja"}},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "mapeo_estados_mantenimiento_invalido"


def test_mapeo_null_restaura_el_defecto(client: TestClient, contexto: dict) -> None:
    headers = contexto["headers"]
    client.patch(
        "/api/v1/configuracion/mapeo-estados-mantenimiento",
        json={"mapeo_estados_mantenimiento": {"correctivo": "en_mantenimiento"}},
        headers=headers,
    )
    restaurado = client.patch(
        "/api/v1/configuracion/mapeo-estados-mantenimiento",
        json={"mapeo_estados_mantenimiento": None},
        headers=headers,
    )
    assert restaurado.status_code == 200
    assert restaurado.json()["mapeo_estados_mantenimiento"] is None

    equipo_id = _crear_equipo(client, headers, "EQ-MANT14-RESTAURADO")
    mant = _crear_mantenimiento(client, headers, equipo_id, "correctivo")
    client.post(f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers)
    assert _estado_equipo(client, headers, equipo_id) == "fuera_de_servicio"


def test_configurar_mapeo_requiere_permiso(client: TestClient, contexto: dict) -> None:
    headers = contexto["headers"]
    password_tecnico = "Cl4veSegura!2026"
    correo_tecnico = f"tec-mant14-{uuid.uuid4().hex[:8]}@mant14.dev"
    creado = client.post(
        "/api/v1/usuarios",
        json={
            "nombre_completo": "Técnico sin acceso",
            "correo": correo_tecnico,
            "password": password_tecnico,
            "rol_ids": [_rol_id(client, headers, "tecnico")],
        },
        headers=headers,
    )
    assert creado.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": contexto["slug"], "correo": correo_tecnico, "password": password_tecnico},
    )
    headers_tecnico = {"Authorization": f"Bearer {login.json()['access_token']}"}

    respuesta = client.patch(
        "/api/v1/configuracion/mapeo-estados-mantenimiento",
        json={"mapeo_estados_mantenimiento": {"correctivo": "en_mantenimiento"}},
        headers=headers_tecnico,
    )
    assert respuesta.status_code == 403
