"""Fase 1 / I12 (auditoría 2026-07-31) — cobertura de casos de error,
condiciones límite y rutas de recuperación de Mantenimientos, el módulo con
menor cobertura del backend (76% en el service, 81% en el router) porque
solo estaba probado el camino feliz. Cada test aquí corresponde a una línea
concreta que `pytest --cov` reportaba como no ejecutada antes de este sprint
— ver `app/modules/mantenimientos/application/mantenimiento_service.py` y
`app/modules/mantenimientos/presentation/router.py`."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.database import set_tenant_context
from app.main import app
from app.modules.adjuntos.infrastructure.repositories import AdjuntoRepositorySQLAlchemy
from app.modules.alertas.application.alerta_service import AlertaService
from app.modules.alertas.infrastructure.repositories import (
    AlertaRepositorySQLAlchemy,
    NotificacionRepositorySQLAlchemy,
)
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.configuracion.infrastructure.repositories import ConfiguracionRepositorySQLAlchemy
from app.modules.equipos.infrastructure.repositories import EquipoRepositorySQLAlchemy
from app.modules.mantenimientos.application.mantenimiento_service import (
    ActorContexto,
    DatosCierre,
    FaltaFechaEjecutada,
    MantenimientoService,
)
from app.modules.mantenimientos.infrastructure.repositories import MantenimientoRepositorySQLAlchemy


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def headers_autenticados(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-mant29-{sufijo}"
    _, _, correo, password = crear_laboratorio_con_admin("Lab Mant29", slug, f"admin-{sufijo}@mant29.dev")
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _crear_equipo(client: TestClient, headers: dict, codigo: str = "EQ-MANT29") -> str:
    respuesta = client.post(
        "/api/v1/equipos", json={"codigo_interno": codigo, "nombre": "Balanza"}, headers=headers
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _crear_mantenimiento(
    client: TestClient, headers: dict, equipo_id: str, tipo: str = "correctivo", **overrides
) -> dict:
    payload = {
        "equipo_id": equipo_id,
        "tipo": tipo,
        "fecha_programada": date.today().isoformat(),
        "tecnico_responsable_id": None,
        "descripcion": "prueba",
        "frecuencia_meses": None,
        **overrides,
    }
    respuesta = client.post("/api/v1/mantenimientos", json=payload, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _cerrar(client: TestClient, headers: dict, mantenimiento_id: str) -> dict:
    respuesta = client.post(
        f"/api/v1/mantenimientos/{mantenimiento_id}/cerrar",
        json={"fecha_ejecutada": date.today().isoformat()},
        headers=headers,
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# ---- Recursos inexistentes (404) --------------------------------------------


def test_obtener_mantenimiento_inexistente_devuelve_404(client: TestClient, headers_autenticados: dict):
    respuesta = client.get(f"/api/v1/mantenimientos/{uuid.uuid4()}", headers=headers_autenticados)
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "mantenimiento_no_encontrado"


def test_crear_mantenimiento_con_equipo_inexistente_devuelve_404(
    client: TestClient, headers_autenticados: dict
):
    respuesta = client.post(
        "/api/v1/mantenimientos",
        json={
            "equipo_id": str(uuid.uuid4()),
            "tipo": "correctivo",
            "fecha_programada": None,
            "tecnico_responsable_id": None,
            "descripcion": None,
            "frecuencia_meses": None,
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "equipo_no_encontrado"


def test_url_evidencia_de_adjunto_inexistente_devuelve_404(client: TestClient, headers_autenticados: dict):
    respuesta = client.get(
        f"/api/v1/mantenimientos/evidencias/{uuid.uuid4()}/url", headers=headers_autenticados
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "evidencia_no_encontrada"


def test_informe_url_sin_informe_asignado_devuelve_404(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT29-SININF")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id)

    respuesta = client.get(f"/api/v1/mantenimientos/{mant['id']}/informe-url", headers=headers_autenticados)
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == "informe_no_disponible"


# ---- Transiciones de estado inválidas (409) — RN-MANT-01 --------------------


def test_iniciar_un_mantenimiento_ya_completado_falla(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT29-INIC2X")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id)
    _cerrar(client, headers_autenticados, mant["id"])

    respuesta = client.post(
        f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers_autenticados
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "transicion_invalida"


def test_cerrar_un_mantenimiento_ya_completado_falla(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT29-CERR2X")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id)
    _cerrar(client, headers_autenticados, mant["id"])

    segunda_vez = client.post(
        f"/api/v1/mantenimientos/{mant['id']}/cerrar",
        json={"fecha_ejecutada": date.today().isoformat()},
        headers=headers_autenticados,
    )
    assert segunda_vez.status_code == 409
    assert segunda_vez.json()["error"]["codigo"] == "transicion_invalida"


def test_cancelar_un_mantenimiento_ya_completado_falla(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT29-CANC2X")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id)
    _cerrar(client, headers_autenticados, mant["id"])

    respuesta = client.post(
        f"/api/v1/mantenimientos/{mant['id']}/cancelar",
        json={"motivo": "ya no aplica"},
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "transicion_invalida"


def test_cancelar_un_mantenimiento_en_ejecucion_revierte_el_equipo(
    client: TestClient, headers_autenticados: dict
):
    """A diferencia de cancelar uno 'programado' (ya cubierto en
    test_mantenimientos_alertas_sprint8.py), cancelar uno EN EJECUCIÓN debe
    revertir el estado del equipo — rama que antes no se ejercitaba."""
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT29-CANCEJEC")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id, tipo="correctivo")
    client.post(f"/api/v1/mantenimientos/{mant['id']}/iniciar", headers=headers_autenticados)
    assert (
        client.get(f"/api/v1/equipos/{equipo_id}", headers=headers_autenticados).json()["estado_operativo"]
        == "fuera_de_servicio"
    )

    cancelado = client.post(
        f"/api/v1/mantenimientos/{mant['id']}/cancelar",
        json={"motivo": "se resolvió de otra forma"},
        headers=headers_autenticados,
    )
    assert cancelado.status_code == 200
    assert cancelado.json()["estado"] == "cancelado"
    assert (
        client.get(f"/api/v1/equipos/{equipo_id}", headers=headers_autenticados).json()["estado_operativo"]
        == "operativo"
    )


def test_cerrar_sin_fecha_ejecutada_a_nivel_de_dominio_lanza_falta_fecha_ejecutada(
    client: TestClient, db: Session, crear_laboratorio_con_admin
):
    """La API nunca puede disparar esta ruta: `CerrarMantenimientoRequest.fecha_ejecutada`
    es un campo obligatorio de Pydantic, así que un `POST /cerrar` sin fecha
    ya falla con 422 antes de llegar al service (ver
    test_cerrar_sin_fecha_ejecutada_falla_validacion en
    test_mantenimientos_alertas_sprint8.py). El chequeo de
    `MantenimientoService.cerrar` (`FaltaFechaEjecutada`) es una segunda
    barrera de defensa en profundidad para cualquier llamador que no pase
    por esa validación — dataclasses de Python no fuerzan sus type hints en
    runtime, así que sí es alcanzable pasando `None` directo al service. El
    equipo/mantenimiento se crean vía la API real (mismo camino que el resto
    de este archivo); solo la llamada final a `cerrar()` se hace directo
    contra el service, con los mismos repositorios reales sin mocks, para
    ejercitar la rama que la API nunca puede alcanzar."""
    laboratorio_id, usuario_id, correo, password = crear_laboratorio_con_admin(
        "Lab Mant29 Dominio", "lab-mant29-dominio", "admin@lab-mant29-dominio.dev"
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": "lab-mant29-dominio", "correo": correo, "password": password},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    equipo_id = _crear_equipo(client, headers, "EQ-MANT29-DOM")
    mant = _crear_mantenimiento(client, headers, equipo_id)

    set_tenant_context(db, laboratorio_id)
    servicio = MantenimientoService(
        MantenimientoRepositorySQLAlchemy(db),
        EquipoRepositorySQLAlchemy(db),
        AdjuntoRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
        AlmacenamientoMinIO(get_settings().minio_bucket_evidencias),
        AlertaService(AlertaRepositorySQLAlchemy(db), NotificacionRepositorySQLAlchemy(db)),
        ConfiguracionRepositorySQLAlchemy(db),
    )
    actor = ActorContexto(usuario_id=usuario_id, ip_origen=None)

    with pytest.raises(FaltaFechaEjecutada):
        servicio.cerrar(
            uuid.UUID(mant["id"]),
            actor,
            DatosCierre(
                fecha_ejecutada=None,  # type: ignore[arg-type]
                repuestos_utilizados=None,
                tiempo_inactividad_horas=None,
                costo=None,
                descripcion=None,
            ),
        )


# ---- Validación de subida de archivos (422) — evidencia/informe ------------


def test_solicitar_url_evidencia_con_formato_no_permitido_falla(
    client: TestClient, headers_autenticados: dict
):
    respuesta = client.post(
        "/api/v1/mantenimientos/upload-url/evidencia",
        json={
            "nombre_archivo": "evidencia.exe",
            "tipo_mime": "application/x-msdownload",
            "tamano_bytes": 100,
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "formato_no_permitido"


def test_solicitar_url_evidencia_demasiado_grande_falla(client: TestClient, headers_autenticados: dict):
    respuesta = client.post(
        "/api/v1/mantenimientos/upload-url/evidencia",
        json={
            "nombre_archivo": "evidencia.jpg",
            "tipo_mime": "image/jpeg",
            "tamano_bytes": 11 * 1024 * 1024,  # límite real: 10 MB
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "archivo_demasiado_grande"


def test_solicitar_url_informe_con_formato_no_permitido_falla(
    client: TestClient, headers_autenticados: dict
):
    # Los informes solo admiten PDF — un JPG (válido para evidencia) debe
    # rechazarse acá, confirmando que las dos listas de formatos permitidos
    # (`FORMATOS_PERMITIDOS_EVIDENCIA` / `_INFORME`) no se mezclan.
    respuesta = client.post(
        "/api/v1/mantenimientos/upload-url/informe",
        json={"nombre_archivo": "informe.jpg", "tipo_mime": "image/jpeg", "tamano_bytes": 100},
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "formato_no_permitido"


def test_solicitar_url_evidencia_valida_devuelve_object_key_bajo_carpeta_evidencias(
    client: TestClient, headers_autenticados: dict
):
    respuesta = client.post(
        "/api/v1/mantenimientos/upload-url/evidencia",
        json={"nombre_archivo": "evidencia.jpg", "tipo_mime": "image/jpeg", "tamano_bytes": 1024},
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["object_key"].startswith("mantenimientos/evidencias/")


def test_solicitar_url_informe_valido_devuelve_object_key_bajo_carpeta_informes(
    client: TestClient, headers_autenticados: dict
):
    respuesta = client.post(
        "/api/v1/mantenimientos/upload-url/informe",
        json={"nombre_archivo": "informe.pdf", "tipo_mime": "application/pdf", "tamano_bytes": 1024},
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["object_key"].startswith("mantenimientos/informes/")


# ---- Evidencias e informe — flujo completo ----------------------------------


def test_agregar_y_listar_evidencias(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT29-EVID")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id)

    assert client.get(
        f"/api/v1/mantenimientos/{mant['id']}/evidencias", headers=headers_autenticados
    ).json() == []

    agregada = client.post(
        f"/api/v1/mantenimientos/{mant['id']}/evidencias",
        json={
            "object_key": "mantenimientos/evidencias/prueba.jpg",
            "nombre_archivo": "prueba.jpg",
            "tamano_bytes": 2048,
            "tipo_mime": "image/jpeg",
        },
        headers=headers_autenticados,
    )
    assert agregada.status_code == 201
    assert agregada.json()["nombre_archivo"] == "prueba.jpg"

    listado = client.get(
        f"/api/v1/mantenimientos/{mant['id']}/evidencias", headers=headers_autenticados
    ).json()
    assert len(listado) == 1

    url = client.get(
        f"/api/v1/mantenimientos/evidencias/{listado[0]['id']}/url", headers=headers_autenticados
    )
    assert url.status_code == 200
    assert url.json()["url"]


def test_asignar_informe_y_descargarlo(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT29-INF")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id)

    asignado = client.post(
        f"/api/v1/mantenimientos/{mant['id']}/informe",
        json={
            "object_key": "mantenimientos/informes/prueba.pdf",
            "nombre_archivo": "prueba.pdf",
            "tamano_bytes": 4096,
            "tipo_mime": "application/pdf",
        },
        headers=headers_autenticados,
    )
    assert asignado.status_code == 200
    assert asignado.json()["tiene_informe"] is True

    url = client.get(f"/api/v1/mantenimientos/{mant['id']}/informe-url", headers=headers_autenticados)
    assert url.status_code == 200
    assert url.json()["url"]


# ---- Lecturas auxiliares -----------------------------------------------------


def test_inactividad_por_equipo(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT29-INACT")
    mant = _crear_mantenimiento(client, headers_autenticados, equipo_id)
    client.post(
        f"/api/v1/mantenimientos/{mant['id']}/cerrar",
        json={"fecha_ejecutada": date.today().isoformat(), "tiempo_inactividad_horas": "4.5"},
        headers=headers_autenticados,
    )

    respuesta = client.get(
        "/api/v1/mantenimientos/inactividad",
        params={
            "equipo_id": equipo_id,
            "desde": date.today().replace(day=1).isoformat(),
            "hasta": date.today().isoformat(),
        },
        headers=headers_autenticados,
    )
    assert respuesta.status_code == 200
    assert float(respuesta.json()["horas"]) == 4.5


def test_mis_mantenimientos_de_hoy(client: TestClient, headers_autenticados: dict):
    equipo_id = _crear_equipo(client, headers_autenticados, "EQ-MANT29-HOY")
    _crear_mantenimiento(
        client, headers_autenticados, equipo_id, fecha_programada=date.today().isoformat()
    )

    respuesta = client.get("/api/v1/mantenimientos/hoy", headers=headers_autenticados)
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
