"""RNF-PERF-03 (docs/04-requerimientos-no-funcionales.md): "Las listas con
más de 50 elementos deben usar paginación o virtualización — nunca
renderizar el listado completo de una vez." Equipos y Auditoría ya lo
cumplían; `GET /mantenimientos` traía TODO el laboratorio sin límite alguno
(ni siquiera un `.limit()` en la consulta) — un laboratorio con más de unas
pocas decenas de mantenimientos registrados habría cargado la lista completa
en cada visita a la pantalla. Ver Sprint 27, docs/18-sprints.md."""

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
    slug = f"lab-mantpag27-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin(
        "Lab MantPag27", slug, f"admin-{sufijo}@mantpag27.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"headers": {"Authorization": f"Bearer {login.json()['access_token']}"}}


def _crear_equipo(client: TestClient, headers: dict) -> str:
    respuesta = client.post(
        "/api/v1/equipos", json={"codigo_interno": "EQ-MANTPAG", "nombre": "Autoclave"}, headers=headers
    )
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


def _crear_n_mantenimientos(client: TestClient, headers: dict, equipo_id: str, n: int) -> None:
    for _ in range(n):
        respuesta = client.post(
            "/api/v1/mantenimientos",
            json={"equipo_id": equipo_id, "tipo": "correctivo"},
            headers=headers,
        )
        assert respuesta.status_code == 201, respuesta.text


def test_listado_general_pagina_con_veinte_por_defecto(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])
    _crear_n_mantenimientos(client, contexto["headers"], equipo_id, 25)

    pagina_1 = client.get("/api/v1/mantenimientos", headers=contexto["headers"])
    assert pagina_1.status_code == 200
    cuerpo = pagina_1.json()
    assert cuerpo["total"] == 25
    assert cuerpo["tamano_pagina"] == 20
    assert cuerpo["pagina"] == 1
    assert len(cuerpo["items"]) == 20

    pagina_2 = client.get("/api/v1/mantenimientos", params={"pagina": 2}, headers=contexto["headers"])
    assert pagina_2.json()["total"] == 25
    assert len(pagina_2.json()["items"]) == 5

    # Sin solapamiento ni huecos entre páginas.
    ids_pagina_1 = {m["id"] for m in pagina_1.json()["items"]}
    ids_pagina_2 = {m["id"] for m in pagina_2.json()["items"]}
    assert ids_pagina_1.isdisjoint(ids_pagina_2)
    assert len(ids_pagina_1 | ids_pagina_2) == 25


def test_listado_por_equipo_no_trunca_el_historial_de_una_ficha(client: TestClient, contexto: dict):
    """Una ficha de equipo individual sigue pidiendo todo su historial en
    una sola página — el límite de 20 es solo para el listado general."""
    equipo_id = _crear_equipo(client, contexto["headers"])
    _crear_n_mantenimientos(client, contexto["headers"], equipo_id, 25)

    respuesta = client.get(
        "/api/v1/mantenimientos", params={"equipo_id": equipo_id}, headers=contexto["headers"]
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total"] == 25
    assert len(cuerpo["items"]) == 25


def test_dashboard_kpis_cuentan_todos_los_mantenimientos_no_solo_la_primera_pagina(
    client: TestClient, contexto: dict
):
    """Regresión: los KPIs del Dashboard y otros agregados internos deben
    usar el conteo real, no quedar limitados a una página de 20/200 (ver
    `listar_todos`, distinto de `listar`)."""
    equipo_id = _crear_equipo(client, contexto["headers"])
    _crear_n_mantenimientos(client, contexto["headers"], equipo_id, 25)

    kpis = client.get("/api/v1/dashboard/kpis", headers=contexto["headers"])
    assert kpis.status_code == 200
    assert kpis.json()["mantenimientos_correctivos_abiertos"] == 25
