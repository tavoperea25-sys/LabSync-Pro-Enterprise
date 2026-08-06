"""Pruebas de Sprint 10: administración de usuarios y roles (RF-USR-01 a 07,
RN-USR-01/02/03)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-usr10-{sufijo}"
    laboratorio_id, admin_id, correo, password = crear_laboratorio_con_admin(
        "Lab Usr10", slug, f"admin-{sufijo}@usr10.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {
        "slug": slug,
        "laboratorio_id": laboratorio_id,
        "admin_id": admin_id,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _rol_id(client: TestClient, headers: dict, nombre: str) -> str:
    roles = client.get("/api/v1/roles", headers=headers).json()
    return next(r["id"] for r in roles if r["nombre"] == nombre)


def _crear_usuario(
    client: TestClient, headers: dict, rol_nombre: str = "tecnico", **overrides
) -> dict:
    payload = {
        "nombre_completo": "Usuario de prueba",
        "correo": f"user-{uuid.uuid4().hex[:8]}@usr10.dev",
        "password": "Cl4veSegura!2026",
        "rol_ids": [_rol_id(client, headers, rol_nombre)],
        **overrides,
    }
    respuesta = client.post("/api/v1/usuarios", json=payload, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# ---- CRUD (RF-USR-01) -------------------------------------------------------


def test_crear_usuario_fuerza_cambio_de_password_y_asigna_rol(client: TestClient, contexto: dict):
    usuario = _crear_usuario(client, contexto["headers"], rol_nombre="tecnico")
    assert usuario["debe_cambiar_password"] is True
    assert usuario["estado"] == "activo"
    assert usuario["roles"] == ["tecnico"]


def test_crear_usuario_con_correo_duplicado_falla(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    correo = f"dup-{uuid.uuid4().hex[:8]}@usr10.dev"
    _crear_usuario(client, headers, correo=correo)
    respuesta = client.post(
        "/api/v1/usuarios",
        json={
            "nombre_completo": "Otro",
            "correo": correo,
            "password": "Cl4veSegura!2026",
            "rol_ids": [_rol_id(client, headers, "tecnico")],
        },
        headers=headers,
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "correo_ya_registrado"


def test_crear_usuario_con_password_debil_falla(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    respuesta = client.post(
        "/api/v1/usuarios",
        json={
            "nombre_completo": "Password Débil",
            "correo": f"debil-{uuid.uuid4().hex[:8]}@usr10.dev",
            "password": "1234",
            "rol_ids": [_rol_id(client, headers, "tecnico")],
        },
        headers=headers,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "password_no_cumple_politica"


def test_crear_usuario_sin_roles_falla(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/usuarios",
        json={
            "nombre_completo": "Sin roles",
            "correo": f"sinrol-{uuid.uuid4().hex[:8]}@usr10.dev",
            "password": "Cl4veSegura!2026",
            "rol_ids": [],
        },
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422


def test_listar_y_actualizar_usuario(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    usuario = _crear_usuario(client, headers)

    listado = client.get("/api/v1/usuarios", headers=headers)
    assert any(u["id"] == usuario["id"] for u in listado.json()["items"])

    actualizado = client.patch(
        f"/api/v1/usuarios/{usuario['id']}", json={"nombre_completo": "Nombre actualizado"}, headers=headers
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["nombre_completo"] == "Nombre actualizado"


# ---- Roles (RF-USR-02) ------------------------------------------------------


def test_asignar_multiples_roles(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    usuario = _crear_usuario(client, headers, rol_nombre="tecnico")
    rol_ids = [_rol_id(client, headers, "tecnico"), _rol_id(client, headers, "metrologia")]

    respuesta = client.put(
        f"/api/v1/usuarios/{usuario['id']}/roles", json={"rol_ids": rol_ids}, headers=headers
    )
    assert respuesta.status_code == 200
    assert set(respuesta.json()["roles"]) == {"tecnico", "metrologia"}


# ---- RN-USR-02 — último Administrador --------------------------------------


def test_desactivar_al_unico_administrador_falla(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    respuesta = client.post(f"/api/v1/usuarios/{contexto['admin_id']}/desactivar", headers=headers)
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "ultimo_administrador"


def test_quitar_rol_administrador_al_unico_administrador_falla(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    rol_tecnico = _rol_id(client, headers, "tecnico")
    respuesta = client.put(
        f"/api/v1/usuarios/{contexto['admin_id']}/roles", json={"rol_ids": [rol_tecnico]}, headers=headers
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "ultimo_administrador"


def test_desactivar_segundo_administrador_es_permitido(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    segundo_admin = _crear_usuario(client, headers, rol_nombre="administrador")

    respuesta = client.post(f"/api/v1/usuarios/{segundo_admin['id']}/desactivar", headers=headers)
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "inactivo"


# ---- RN-USR-01 — desactivar revoca sesiones y bloquea login -----------------


def test_desactivar_usuario_le_impide_iniciar_sesion(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    correo = f"revocado-{uuid.uuid4().hex[:8]}@usr10.dev"
    password = "Cl4veSegura!2026"
    usuario = _crear_usuario(client, headers, correo=correo, password=password)

    client.post(f"/api/v1/usuarios/{usuario['id']}/desactivar", headers=headers)

    login_bloqueado = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": contexto["slug"], "correo": correo, "password": password},
    )
    assert login_bloqueado.status_code == 401


# ---- Sesiones activas (RF-USR-06) ------------------------------------------


def test_listar_y_cerrar_sesiones_activas(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    correo = f"sesion-{uuid.uuid4().hex[:8]}@usr10.dev"
    password = "Cl4veSegura!2026"
    usuario = _crear_usuario(client, headers, correo=correo, password=password)

    # Un segundo TestClient, con su propio cookie jar, para no mezclar la
    # sesión del admin con la del usuario recién creado.
    cliente_usuario = TestClient(app)
    login = cliente_usuario.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": contexto["slug"], "correo": correo, "password": password},
    )
    assert login.status_code == 200

    sesiones = client.get(f"/api/v1/usuarios/{usuario['id']}/sesiones", headers=headers)
    assert sesiones.status_code == 200
    assert len(sesiones.json()) == 1
    sesion_id = sesiones.json()[0]["id"]

    cierre = client.delete(f"/api/v1/usuarios/{usuario['id']}/sesiones/{sesion_id}", headers=headers)
    assert cierre.status_code == 204

    sesiones_tras_cierre = client.get(f"/api/v1/usuarios/{usuario['id']}/sesiones", headers=headers)
    assert sesiones_tras_cierre.json() == []


# ---- Autorización -----------------------------------------------------------


def test_tecnico_no_puede_administrar_usuarios(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    correo = f"tec-{uuid.uuid4().hex[:8]}@usr10.dev"
    password = "Cl4veSegura!2026"
    _crear_usuario(client, headers, correo=correo, password=password, rol_nombre="tecnico")

    login_tecnico = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": contexto["slug"], "correo": correo, "password": password},
    )
    headers_tecnico = {"Authorization": f"Bearer {login_tecnico.json()['access_token']}"}

    respuesta = client.get("/api/v1/usuarios", headers=headers_tecnico)
    assert respuesta.status_code == 403
