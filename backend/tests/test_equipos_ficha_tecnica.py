"""Ficha técnica extendida de equipos — Fase 2 de hojas de vida
(docs/25-diseno-tecnico-hojas-de-vida.md, migración 0019)."""

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
    slug = f"lab-ficha-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin(
        "Lab Ficha Técnica", slug, f"admin-{sufijo}@ficha.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"headers": {"Authorization": f"Bearer {login.json()['access_token']}"}}


def _crear_equipo(client: TestClient, headers: dict, codigo: str = "EQ-FICHA-1") -> str:
    creado = client.post(
        "/api/v1/equipos", json={"codigo_interno": codigo, "nombre": "Autoclave AC-204"}, headers=headers
    )
    assert creado.status_code == 201, creado.text
    return creado.json()["id"]


# ---- Campos nuevos de `equipos` (migración 0019) -------------------------------


def test_crear_equipo_sin_ningun_campo_tecnico_nuevo(client: TestClient, contexto: dict):
    """RF-EQ — "ningún campo técnico obligatorio: todos admiten vacío"
    (docs/24-...md sección 3.8)."""
    creado = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": "EQ-FICHA-VACIO", "nombre": "Equipo sin ficha"},
        headers=contexto["headers"],
    )
    assert creado.status_code == 201, creado.text
    cuerpo = creado.json()
    for campo in (
        "capitulo",
        "grupo",
        "subgrupo",
        "ubicacion",
        "numero_inventario",
        "condicion_fisica",
        "clasificacion_riesgo",
        "criticidad",
        "forma_adquisicion",
        "garantia",
        "garantia_inicio",
        "garantia_fin",
        "proveedor_id",
        "fabricante_id",
    ):
        assert cuerpo[campo] is None


def test_crear_equipo_con_campos_nuevos_completos(client: TestClient, contexto: dict):
    creado = client.post(
        "/api/v1/equipos",
        json={
            "codigo_interno": "EQ-FICHA-2",
            "nombre": "Autoclave",
            "capitulo": "Esterilización",
            "grupo": "Equipos de calor",
            "ubicacion": "Laboratorio Fisicoquímica - Mesón 3",
            "condicion_fisica": "bueno",
            "clasificacion_riesgo": "IIB",
            "criticidad": "alta",
            "forma_adquisicion": "compra",
            "garantia": True,
            "garantia_inicio": "2026-01-01",
            "garantia_fin": "2027-01-01",
        },
        headers=contexto["headers"],
    )
    assert creado.status_code == 201, creado.text
    cuerpo = creado.json()
    assert cuerpo["condicion_fisica"] == "bueno"
    assert cuerpo["clasificacion_riesgo"] == "IIB"
    assert cuerpo["criticidad"] == "alta"
    assert cuerpo["garantia"] is True


@pytest.mark.parametrize(
    "campo,valor,codigo_esperado",
    [
        ("condicion_fisica", "excelente", "condicion_fisica_invalido"),
        ("clasificacion_riesgo", "IV", "clasificacion_riesgo_invalido"),
        ("criticidad", "critica", "criticidad_invalido"),
        ("forma_adquisicion", "robo", "forma_adquisicion_invalido"),
    ],
)
def test_crear_equipo_con_valor_fuera_de_dominio_rechazado(
    client: TestClient, contexto: dict, campo: str, valor: str, codigo_esperado: str
):
    creado = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": f"EQ-DOM-{campo}", "nombre": "Equipo", campo: valor},
        headers=contexto["headers"],
    )
    assert creado.status_code == 422
    assert creado.json()["error"]["codigo"] == codigo_esperado


def test_crear_equipo_con_garantia_fin_antes_de_inicio_rechazado(client: TestClient, contexto: dict):
    creado = client.post(
        "/api/v1/equipos",
        json={
            "codigo_interno": "EQ-GARANTIA-1",
            "nombre": "Equipo",
            "garantia_inicio": "2026-06-01",
            "garantia_fin": "2026-01-01",
        },
        headers=contexto["headers"],
    )
    assert creado.status_code == 422
    assert creado.json()["error"]["codigo"] == "garantia_fechas_invalidas"


# ---- `equipo_ficha_tecnica` (1:1) -----------------------------------------------


def test_obtener_ficha_tecnica_de_equipo_sin_fila_devuelve_vacia(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])
    respuesta = client.get(f"/api/v1/equipos/{equipo_id}/ficha-tecnica", headers=contexto["headers"])
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["voltaje"] is None
    assert cuerpo["datos_adicionales"] == {}
    assert cuerpo["actualizado_en"] is None


def test_guardar_y_obtener_ficha_tecnica(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])

    guardado = client.put(
        f"/api/v1/equipos/{equipo_id}/ficha-tecnica",
        json={
            "voltaje": "120V",
            "corriente": "N/A",
            "rpm": "N/A",
            "dimensiones": "60x60x90 cm",
            "datos_adicionales": {"cfm": "350", "refrigerante": "R134a"},
        },
        headers=contexto["headers"],
    )
    assert guardado.status_code == 200, guardado.text
    assert guardado.json()["voltaje"] == "120V"
    assert guardado.json()["corriente"] == "N/A"
    assert guardado.json()["datos_adicionales"] == {"cfm": "350", "refrigerante": "R134a"}
    assert guardado.json()["actualizado_en"] is not None

    obtenido = client.get(f"/api/v1/equipos/{equipo_id}/ficha-tecnica", headers=contexto["headers"])
    assert obtenido.json()["voltaje"] == "120V"


def test_guardar_ficha_tecnica_dos_veces_actualiza_no_duplica(client: TestClient, contexto: dict):
    equipo_id = _crear_equipo(client, contexto["headers"])

    client.put(
        f"/api/v1/equipos/{equipo_id}/ficha-tecnica", json={"voltaje": "120V"}, headers=contexto["headers"]
    )
    segunda = client.put(
        f"/api/v1/equipos/{equipo_id}/ficha-tecnica", json={"voltaje": "220V"}, headers=contexto["headers"]
    )
    assert segunda.status_code == 200
    assert segunda.json()["voltaje"] == "220V"

    obtenido = client.get(f"/api/v1/equipos/{equipo_id}/ficha-tecnica", headers=contexto["headers"])
    assert obtenido.json()["voltaje"] == "220V"


def test_ficha_tecnica_de_equipo_inexistente_404(client: TestClient, contexto: dict):
    respuesta = client.get(f"/api/v1/equipos/{uuid.uuid4()}/ficha-tecnica", headers=contexto["headers"])
    assert respuesta.status_code == 404


def test_duplicar_equipo_copia_la_ficha_tecnica(client: TestClient, contexto: dict):
    """RN-EQ-04 extendida (Fase 2) — la ficha técnica describe el MODELO,
    no la unidad física, y se copia junto con marca/fabricante."""
    equipo_id = _crear_equipo(client, contexto["headers"], "EQ-FICHA-DUP")
    client.put(
        f"/api/v1/equipos/{equipo_id}/ficha-tecnica", json={"voltaje": "120V"}, headers=contexto["headers"]
    )

    copia = client.post(f"/api/v1/equipos/{equipo_id}/duplicar", headers=contexto["headers"])
    assert copia.status_code == 201, copia.text

    ficha_copia = client.get(
        f"/api/v1/equipos/{copia.json()['id']}/ficha-tecnica", headers=contexto["headers"]
    )
    assert ficha_copia.json()["voltaje"] == "120V"
