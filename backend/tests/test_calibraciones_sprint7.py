"""Pruebas de Sprint 7: cálculo de próxima fecha y semáforo (RN-CAL-01/03),
corrección sin eliminar (RN-CAL-02), certificado adjunto (RF-CAL-06) y
listado de críticos (RF-CAL-05)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.calibraciones.domain.entities import calcular_proxima_fecha, semaforo


def test_calcular_proxima_fecha_suma_meses_simple():
    assert calcular_proxima_fecha(date(2026, 1, 15), 12) == date(2027, 1, 15)


def test_calcular_proxima_fecha_ajusta_fin_de_mes():
    # 31 de enero + 1 mes no puede ser "3 de marzo" por desborde silencioso.
    assert calcular_proxima_fecha(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_calcular_proxima_fecha_cruza_anio():
    assert calcular_proxima_fecha(date(2026, 11, 1), 3) == date(2027, 2, 1)


def test_semaforo_verde_amarillo_rojo_gris():
    hoy = date(2026, 6, 1)
    assert semaforo(date(2026, 12, 1), hoy) == "verde"
    assert semaforo(date(2026, 6, 20), hoy) == "amarillo"  # 19 días, dentro del umbral de 30
    assert semaforo(date(2026, 5, 1), hoy) == "rojo"
    assert semaforo(None, hoy) == "gris"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def headers_autenticados(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-cal7-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab Cal7", slug, f"admin-{sufijo}@cal7.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _crear_equipo(client: TestClient, headers: dict, codigo: str = "EQ-CAL1") -> str:
    respuesta = client.post(
        "/api/v1/equipos", json={"codigo_interno": codigo, "nombre": "Balanza analítica"}, headers=headers
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _subir_certificado(client: TestClient, headers: dict) -> dict:
    contenido = b"%PDF-1.4 certificado de prueba"
    solicitud = client.post(
        "/api/v1/calibraciones/upload-url",
        json={"nombre_archivo": "cert.pdf", "tipo_mime": "application/pdf", "tamano_bytes": len(contenido)},
        headers=headers,
    )
    assert solicitud.status_code == 200, solicitud.text
    datos = solicitud.json()
    respuesta_put = httpx.put(
        datos["url_subida"], content=contenido, headers={"Content-Type": "application/pdf"}
    )
    assert respuesta_put.status_code in (200, 204)
    return {
        "object_key": datos["object_key"],
        "nombre_archivo": "cert.pdf",
        "tamano_bytes": len(contenido),
        "tipo_mime": "application/pdf",
    }


def test_crear_calibracion_calcula_proxima_fecha_y_semaforo(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados)
    respuesta = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": "2026-01-01",
            "frecuencia_meses": 12,
            "resultado": "conforme",
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["proxima_fecha"] == "2027-01-01"
    assert cuerpo["semaforo"] == "verde"
    assert cuerpo["tiene_certificado"] is False


def test_crear_calibracion_con_fecha_futura_falla(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados)
    manana = (date.today() + timedelta(days=1)).isoformat()
    respuesta = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": manana,
            "frecuencia_meses": 12,
            "resultado": "conforme",
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "fecha_calibracion_futura"


def test_crear_calibracion_para_equipo_inexistente_falla(client: TestClient, headers_autenticados: dict):
    respuesta = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": str(uuid.uuid4()),
            "fecha_calibracion": "2026-01-01",
            "frecuencia_meses": 12,
            "resultado": "conforme",
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "equipo_no_encontrado"


def test_crear_calibracion_con_certificado_y_descargarlo(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados)
    certificado = _subir_certificado(client, headers_autenticados)
    creada = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": "2026-01-01",
            "frecuencia_meses": 12,
            "resultado": "conforme",
            "certificado": certificado,
        },
        headers=headers_autenticados,
    )
    assert creada.status_code == 201
    assert creada.json()["tiene_certificado"] is True

    descarga = client.get(
        f"/api/v1/calibraciones/{creada.json()['id']}/certificado-url", headers=headers_autenticados
    )
    assert descarga.status_code == 200
    assert descarga.json()["url"].startswith("http")


def test_descargar_certificado_sin_adjunto_falla(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados)
    creada = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": "2026-01-01",
            "frecuencia_meses": 12,
            "resultado": "conforme",
        },
        headers=headers_autenticados,
    ).json()
    respuesta = client.get(
        f"/api/v1/calibraciones/{creada['id']}/certificado-url", headers=headers_autenticados
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "certificado_no_disponible"


def test_corregir_preserva_la_original_y_referencia_el_motivo(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados)
    original = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": "2026-01-01",
            "frecuencia_meses": 12,
            "resultado": "conforme",
            "numero_certificado": "CERT-001",
        },
        headers=headers_autenticados,
    ).json()

    correccion = client.post(
        f"/api/v1/calibraciones/{original['id']}/corregir",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": "2026-01-01",
            "frecuencia_meses": 12,
            "resultado": "conforme",
            "numero_certificado": "CERT-001-B",
            "motivo": "Número de certificado transcrito incorrectamente.",
        },
        headers=headers_autenticados,
    )
    assert correccion.status_code == 201
    cuerpo = correccion.json()
    assert cuerpo["corrige_a_id"] == original["id"]
    assert cuerpo["motivo_correccion"] == "Número de certificado transcrito incorrectamente."
    assert cuerpo["id"] != original["id"]

    # La original sigue intacta — RN-CAL-02, nunca se sobrescribe.
    original_tras_correccion = client.get(
        f"/api/v1/calibraciones/{original['id']}", headers=headers_autenticados
    )
    assert original_tras_correccion.json()["numero_certificado"] == "CERT-001"

    historial = client.get(f"/api/v1/calibraciones?equipo_id={equipo_id}", headers=headers_autenticados)
    assert len(historial.json()) == 2


def test_corregir_sin_motivo_falla_validacion(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados)
    original = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": "2026-01-01",
            "frecuencia_meses": 12,
            "resultado": "conforme",
        },
        headers=headers_autenticados,
    ).json()
    respuesta = client.post(
        f"/api/v1/calibraciones/{original['id']}/corregir",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": "2026-01-01",
            "frecuencia_meses": 12,
            "resultado": "conforme",
            "motivo": "",
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 422


def test_listar_criticos_ordena_por_urgencia_y_excluye_verdes(client: TestClient, headers_autenticados: dict):
    hoy = date.today()

    equipo_vencido = _crear_equipo(client, headers_autenticados, "EQ-ROJO")
    client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_vencido,
            "fecha_calibracion": (hoy - timedelta(days=400)).isoformat(),
            "frecuencia_meses": 1,
            "resultado": "conforme",
        },
        headers=headers_autenticados,
    )

    equipo_proximo = _crear_equipo(client, headers_autenticados, "EQ-AMARILLO")
    client.post(
        "/api/v1/calibraciones",
        json={
            # fecha_calibracion + 1 mes cae entre 28 y 31 días de hoy según
            # el mes; restar 20 días de margen garantiza aterrizar dentro
            # del umbral de 30 (8-11 días) sin depender de qué mes sea hoy.
            "equipo_id": equipo_proximo,
            "fecha_calibracion": (hoy - timedelta(days=20)).isoformat(),
            "frecuencia_meses": 1,
            "resultado": "conforme",
        },
        headers=headers_autenticados,
    )

    equipo_vigente = _crear_equipo(client, headers_autenticados, "EQ-VERDE")
    client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_vigente,
            "fecha_calibracion": hoy.isoformat(),
            "frecuencia_meses": 24,
            "resultado": "conforme",
        },
        headers=headers_autenticados,
    )

    equipo_sin_calibrar = _crear_equipo(client, headers_autenticados, "EQ-GRIS")

    criticos = client.get("/api/v1/calibraciones/criticas", headers=headers_autenticados)
    assert criticos.status_code == 200
    cuerpo = criticos.json()

    ids_criticos = [c["equipo_id"] for c in cuerpo]
    assert equipo_vigente not in ids_criticos  # verde excluido
    assert ids_criticos.index(equipo_vencido) < ids_criticos.index(equipo_proximo)
    assert ids_criticos.index(equipo_proximo) < ids_criticos.index(equipo_sin_calibrar)

    semaforos = {c["equipo_id"]: c["semaforo"] for c in cuerpo}
    assert semaforos[equipo_vencido] == "rojo"
    assert semaforos[equipo_proximo] == "amarillo"
    assert semaforos[equipo_sin_calibrar] == "gris"
