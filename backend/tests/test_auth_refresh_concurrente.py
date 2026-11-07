"""Revisión de seguridad módulo Auth, hallazgo 1 — dos refresh concurrentes
con el mismo refresh token (misma cookie, distintas pestañas/dispositivos)
no deben disparar la detección de reuso ni revocar todas las sesiones del
usuario. Ver AuthService.refresh (ventana de gracia + SELECT ... FOR UPDATE)
y frontend/src/lib/httpClient.ts (single-flight, cubre el caso de una sola
pestaña — esta prueba cubre el caso que el single-flight no puede cubrir).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.database import set_tenant_context
from app.core.security import decodificar_refresh_token
from app.main import app
from app.modules.auth.application.auth_service import _hash_jti
from app.modules.auth.infrastructure.models import Sesion
from app.modules.auth.infrastructure.repositories import SesionRepositorySQLAlchemy


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_dos_refresh_concurrentes_con_mismo_token_no_revocan_todo(
    client: TestClient, crear_laboratorio_con_admin, db
):
    laboratorio_id, usuario_id, correo, password = crear_laboratorio_con_admin(
        "Lab Refresh Concurrente", "lab-refresh-concurrente", "user@lab-refresh-concurrente.dev"
    )

    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-refresh-concurrente", "correo": correo, "password": password},
    )
    assert login.status_code == 200
    cookie_refresh = client.cookies.get("refresh_token")
    assert cookie_refresh

    def _refrescar() -> int:
        # Cliente propio por hilo (no se comparte la instancia de
        # TestClient/httpx entre hilos) — cada uno lleva la MISMA cookie de
        # refresh capturada arriba, que es justo lo que se quiere probar:
        # dos pestañas/dispositivos presentando el mismo token a la vez.
        cliente_hilo = TestClient(app)
        cliente_hilo.cookies.set("refresh_token", cookie_refresh, path="/api/v1/auth")
        return cliente_hilo.post("/api/v1/auth/refresh").status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_a = executor.submit(_refrescar)
        futuro_b = executor.submit(_refrescar)
        status_a = futuro_a.result()
        status_b = futuro_b.result()

    # Antes de este fix, una de las dos (la que viera la sesión ya rotada
    # por la otra) recibía 401 "sesión comprometida".
    assert status_a == 200
    assert status_b == 200

    # Y la detección de reuso no debió haber revocado todas las sesiones
    # del usuario — al menos una sigue activa. `crear_laboratorio_con_admin`
    # ya hizo `db.commit()` internamente, lo que revierte el `SET LOCAL` de
    # `set_tenant_context` (ver app/core/database.py) — hay que volver a
    # fijarlo antes de consultar `db` directamente.
    set_tenant_context(db, laboratorio_id)
    sesiones_activas = SesionRepositorySQLAlchemy(db).listar_activas_de_usuario(usuario_id)
    assert len(sesiones_activas) >= 1


def test_reuso_repetido_dentro_de_la_ventana_no_debe_reiniciarla(
    client: TestClient, crear_laboratorio_con_admin, db
):
    """Regresión — `revocar_por_rotacion` pisaba `revocada_en` con `now()`
    en CADA reuso dentro de la ventana de gracia, no solo en la primera
    rotación. Eso reiniciaba la ventana con cada reuso: un atacante que
    reutilizara el refresh token robado cada menos de
    `refresh_ventana_gracia_segundos` nunca la veía expirar, así que la
    detección de robo nunca se activaba. El fix usa `COALESCE` para que
    `revocada_en` solo se fije la primera vez (ver
    SesionRepositorySQLAlchemy.revocar_por_rotacion). Controla el reloj
    retrocediendo `revocada_en` directamente en la BD en vez de usar
    `sleep`, para no depender de que pase tiempo real."""
    ventana = get_settings().refresh_ventana_gracia_segundos

    laboratorio_id, usuario_id, correo, password = crear_laboratorio_con_admin(
        "Lab Ventana Gracia", "lab-ventana-gracia", "user@lab-ventana-gracia.dev"
    )

    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-ventana-gracia", "correo": correo, "password": password},
    )
    assert login.status_code == 200
    token_a = client.cookies.get("refresh_token")
    assert token_a

    # `crear_laboratorio_con_admin` ya hizo `db.commit()` internamente, lo
    # que revierte el `SET LOCAL` de `set_tenant_context` — hay que volver a
    # fijarlo antes de cada uso directo de `db` (mismo patrón que el test de
    # arriba).
    set_tenant_context(db, laboratorio_id)
    hash_a = _hash_jti(decodificar_refresh_token(token_a)["jti"])
    sesion_a_id = SesionRepositorySQLAlchemy(db).buscar_por_hash(hash_a).id

    # Rotación normal del token A — queda revocado, con `revocada_en` fijado
    # a la hora real de ahora (T0).
    primer_refresh = client.post("/api/v1/auth/refresh")
    assert primer_refresh.status_code == 200

    # Se retrocede `revocada_en` a (ventana - 2s) en el pasado — simula que
    # la PRIMERA rotación "ocurrió" casi al borde de la ventana, sin tener
    # que esperar ese tiempo real.
    set_tenant_context(db, laboratorio_id)
    limite_dentro_de_ventana = datetime.now(UTC) - timedelta(seconds=ventana - 2)
    db.execute(
        update(Sesion).where(Sesion.id == sesion_a_id).values(revocada_en=limite_dentro_de_ventana)
    )
    db.commit()

    # `primer_refresh` ya actualizó la cookie del cliente a un token nuevo
    # (rotado) — se vuelve a fijar explícitamente a A, porque lo que se
    # quiere simular es un atacante reutilizando SIEMPRE el mismo token
    # robado, no siguiendo la rotación legítima.
    client.cookies.set("refresh_token", token_a, path="/api/v1/auth")

    # Reuso de A todavía dentro de la ventana (quedan ~2s) — debe tolerarse.
    set_tenant_context(db, laboratorio_id)
    reuso_dentro_de_ventana = client.post("/api/v1/auth/refresh")
    assert reuso_dentro_de_ventana.status_code == 200

    # Aserción clave del fix: `revocada_en` NO debe haberse movido. Con el
    # bug, `revocar_por_rotacion` la pisaba con `now()` en este mismo reuso,
    # reiniciando la ventana indefinidamente.
    set_tenant_context(db, laboratorio_id)
    revocada_en_tras_reuso = db.execute(
        select(Sesion.revocada_en).where(Sesion.id == sesion_a_id)
    ).scalar_one()
    assert abs((revocada_en_tras_reuso - limite_dentro_de_ventana).total_seconds()) < 1

    # Se retrocede más allá de la ventana, contada desde la PRIMERA rotación
    # — un reuso de A ya no debe tolerarse.
    set_tenant_context(db, laboratorio_id)
    mas_alla_de_la_ventana = datetime.now(UTC) - timedelta(seconds=ventana + 1)
    db.execute(
        update(Sesion).where(Sesion.id == sesion_a_id).values(revocada_en=mas_alla_de_la_ventana)
    )
    db.commit()

    # Igual que arriba — se reafirma A, no el token rotado por el reuso anterior.
    client.cookies.set("refresh_token", token_a, path="/api/v1/auth")

    set_tenant_context(db, laboratorio_id)
    reuso_fuera_de_ventana = client.post("/api/v1/auth/refresh")
    assert reuso_fuera_de_ventana.status_code == 401
    assert reuso_fuera_de_ventana.json()["error"]["codigo"] == "token_invalido"

    # Y la detección de robo sí debió revocar todas las sesiones del
    # usuario esta vez.
    set_tenant_context(db, laboratorio_id)
    sesiones_activas = SesionRepositorySQLAlchemy(db).listar_activas_de_usuario(usuario_id)
    assert len(sesiones_activas) == 0
