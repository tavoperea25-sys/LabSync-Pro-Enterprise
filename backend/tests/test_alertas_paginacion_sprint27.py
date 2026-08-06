"""RNF-PERF-03 — mismo hallazgo que en Mantenimientos (Sprint 27):
`GET /alertas` traía todo el laboratorio sin límite alguno, ni siquiera un
`.limit()` en la consulta. Es un problema real porque toda alerta generada a
lo largo de la vida de un laboratorio queda en la tabla (activa o resuelta,
RN-AUD-01-style — nada se purga); un laboratorio con suficiente historial
terminaría cargando cientos de filas en cada apertura del Centro de Alertas
o del panel de notificaciones del Navbar."""

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
    slug = f"lab-alertpag27-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin(
        "Lab AlertPag27", slug, f"admin-{sufijo}@alertpag27.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"headers": {"Authorization": f"Bearer {login.json()['access_token']}"}}


def _generar_n_alertas_criticas(client: TestClient, headers: dict, n: int) -> None:
    """Cada equipo con un correctivo recién iniciado genera exactamente una
    alerta crítica (`origen_tipo="equipo"`) — la forma más simple de generar
    N alertas reales sin depender de calibraciones/documentos vencidos."""
    for i in range(n):
        equipo = client.post(
            "/api/v1/equipos",
            json={"codigo_interno": f"EQ-ALERTPAG-{i}", "nombre": "Autoclave"},
            headers=headers,
        ).json()
        mant = client.post(
            "/api/v1/mantenimientos",
            json={"equipo_id": equipo["id"], "tipo": "correctivo"},
            headers=headers,
        ).json()
        client.post(f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers)


def test_listado_de_alertas_pagina_con_veinte_por_defecto(client: TestClient, contexto: dict):
    _generar_n_alertas_criticas(client, contexto["headers"], 25)

    pagina_1 = client.get("/api/v1/alertas", headers=contexto["headers"])
    assert pagina_1.status_code == 200
    cuerpo = pagina_1.json()
    assert cuerpo["total"] == 25
    assert cuerpo["tamano_pagina"] == 20
    assert len(cuerpo["items"]) == 20

    pagina_2 = client.get("/api/v1/alertas", params={"pagina": 2}, headers=contexto["headers"])
    assert pagina_2.json()["total"] == 25
    assert len(pagina_2.json()["items"]) == 5


def test_notificaciones_bell_puede_pedir_una_pagina_mas_chica(client: TestClient, contexto: dict):
    """`NotificacionesBell` pide un `tamano_pagina` reducido directamente al
    servidor en vez de traer todo y recortar del lado del cliente."""
    _generar_n_alertas_criticas(client, contexto["headers"], 25)

    respuesta = client.get(
        "/api/v1/alertas", params={"estado": "activa", "tamano_pagina": 8}, headers=contexto["headers"]
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 25
    assert len(cuerpo["items"]) == 8


def test_contar_activas_sigue_contando_el_total_real(client: TestClient, contexto: dict):
    """Regresión — `contar_activas` es un método separado, no debe verse
    afectado por el límite de página de `listar`."""
    _generar_n_alertas_criticas(client, contexto["headers"], 25)

    contador = client.get("/api/v1/alertas/contar-activas", headers=contexto["headers"])
    assert contador.json()["activas"] == 25
