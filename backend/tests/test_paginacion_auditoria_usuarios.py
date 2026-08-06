"""Fase 2 / M3 (planificación 2026-08-04, docs/22) — paginación real en
`GET /api/v1/auditoria` y `GET /api/v1/usuarios`, que antes devolvían un
límite fijo sin página/offset real. Mismo patrón ya usado por Equipos
(`PaginaEquiposOut`), ver app/core/pagination.py para los límites
compartidos (tamaño por defecto 20, máximo 100)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.core.security import hash_password
from app.main import app
from app.modules.auth.infrastructure.models import Usuario

_TOTAL = 13
_TAMANO_PAGINA = 5  # 13 registros -> páginas de 5, 5 y 3 (primera/intermedia/última)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-pag-{sufijo}"
    laboratorio_id, admin_id, correo, password = crear_laboratorio_con_admin(
        "Lab Paginación", slug, f"admin-{sufijo}@pag.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {
        "laboratorio_id": laboratorio_id,
        "admin_id": admin_id,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _crear_equipo(client: TestClient, headers: dict, codigo: str) -> None:
    respuesta = client.post(
        "/api/v1/equipos", json={"codigo_interno": codigo, "nombre": "Equipo de paginación"}, headers=headers
    )
    assert respuesta.status_code == 201, respuesta.text


def _crear_usuarios_directos(db: Session, laboratorio_id: uuid.UUID, cantidad: int, prefijo: str) -> None:
    """Inserción directa (no vía API) — evita pagar el costo de bcrypt N
    veces solo para tener datos de prueba; el hash es el mismo para los N
    usuarios porque ninguno de estos tests inicia sesión con ellos."""
    set_tenant_context(db, laboratorio_id)
    hash_comun = hash_password("Cl4veSegura!2026")
    for i in range(cantidad):
        db.add(
            Usuario(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio_id,
                correo=f"{prefijo}-{i:03d}-{uuid.uuid4().hex[:6]}@pag.dev",
                password_hash=hash_comun,
                nombre_completo=f"{prefijo} {i:03d}",
                estado="activo",
                debe_cambiar_password=False,
            )
        )
    db.commit()


# ---- GET /api/v1/auditoria ---------------------------------------------------


def test_auditoria_primera_pagina(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    for i in range(_TOTAL):
        _crear_equipo(client, headers, f"EQ-PAG-{i:03d}")

    respuesta = client.get(
        "/api/v1/auditoria",
        params={"modulo": "equipos", "pagina": 1, "tamano_pagina": _TAMANO_PAGINA},
        headers=headers,
    )
    cuerpo = respuesta.json()
    assert respuesta.status_code == 200
    assert len(cuerpo["items"]) == _TAMANO_PAGINA
    assert cuerpo["total"] == _TOTAL
    assert cuerpo["pagina"] == 1
    assert cuerpo["tamano_pagina"] == _TAMANO_PAGINA


def test_auditoria_pagina_intermedia_y_ultima_sin_solapamiento(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    for i in range(_TOTAL):
        _crear_equipo(client, headers, f"EQ-PAG-{i:03d}")

    paginas = [
        client.get(
            "/api/v1/auditoria",
            params={"modulo": "equipos", "pagina": p, "tamano_pagina": _TAMANO_PAGINA},
            headers=headers,
        ).json()
        for p in (1, 2, 3)
    ]

    assert [len(p["items"]) for p in paginas] == [5, 5, 3]  # primera, intermedia, última

    ids_por_pagina = [{item["id"] for item in p["items"]} for p in paginas]
    # Ordenamiento estable: ninguna fila se repite ni se salta entre páginas.
    todos_los_ids = ids_por_pagina[0] | ids_por_pagina[1] | ids_por_pagina[2]
    assert len(todos_los_ids) == _TOTAL
    assert ids_por_pagina[0].isdisjoint(ids_por_pagina[1])
    assert ids_por_pagina[1].isdisjoint(ids_por_pagina[2])


def test_auditoria_pagina_fuera_de_rango_devuelve_vacio_sin_error(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    _crear_equipo(client, headers, "EQ-PAG-UNICO")

    respuesta = client.get(
        "/api/v1/auditoria",
        params={"modulo": "equipos", "pagina": 999, "tamano_pagina": _TAMANO_PAGINA},
        headers=headers,
    )
    cuerpo = respuesta.json()
    assert respuesta.status_code == 200
    assert cuerpo["items"] == []
    assert cuerpo["total"] == 1
    assert cuerpo["pagina"] == 999


def test_auditoria_tamano_pagina_maximo_permitido(client: TestClient, contexto: dict):
    respuesta = client.get(
        "/api/v1/auditoria", params={"tamano_pagina": 100}, headers=contexto["headers"]
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["tamano_pagina"] == 100


@pytest.mark.parametrize(
    ("parametro", "valor"), [("pagina", 0), ("tamano_pagina", 0), ("tamano_pagina", 101)]
)
def test_auditoria_rechaza_parametros_de_paginacion_invalidos(
    client: TestClient, contexto: dict, parametro: str, valor: int
):
    respuesta = client.get(
        "/api/v1/auditoria", params={parametro: valor}, headers=contexto["headers"]
    )
    assert respuesta.status_code == 422


# ---- GET /api/v1/usuarios ----------------------------------------------------


def test_usuarios_primera_pagina(client: TestClient, contexto: dict, db: Session):
    # -1 porque `crear_laboratorio_con_admin` ya crea al administrador.
    _crear_usuarios_directos(db, contexto["laboratorio_id"], _TOTAL - 1, "Usuario Pag")

    respuesta = client.get(
        "/api/v1/usuarios", params={"pagina": 1, "tamano_pagina": _TAMANO_PAGINA}, headers=contexto["headers"]
    )
    cuerpo = respuesta.json()
    assert respuesta.status_code == 200
    assert len(cuerpo["items"]) == _TAMANO_PAGINA
    assert cuerpo["total"] == _TOTAL
    assert cuerpo["pagina"] == 1
    assert cuerpo["tamano_pagina"] == _TAMANO_PAGINA


def test_usuarios_pagina_intermedia_y_ultima_sin_solapamiento(
    client: TestClient, contexto: dict, db: Session
):
    _crear_usuarios_directos(db, contexto["laboratorio_id"], _TOTAL - 1, "Usuario Pag")

    paginas = [
        client.get(
            "/api/v1/usuarios",
            params={"pagina": p, "tamano_pagina": _TAMANO_PAGINA},
            headers=contexto["headers"],
        ).json()
        for p in (1, 2, 3)
    ]

    assert [len(p["items"]) for p in paginas] == [5, 5, 3]

    ids_por_pagina = [{item["id"] for item in p["items"]} for p in paginas]
    todos_los_ids = ids_por_pagina[0] | ids_por_pagina[1] | ids_por_pagina[2]
    assert len(todos_los_ids) == _TOTAL
    assert ids_por_pagina[0].isdisjoint(ids_por_pagina[1])
    assert ids_por_pagina[1].isdisjoint(ids_por_pagina[2])


def test_usuarios_pagina_fuera_de_rango_devuelve_vacio_sin_error(
    client: TestClient, contexto: dict, db: Session
):
    respuesta = client.get(
        "/api/v1/usuarios",
        params={"pagina": 999, "tamano_pagina": _TAMANO_PAGINA},
        headers=contexto["headers"],
    )
    cuerpo = respuesta.json()
    assert respuesta.status_code == 200
    assert cuerpo["items"] == []
    assert cuerpo["total"] == 1  # solo el administrador del contexto
    assert cuerpo["pagina"] == 999


def test_usuarios_tamano_pagina_maximo_permitido(client: TestClient, contexto: dict):
    respuesta = client.get("/api/v1/usuarios", params={"tamano_pagina": 100}, headers=contexto["headers"])
    assert respuesta.status_code == 200
    assert respuesta.json()["tamano_pagina"] == 100


@pytest.mark.parametrize(
    ("parametro", "valor"), [("pagina", 0), ("tamano_pagina", 0), ("tamano_pagina", 101)]
)
def test_usuarios_rechaza_parametros_de_paginacion_invalidos(
    client: TestClient, contexto: dict, parametro: str, valor: int
):
    respuesta = client.get("/api/v1/usuarios", params={parametro: valor}, headers=contexto["headers"])
    assert respuesta.status_code == 422
