"""Fase 2 / M1 (planificación 2026-08-04, docs/22) — un `IntegrityError` sin
capturar llegaba como 500 genérico. Ver el handler global registrado en
`app/core/errors.py::registrar_manejadores_de_error`.

Dos violaciones reales y deterministas contra Postgres:
- FOREIGN KEY: `EquipoService.crear`/`actualizar` nunca validan que
  `categoria_id`/`area_id` existan antes de guardar — alcanzable de punta a
  punta vía la API real, sin ningún truco.
- UNIQUE: a diferencia de la FK, todo constraint UNIQUE alcanzable desde la
  API (código interno, correo, nombre de categoría/área) YA tiene un chequeo
  explícito de aplicación antes del `INSERT` — el `IntegrityError` crudo solo
  puede ocurrir por una condición de carrera entre ese chequeo y el
  `INSERT` (dos peticiones concurrentes). Reproducirla de forma determinista
  requiere llamar al repositorio dos veces sin pasar por el chequeo del
  servicio (documentado en el propio test) — no es un mock de
  infraestructura, es Postgres real con una violación real."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.main import app
from app.modules.equipos.domain.entities import Equipo
from app.modules.equipos.infrastructure.repositories import EquipoRepositorySQLAlchemy


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def headers_autenticados(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-integridad-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin(
        "Lab Integridad", slug, f"admin-{sufijo}@lab-integridad.dev"
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": slug, "correo": correo, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_violacion_de_clave_foranea_devuelve_409_consistente(client: TestClient, headers_autenticados: dict):
    respuesta = client.post(
        "/api/v1/equipos",
        json={
            "codigo_interno": "EQ-FK-001",
            "nombre": "Equipo con categoría inexistente",
            "categoria_id": str(uuid.uuid4()),  # UUID válido, pero no existe en categorias_equipo
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 409
    cuerpo = respuesta.json()
    assert cuerpo["error"]["codigo"] == "referencia_invalida"
    assert "no existe" in cuerpo["error"]["mensaje"].lower()


def test_violacion_de_clave_foranea_no_deja_fila_parcial_ni_rompe_la_conexion(
    client: TestClient, headers_autenticados: dict
):
    """Verifica el rollback de dos formas a la vez: (1) el código interno
    del intento fallido queda libre — no quedó ninguna fila a medio guardar
    — y (2) la conexión que atendió la petición fallida sigue sirviendo
    normalmente la siguiente petición (si el rollback no ocurriera, la
    conexión del pool quedaría en estado `InFailedSqlTransaction` y la
    siguiente query sobre ella fallaría con un error no relacionado)."""
    fallido = client.post(
        "/api/v1/equipos",
        json={
            "codigo_interno": "EQ-FK-002",
            "nombre": "Equipo con área inexistente",
            "area_id": str(uuid.uuid4()),
        },
        headers=headers_autenticados,
    )
    assert fallido.status_code == 409

    reintento = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-FK-002", "nombre": "Mismo código, ahora sin área inválida"},
        headers=headers_autenticados,
    )
    assert reintento.status_code == 201
    assert reintento.json()["codigo_interno"] == "EQ-FK-002"


def test_violacion_de_unicidad_via_handler_devuelve_409_consistente(
    db: Session, crear_laboratorio_con_admin
):
    laboratorio_id, _, _, _ = crear_laboratorio_con_admin(
        "Lab Integridad Unique", "lab-integridad-unique", "admin@lab-integridad-unique.dev"
    )
    set_tenant_context(db, laboratorio_id)
    repositorio = EquipoRepositorySQLAlchemy(db)

    def _equipo(codigo: str) -> Equipo:
        ahora = datetime.utcnow()
        return Equipo(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            codigo_interno=codigo,
            nombre="Equipo de prueba",
            estado_operativo="operativo",
            categoria_id=None,
            area_id=None,
            responsable_id=None,
            marca=None,
            modelo=None,
            numero_serie=None,
            fabricante=None,
            proveedor=None,
            fecha_adquisicion=None,
            observaciones=None,
            foto_object_key=None,
            manual_object_key=None,
            proveedor_id=None,
            fabricante_id=None,
            capitulo=None,
            grupo=None,
            subgrupo=None,
            ubicacion=None,
            numero_inventario=None,
            condicion_fisica=None,
            clasificacion_riesgo=None,
            criticidad=None,
            forma_adquisicion=None,
            garantia=None,
            garantia_inicio=None,
            garantia_fin=None,
            eliminado_en=None,
            creado_en=ahora,
            actualizado_en=ahora,
        )

    repositorio.crear(_equipo("EQ-UQ-001"))
    db.commit()
    set_tenant_context(db, laboratorio_id)

    # Bypass deliberado de `EquipoService.existe_codigo` — es la única forma
    # determinista de reproducir la condición de carrera real (ver docstring
    # del módulo) sin depender de timing entre hilos.
    with pytest.raises(IntegrityError) as exc_info:
        repositorio.crear(_equipo("EQ-UQ-001"))

    manejador = app.exception_handlers[IntegrityError]
    respuesta = asyncio.run(manejador(None, exc_info.value))  # type: ignore[arg-type]

    assert respuesta.status_code == 409
    cuerpo = json.loads(bytes(respuesta.body))
    assert cuerpo["error"]["codigo"] == "registro_duplicado"


def test_violacion_de_check_constraint_devuelve_409_generico_no_clasificado(
    db: Session, crear_laboratorio_con_admin
):
    """Rama de respaldo del handler: una violación de integridad que no es
    ni UNIQUE ni FOREIGN KEY (aquí, el CHECK de `equipos.estado_operativo`
    añadido en la migración 0016 — ver test_check_constraints_estados.py
    para la prueba equivalente a nivel de base de datos) sigue recibiendo
    una respuesta 409 consistente en vez de un 500, aunque el handler no
    tenga un mensaje específico para ese caso."""
    laboratorio_id, _, _, _ = crear_laboratorio_con_admin(
        "Lab Integridad Check", "lab-integridad-check", "admin@lab-integridad-check.dev"
    )
    set_tenant_context(db, laboratorio_id)
    repositorio = EquipoRepositorySQLAlchemy(db)
    ahora = datetime.utcnow()

    with pytest.raises(IntegrityError) as exc_info:
        repositorio.crear(
            Equipo(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio_id,
                codigo_interno="EQ-CK-001",
                nombre="Equipo con estado inválido",
                estado_operativo="invalido",  # fuera del CHECK de la migración 0016
                categoria_id=None,
                area_id=None,
                responsable_id=None,
                marca=None,
                modelo=None,
                numero_serie=None,
                fabricante=None,
                proveedor=None,
                fecha_adquisicion=None,
                observaciones=None,
                foto_object_key=None,
                manual_object_key=None,
                proveedor_id=None,
                fabricante_id=None,
                capitulo=None,
                grupo=None,
                subgrupo=None,
                ubicacion=None,
                numero_inventario=None,
                condicion_fisica=None,
                clasificacion_riesgo=None,
                criticidad=None,
                forma_adquisicion=None,
                garantia=None,
                garantia_inicio=None,
                garantia_fin=None,
                eliminado_en=None,
                creado_en=ahora,
                actualizado_en=ahora,
            )
        )

    manejador = app.exception_handlers[IntegrityError]
    respuesta = asyncio.run(manejador(None, exc_info.value))  # type: ignore[arg-type]

    assert respuesta.status_code == 409
    cuerpo = json.loads(bytes(respuesta.body))
    assert cuerpo["error"]["codigo"] == "violacion_de_integridad_de_datos"


def test_otros_errores_de_dominio_siguen_propagandose_sin_cambios(
    client: TestClient, headers_autenticados: dict
):
    """El nuevo handler de `IntegrityError` no debe interferir con el
    despacho de errores de dominio ya existentes — un 404 por recurso
    inexistente debe seguir siendo exactamente ese 404, no un 409 genérico
    de integridad ni un 500."""
    respuesta = client.get(f"/api/v1/equipos/{uuid.uuid4()}", headers=headers_autenticados)
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "equipo_no_encontrado"
