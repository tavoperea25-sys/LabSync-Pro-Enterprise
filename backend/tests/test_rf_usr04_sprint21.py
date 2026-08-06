"""RF-USR-04 (docs/03-requerimientos-funcionales.md): "Forzar cambio de
contraseña en el primer inicio de sesión." La bandera `debe_cambiar_password`
existía desde el Sprint 10 (se fija en `crear()`, se limpia en
`cambiar_password_propio()`, viaja en las respuestas de login/refresh/me) pero
nada la hacía cumplir — un usuario podía ignorarla indefinidamente y seguir
usando la contraseña temporal. Ver Sprint 21, docs/18-sprints.md."""

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
    slug = f"lab-usr04-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab USR04", slug, f"admin-{sufijo}@usr04.dev")
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


def _crear_tecnico_con_password_temporal(client: TestClient, headers: dict, slug: str) -> dict:
    password_temporal = "Temp0ral!Segura"
    correo = f"tec-{uuid.uuid4().hex[:8]}@usr04.dev"
    creado = client.post(
        "/api/v1/usuarios",
        json={
            "nombre_completo": "Técnico Temporal",
            "correo": correo,
            "password": password_temporal,
            "rol_ids": [_rol_id(client, headers, "tecnico")],
        },
        headers=headers,
    )
    assert creado.status_code == 201, creado.text
    assert creado.json()["debe_cambiar_password"] is True

    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": slug, "correo": correo, "password": password_temporal},
    )
    assert login.status_code == 200
    assert login.json()["usuario"]["debe_cambiar_password"] is True
    return {
        "correo": correo,
        "password_temporal": password_temporal,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def test_admin_recien_creado_no_puede_usar_endpoints_protegidos(client: TestClient, contexto: dict):
    tecnico = _crear_tecnico_con_password_temporal(client, contexto["headers"], contexto["slug"])

    bloqueado = client.get("/api/v1/equipos", headers=tecnico["headers"])

    assert bloqueado.status_code == 403, bloqueado.text
    assert bloqueado.json()["error"]["codigo"] == "debe_cambiar_password_pendiente"


def test_usuario_pendiente_puede_consultar_auth_me(client: TestClient, contexto: dict):
    tecnico = _crear_tecnico_con_password_temporal(client, contexto["headers"], contexto["slug"])

    respuesta = client.get("/api/v1/auth/me", headers=tecnico["headers"])

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["debe_cambiar_password"] is True


def test_usuario_pendiente_puede_actualizar_su_perfil(client: TestClient, contexto: dict):
    """RF-USR-04 fuerza el cambio de CONTRASEÑA, no bloquea el resto de la
    cuenta — comportamiento ya cubierto por test_configuracion_sprint12.py,
    verificado aquí también para que este archivo documente la regla
    completa por sí solo."""
    tecnico = _crear_tecnico_con_password_temporal(client, contexto["headers"], contexto["slug"])

    respuesta = client.patch(
        "/api/v1/usuarios/me",
        json={"nombre_completo": "Nombre Actualizado", "correo": tecnico["correo"]},
        headers=tecnico["headers"],
    )

    assert respuesta.status_code == 200, respuesta.text


def test_ciclo_completo_cambiar_password_libera_el_bloqueo(client: TestClient, contexto: dict):
    tecnico = _crear_tecnico_con_password_temporal(client, contexto["headers"], contexto["slug"])
    password_nueva = "Nueva!Password2026"

    cambio = client.post(
        "/api/v1/usuarios/me/cambiar-password",
        json={"password_actual": tecnico["password_temporal"], "password_nueva": password_nueva},
        headers=tecnico["headers"],
    )
    assert cambio.status_code == 204, cambio.text

    # El access token viejo sigue llevando `debe_cambiar_password=True`
    # embebido (es un JWT sin estado) — sigue bloqueado hasta que expire,
    # nunca queda "abierto" por accidente tras el cambio.
    con_token_viejo = client.get("/api/v1/equipos", headers=tecnico["headers"])
    assert con_token_viejo.status_code == 403
    assert con_token_viejo.json()["error"]["codigo"] == "debe_cambiar_password_pendiente"

    # Cambiar la contraseña revoca todas las sesiones (RN-USR-01) — el
    # usuario necesita un login nuevo, que emite un token nuevo con la
    # bandera ya en False.
    nuevo_login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": contexto["slug"], "correo": tecnico["correo"], "password": password_nueva},
    )
    assert nuevo_login.status_code == 200
    assert nuevo_login.json()["usuario"]["debe_cambiar_password"] is False
    headers_nuevos = {"Authorization": f"Bearer {nuevo_login.json()['access_token']}"}

    permitido = client.get("/api/v1/equipos", headers=headers_nuevos)
    assert permitido.status_code == 200


def test_admin_sin_password_pendiente_no_se_ve_afectado(client: TestClient, contexto: dict):
    """Guarda de regresión: el usuario admin del contexto (creado con
    `crear_laboratorio_con_admin`, `debe_cambiar_password=False`) debe seguir
    operando con normalidad — RF-USR-04 no debe bloquear a nadie que ya
    cumplió con el cambio de contraseña."""
    respuesta = client.get("/api/v1/equipos", headers=contexto["headers"])
    assert respuesta.status_code == 200
