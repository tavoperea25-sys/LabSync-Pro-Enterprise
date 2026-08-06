"""RF-QR-03 (docs/03-requerimientos-funcionales.md), sección "Salidas":
"incidencia creada (visible luego en el módulo de Mantenimientos como
solicitud pendiente de triage)". El reporte de incidencia sin autenticación
existía desde el Sprint 4 (`test_qr_flow.py`), pero no existía NINGÚN
camino de lectura — `IncidenciaQrRepository` solo tenía `crear()` — así que
la incidencia quedaba escrita en la base de datos pero invisible para
siempre. Ver Sprint 23, docs/18-sprints.md."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _rol_id(client: TestClient, headers: dict, nombre: str) -> str:
    roles = client.get("/api/v1/roles", headers=headers).json()
    return next(r["id"] for r in roles if r["nombre"] == nombre)


@pytest.fixture
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-qr23-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab QR23", slug, f"admin-{sufijo}@qr23.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    equipo = client.post(
        "/api/v1/equipos", json={"codigo_interno": "EQ-QR23", "nombre": "Centrífuga"}, headers=headers
    ).json()
    token = client.get(f"/api/v1/equipos/{equipo['id']}/qr", headers=headers).json()["token"]

    return {"slug": slug, "headers": headers, "equipo": equipo, "token": token}


def _reportar(client: TestClient, token: str, descripcion: str = "El equipo hace ruido extraño.") -> str:
    respuesta = client.post(
        f"/api/v1/publico/qr/{token}/incidencias",
        json={"descripcion": descripcion, "contacto_nombre": "Juan Pérez"},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _crear_tecnico(client: TestClient, headers: dict, slug: str) -> dict:
    password_temporal = "Temp0ral!Segura"
    correo = f"tec-{uuid.uuid4().hex[:8]}@qr23.dev"
    creado = client.post(
        "/api/v1/usuarios",
        json={
            "nombre_completo": "Técnico QR23",
            "correo": correo,
            "password": password_temporal,
            "rol_ids": [_rol_id(client, headers, "tecnico")],
        },
        headers=headers,
    )
    assert creado.status_code == 201, creado.text

    # RF-USR-04: un usuario recién creado con contraseña temporal está
    # bloqueado hasta cambiarla — cambia la contraseña de una vez para que
    # las pruebas de este archivo puedan operar con normalidad.
    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": slug, "correo": correo, "password": password_temporal},
    )
    headers_temp = {"Authorization": f"Bearer {login.json()['access_token']}"}
    nueva_password = "NuevaClaveSegura!2026"
    cambio = client.post(
        "/api/v1/usuarios/me/cambiar-password",
        json={"password_actual": password_temporal, "password_nueva": nueva_password},
        headers=headers_temp,
    )
    assert cambio.status_code == 204, cambio.text

    login_final = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": slug, "correo": correo, "password": nueva_password},
    )
    assert login_final.status_code == 200
    return {"headers": {"Authorization": f"Bearer {login_final.json()['access_token']}"}}


def test_incidencia_reportada_aparece_en_listado_con_datos_del_equipo(client: TestClient, contexto: dict):
    _reportar(client, contexto["token"], "El equipo hace ruido extraño.")

    listado = client.get("/api/v1/qr/incidencias", headers=contexto["headers"])
    assert listado.status_code == 200
    cuerpo = listado.json()
    assert len(cuerpo) == 1
    incidencia = cuerpo[0]
    assert incidencia["descripcion"] == "El equipo hace ruido extraño."
    assert incidencia["estado"] == "pendiente"
    assert incidencia["equipo_codigo_interno"] == contexto["equipo"]["codigo_interno"]
    assert incidencia["equipo_nombre"] == contexto["equipo"]["nombre"]
    assert incidencia["contacto_nombre"] == "Juan Pérez"


def test_listado_vacio_sin_incidencias_reportadas(client: TestClient, contexto: dict):
    listado = client.get("/api/v1/qr/incidencias", headers=contexto["headers"])
    assert listado.status_code == 200
    assert listado.json() == []


def test_tecnico_puede_listar_y_hacer_triage(client: TestClient, contexto: dict):
    """El técnico es quien normalmente atiende el mantenimiento al que esta
    incidencia da lugar — mismo permiso (`mantenimientos.crear`/`equipos.leer`)
    que ya tiene para el resto del módulo."""
    incidencia_id = _reportar(client, contexto["token"])
    tecnico = _crear_tecnico(client, contexto["headers"], contexto["slug"])

    listado = client.get("/api/v1/qr/incidencias", headers=tecnico["headers"])
    assert listado.status_code == 200
    assert len(listado.json()) == 1

    actualizado = client.patch(
        f"/api/v1/qr/incidencias/{incidencia_id}/estado",
        json={"estado": "en_revision"},
        headers=tecnico["headers"],
    )
    assert actualizado.status_code == 200, actualizado.text
    assert actualizado.json()["estado"] == "en_revision"


def test_actualizar_estado_transiciona_de_pendiente_a_resuelta(client: TestClient, contexto: dict):
    incidencia_id = _reportar(client, contexto["token"])

    en_revision = client.patch(
        f"/api/v1/qr/incidencias/{incidencia_id}/estado",
        json={"estado": "en_revision"},
        headers=contexto["headers"],
    )
    assert en_revision.status_code == 200
    assert en_revision.json()["estado"] == "en_revision"

    resuelta = client.patch(
        f"/api/v1/qr/incidencias/{incidencia_id}/estado",
        json={"estado": "resuelta"},
        headers=contexto["headers"],
    )
    assert resuelta.status_code == 200
    assert resuelta.json()["estado"] == "resuelta"

    listado = client.get("/api/v1/qr/incidencias", headers=contexto["headers"])
    assert listado.json()[0]["estado"] == "resuelta"


def test_actualizar_estado_invalido_devuelve_422(client: TestClient, contexto: dict):
    incidencia_id = _reportar(client, contexto["token"])

    respuesta = client.patch(
        f"/api/v1/qr/incidencias/{incidencia_id}/estado",
        json={"estado": "archivada"},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422


def test_actualizar_estado_incidencia_inexistente_devuelve_404(client: TestClient, contexto: dict):
    respuesta = client.patch(
        f"/api/v1/qr/incidencias/{uuid.uuid4()}/estado",
        json={"estado": "en_revision"},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "incidencia_no_encontrada"


def test_actualizar_estado_genera_registro_de_auditoria(client: TestClient, contexto: dict):
    incidencia_id = _reportar(client, contexto["token"])
    client.patch(
        f"/api/v1/qr/incidencias/{incidencia_id}/estado",
        json={"estado": "en_revision"},
        headers=contexto["headers"],
    )

    auditoria = client.get(
        "/api/v1/auditoria", params={"modulo": "qr"}, headers=contexto["headers"]
    )
    assert auditoria.status_code == 200
    registros = auditoria.json()["items"]
    assert len(registros) == 1
    assert registros[0]["accion"] == "actualizar_estado_incidencia"
    assert registros[0]["entidad_tipo"] == "incidencia_qr"


def test_aislamiento_multi_tenant_de_incidencias(
    client: TestClient, contexto: dict, crear_laboratorio_con_admin
):
    """RN-TEN-01 — una incidencia reportada en un laboratorio nunca debe ser
    visible ni editable desde otro."""
    _reportar(client, contexto["token"], "Incidencia del laboratorio A.")

    sufijo = uuid.uuid4().hex[:8]
    slug_b = f"lab-qr23-b-{sufijo}"
    _, _, correo_b, password_b = crear_laboratorio_con_admin(
        "Lab QR23 B", slug_b, f"admin-{sufijo}@qr23b.dev"
    )
    login_b = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug_b, "correo": correo_b, "password": password_b}
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    listado_b = client.get("/api/v1/qr/incidencias", headers=headers_b)
    assert listado_b.status_code == 200
    assert listado_b.json() == []
