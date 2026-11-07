"""Pruebas end-to-end del módulo Auth vía API real (docs/09-user-flows.md Flow 1)."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import set_tenant_context
from app.main import app
from app.modules.auth.infrastructure.models import Usuario as UsuarioModel


def _max_age_de_cookie_refresh(respuesta) -> int:
    set_cookie = respuesta.headers.get("set-cookie", "")
    coincidencia = re.search(r"Max-Age=(\d+)", set_cookie, re.IGNORECASE)
    assert coincidencia, f"No se encontró Max-Age en el Set-Cookie: {set_cookie!r}"
    return int(coincidencia.group(1))


@pytest.fixture
def client() -> TestClient:
    # Un cliente nuevo por prueba: evita que las cookies de sesión de una
    # prueba se filtren a otra (TestClient conserva su cookie jar mientras
    # viva la instancia).
    return TestClient(app)


def test_login_exitoso_emite_access_token_y_cookie(client: TestClient, crear_laboratorio_con_admin):
    _, _, correo, password = crear_laboratorio_con_admin("Lab Login", "lab-login", "user@lab-login.dev")

    respuesta = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-login", "correo": correo, "password": password},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["usuario"]["correo"] == correo
    assert "administrador" in cuerpo["usuario"]["roles"]
    assert cuerpo["access_token"]
    assert "refresh_token" in respuesta.cookies


def test_login_password_incorrecto_no_revela_informacion(client: TestClient, crear_laboratorio_con_admin):
    _, _, correo, _ = crear_laboratorio_con_admin("Lab Fail", "lab-fail", "user@lab-fail.dev")

    respuesta = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-fail", "correo": correo, "password": "password-incorrecta"},
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["codigo"] == "credenciales_invalidas"


def test_login_con_slug_de_otro_tenant_falla(client: TestClient, crear_laboratorio_con_admin):
    """El usuario existe, pero no en el laboratorio indicado — RN-TEN-01."""
    crear_laboratorio_con_admin("Lab X", "lab-x", "user@lab-x.dev", "Passw0rd!Segura")
    crear_laboratorio_con_admin("Lab Y", "lab-y", "otro@lab-y.dev", "Passw0rd!Segura")

    respuesta = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-y", "correo": "user@lab-x.dev", "password": "Passw0rd!Segura"},
    )

    assert respuesta.status_code == 401


def test_me_sin_token_devuelve_401(client: TestClient):
    respuesta = client.get("/api/v1/auth/me")
    assert respuesta.status_code == 401


def test_flujo_completo_login_me_refresh_logout(client: TestClient, crear_laboratorio_con_admin, monkeypatch):
    # Revisión de seguridad módulo Auth, hallazgo 1 — AuthService.refresh
    # ahora tolera el reuso de un refresh token ya rotado dentro de una
    # ventana de gracia corta (carrera benigna de refresh concurrente, no
    # robo). Esta prueba simula un reuso genuino (sin ninguna concurrencia
    # real de por medio) para confirmar que la detección de robo sigue
    # funcionando — se fija la ventana a 0 para aislar justamente ese caso
    # del de la ventana de gracia, que tiene su propia prueba dedicada en
    # test_auth_refresh_concurrente.py.
    monkeypatch.setattr(get_settings(), "refresh_ventana_gracia_segundos", 0)
    _, _, correo, password = crear_laboratorio_con_admin("Lab Flow", "lab-flow", "user@lab-flow.dev")

    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-flow", "correo": correo, "password": password},
    )
    access_token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json()["correo"] == correo

    refresh_token_original = client.cookies.get("refresh_token")

    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200

    nuevo_access_token = refresh.json()["access_token"]
    me_tras_refresh = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {nuevo_access_token}"})
    assert me_tras_refresh.status_code == 200

    # Detección de reuso (docs/16-seguridad.md): el refresh token original
    # ya fue rotado — volver a presentarlo debe fallar, no solo por estar
    # "viejo" sino porque su reuso es indicio de robo.
    client.cookies.jar.clear()
    client.cookies.set("refresh_token", refresh_token_original, path="/api/v1/auth")
    reuso = client.post("/api/v1/auth/refresh")
    assert reuso.status_code == 401

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    refresh_tras_logout = client.post("/api/v1/auth/refresh")
    assert refresh_tras_logout.status_code == 401


def test_bloqueo_progresivo_tras_intentos_fallidos(client: TestClient, crear_laboratorio_con_admin):
    _, _, correo, _ = crear_laboratorio_con_admin("Lab Bloqueo", "lab-bloqueo", "user@lab-bloqueo.dev")

    for _ in range(5):
        client.post(
            "/api/v1/auth/login",
            json={"laboratorio_slug": "lab-bloqueo", "correo": correo, "password": "incorrecta"},
        )

    respuesta = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-bloqueo", "correo": correo, "password": "incorrecta"},
    )

    assert respuesta.status_code == 429
    assert respuesta.json()["error"]["codigo"] == "cuenta_bloqueada"


def test_recordarme_propaga_duracion_a_sesion_y_sobrevive_refresh(
    client: TestClient, crear_laboratorio_con_admin
):
    """Hallazgo 2 — antes, "Recordarme" solo cambiaba la cookie del login
    (30 días) pero la sesión en base de datos quedaba fija en 7 días, y el
    primer refresh volvía a fijar la cookie en 7 días sin importar la
    preferencia original."""
    _, _, correo, password = crear_laboratorio_con_admin(
        "Lab Recordarme", "lab-recordarme", "user@lab-recordarme.dev"
    )
    dias_recordarme = get_settings().refresh_recordarme_dias

    login = client.post(
        "/api/v1/auth/login",
        json={
            "laboratorio_slug": "lab-recordarme",
            "correo": correo,
            "password": password,
            "recordarme": True,
        },
    )
    assert login.status_code == 200
    assert _max_age_de_cookie_refresh(login) == dias_recordarme * 24 * 60 * 60

    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200
    assert _max_age_de_cookie_refresh(refresh) == dias_recordarme * 24 * 60 * 60


def test_login_correo_inexistente_ejecuta_verificacion_ficticia(
    client: TestClient, crear_laboratorio_con_admin, monkeypatch
):
    """Hallazgo 4 — antes, con un correo inexistente, `login` retornaba sin
    llamar nunca a `verificar_password` (Argon2id), a diferencia de la rama
    de contraseña incorrecta (correo sí existe) que sí lo hacía — una
    asimetría de tiempo de respuesta que permite enumerar correos."""
    crear_laboratorio_con_admin("Lab Enum", "lab-enum", "existe@lab-enum.dev")

    from app.modules.auth.application import auth_service as auth_service_module

    llamadas = []
    original = auth_service_module.verificar_password

    def _espia(password_plano, password_hash):
        llamadas.append(password_hash)
        return original(password_plano, password_hash)

    monkeypatch.setattr(auth_service_module, "verificar_password", _espia)

    respuesta = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-enum", "correo": "no-existe@lab-enum.dev", "password": "cualquiera"},
    )

    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["codigo"] == "credenciales_invalidas"
    # Se verificó contra el hash ficticio precalculado, no se omitió la
    # verificación — mismo costo de Argon2id que la rama de contraseña
    # incorrecta.
    assert llamadas == [auth_service_module._HASH_FICTICIO]


def test_bloqueo_progresivo_respeta_el_techo_configurado(
    client: TestClient, crear_laboratorio_con_admin, db, monkeypatch
):
    """Hallazgo 5 — sin techo, el bloqueo duplica sin límite en cada
    intento fallido adicional (a los 20 intentos supera las 500 horas).
    Simula un usuario que ya acumuló 8 intentos fallidos previos (sin
    bloqueo activo) para que el próximo (9º, ciclos_de_bloqueo=5) caiga en
    60*2^4=960s sin techo — muy por encima del límite fijado abajo. No se
    puede llegar a este estado disparando 9 logins fallidos seguidos: tras
    el 5º el login ya responde 429 sin volver a registrar el intento."""
    monkeypatch.setattr(get_settings(), "bloqueo_maximo_segundos", 90)
    laboratorio_id, usuario_id, correo, _ = crear_laboratorio_con_admin(
        "Lab Techo", "lab-techo", "user@lab-techo.dev"
    )
    # `crear_laboratorio_con_admin` ya hizo `db.commit()` internamente, lo
    # que revierte el `SET LOCAL` de `set_tenant_context` (ver
    # app/core/database.py) — hay que volver a fijarlo antes de tocar `db`
    # directamente, mismo patrón que el resto de la suite (p. ej.
    # test_alertas_isolation.py).
    set_tenant_context(db, laboratorio_id)
    db.query(UsuarioModel).filter_by(id=usuario_id).update(
        {"intentos_fallidos": 8, "bloqueado_hasta": None}
    )
    db.commit()

    # Este 9º intento fallido es el que calcula y persiste el nuevo
    # `bloqueado_hasta` (capado) — la respuesta a ESTE intento sigue siendo
    # `credenciales_invalidas` (401), el bloqueo recién se aplica al
    # siguiente intento.
    noveno_intento = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-techo", "correo": correo, "password": "incorrecta"},
    )
    assert noveno_intento.status_code == 401

    respuesta = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-techo", "correo": correo, "password": "incorrecta"},
    )

    assert respuesta.status_code == 429
    segundos_restantes = respuesta.json()["error"]["detalles"]["segundos_restantes"]
    assert segundos_restantes <= 90
