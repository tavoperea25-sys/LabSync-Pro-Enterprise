"""Revisión de seguridad módulo Auth, hallazgo 1 — dos refresh concurrentes
con el mismo refresh token (misma cookie, distintas pestañas/dispositivos)
no deben disparar la detección de reuso ni revocar todas las sesiones del
usuario. Ver AuthService.refresh (ventana de gracia + SELECT ... FOR UPDATE)
y frontend/src/lib/httpClient.ts (single-flight, cubre el caso de una sola
pestaña — esta prueba cubre el caso que el single-flight no puede cubrir).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.core.database import set_tenant_context
from app.main import app
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
