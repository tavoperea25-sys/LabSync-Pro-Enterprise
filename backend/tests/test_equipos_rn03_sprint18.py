"""RN-EQ-03 (docs/07-reglas-de-negocio.md): un equipo no puede pasar a
estado "Operativo" si su categoría exige calibración vigente y la última
registrada está vencida. Documentada desde el Sprint 3 pero nunca conectada
en el código — `categorias_equipo` no tenía dónde guardar la configuración
"por categoría" que la regla exige (ver Sprint 17, docs/18-sprints.md)."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def headers_autenticados(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-eq03-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab EQ03", slug, f"admin-{sufijo}@eq03.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _crear_categoria(client: TestClient, headers: dict, bloquea: bool, nombre: str = "Balanzas") -> str:
    respuesta = client.post(
        "/api/v1/categorias-equipo",
        json={"nombre": nombre, "bloquea_activacion_si_calibracion_vencida": bloquea},
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _crear_equipo(
    client: TestClient, headers: dict, categoria_id: str | None, codigo: str = "EQ-RN03"
) -> str:
    respuesta = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": codigo, "nombre": "Balanza analítica", "categoria_id": categoria_id},
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _patch_estado(
    client: TestClient,
    headers: dict,
    equipo_id: str,
    codigo: str,
    categoria_id: str | None,
    estado_operativo: str,
    nombre: str = "Balanza analítica",
):
    # `PATCH /equipos/{id}` es reemplazo completo (como PUT), no un parche
    # parcial — omitir `categoria_id` la borraría silenciosamente, igual que
    # omitir cualquier otro campo. Se envía siempre, como haría un formulario
    # real que reenvía el estado completo del equipo.
    return client.patch(
        f"/api/v1/equipos/{equipo_id}",
        json={
            "codigo_interno": codigo,
            "nombre": nombre,
            "estado_operativo": estado_operativo,
            "categoria_id": categoria_id,
        },
        headers=headers,
    )


def _poner_fuera_de_servicio(
    client: TestClient, headers: dict, equipo_id: str, codigo: str, categoria_id: str | None
) -> None:
    respuesta = _patch_estado(client, headers, equipo_id, codigo, categoria_id, "fuera_de_servicio")
    assert respuesta.status_code == 200, respuesta.text


def _intentar_reactivar(
    client: TestClient, headers: dict, equipo_id: str, codigo: str, categoria_id: str | None
):
    return _patch_estado(client, headers, equipo_id, codigo, categoria_id, "operativo")


def _registrar_calibracion(
    client: TestClient,
    headers: dict,
    equipo_id: str,
    fecha: str,
    frecuencia_meses: int,
    resultado: str = "conforme",
) -> None:
    respuesta = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": fecha,
            "frecuencia_meses": frecuencia_meses,
            "resultado": resultado,
        },
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text


def test_no_puede_activarse_con_calibracion_vencida_si_la_categoria_bloquea(
    client: TestClient, headers_autenticados: dict
):
    categoria_id = _crear_categoria(client, headers_autenticados, bloquea=True)
    equipo_id = _crear_equipo(client, headers_autenticados, categoria_id, "EQ-RN03-A")
    # Vencida hace mucho: frecuencia de 1 mes desde 2020.
    _registrar_calibracion(client, headers_autenticados, equipo_id, "2020-01-01", 1)
    _poner_fuera_de_servicio(client, headers_autenticados, equipo_id, "EQ-RN03-A", categoria_id)

    respuesta = _intentar_reactivar(client, headers_autenticados, equipo_id, "EQ-RN03-A", categoria_id)

    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json()["error"]["codigo"] == "calibracion_vencida_bloquea_activacion"


def test_puede_activarse_si_la_categoria_no_tiene_el_bloqueo(client: TestClient, headers_autenticados: dict):
    categoria_id = _crear_categoria(client, headers_autenticados, bloquea=False, nombre="Termómetros")
    equipo_id = _crear_equipo(client, headers_autenticados, categoria_id, "EQ-RN03-B")
    _registrar_calibracion(client, headers_autenticados, equipo_id, "2020-01-01", 1)
    _poner_fuera_de_servicio(client, headers_autenticados, equipo_id, "EQ-RN03-B", categoria_id)

    respuesta = _intentar_reactivar(client, headers_autenticados, equipo_id, "EQ-RN03-B", categoria_id)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado_operativo"] == "operativo"


def test_puede_activarse_si_no_tiene_categoria(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, None, "EQ-RN03-C")
    _registrar_calibracion(client, headers_autenticados, equipo_id, "2020-01-01", 1)
    _poner_fuera_de_servicio(client, headers_autenticados, equipo_id, "EQ-RN03-C", None)

    respuesta = _intentar_reactivar(client, headers_autenticados, equipo_id, "EQ-RN03-C", None)

    assert respuesta.status_code == 200, respuesta.text


def test_puede_activarse_si_nunca_fue_calibrado(client: TestClient, headers_autenticados: dict):
    """"Vencido" (rojo) es distinto de "sin información" (gris) — RN-CAL-01.
    RN-EQ-03 solo bloquea por "Vencido", así que un equipo nunca calibrado
    no debe bloquearse por esta regla."""
    categoria_id = _crear_categoria(client, headers_autenticados, bloquea=True, nombre="Nunca calibrado")
    equipo_id = _crear_equipo(client, headers_autenticados, categoria_id, "EQ-RN03-D")
    _poner_fuera_de_servicio(client, headers_autenticados, equipo_id, "EQ-RN03-D", categoria_id)

    respuesta = _intentar_reactivar(client, headers_autenticados, equipo_id, "EQ-RN03-D", categoria_id)

    assert respuesta.status_code == 200, respuesta.text


def test_puede_activarse_si_la_ultima_calibracion_esta_vigente(
    client: TestClient, headers_autenticados: dict
):
    categoria_id = _crear_categoria(client, headers_autenticados, bloquea=True, nombre="Al día")
    equipo_id = _crear_equipo(client, headers_autenticados, categoria_id, "EQ-RN03-E")
    _registrar_calibracion(client, headers_autenticados, equipo_id, "2020-01-01", 1, resultado="conforme")
    # Una calibración posterior, vigente por 60 meses desde hoy, reemplaza
    # a la anterior vencida como "última" (orden por fecha_calibracion).
    _registrar_calibracion(client, headers_autenticados, equipo_id, date.today().isoformat(), 60)
    _poner_fuera_de_servicio(client, headers_autenticados, equipo_id, "EQ-RN03-E", categoria_id)

    respuesta = _intentar_reactivar(client, headers_autenticados, equipo_id, "EQ-RN03-E", categoria_id)

    assert respuesta.status_code == 200, respuesta.text


def test_no_bloquea_una_actualizacion_que_no_pasa_por_operativo(
    client: TestClient, headers_autenticados: dict
):
    """Editar otros campos de un equipo que sigue fuera de servicio (sin
    pedir pasar a "operativo") nunca debe dispararse esta regla."""
    categoria_id = _crear_categoria(client, headers_autenticados, bloquea=True, nombre="Sin cambio de estado")
    equipo_id = _crear_equipo(client, headers_autenticados, categoria_id, "EQ-RN03-F")
    _registrar_calibracion(client, headers_autenticados, equipo_id, "2020-01-01", 1)
    _poner_fuera_de_servicio(client, headers_autenticados, equipo_id, "EQ-RN03-F", categoria_id)

    respuesta = _patch_estado(
        client,
        headers_autenticados,
        equipo_id,
        "EQ-RN03-F",
        categoria_id,
        "fuera_de_servicio",
        nombre="Balanza analítica (renombrada)",
    )

    assert respuesta.status_code == 200, respuesta.text
