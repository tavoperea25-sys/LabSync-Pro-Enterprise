"""Pruebas de Sprint 12: módulo Configuración — umbrales configurables
(RF-CFG-03) y su efecto real en Calibraciones, política de contraseña
configurable (RF-CFG-03/RF-USR-05), perfil propio (RF-CFG-01), datos
institucionales (RF-CFG-04) y CRUD de categorías/áreas (RF-CFG-05)."""

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
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-cfg12-{sufijo}"
    laboratorio_id, admin_id, correo, password = crear_laboratorio_con_admin(
        "Lab Cfg12", slug, f"admin-{sufijo}@cfg12.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {
        "slug": slug,
        "laboratorio_id": laboratorio_id,
        "admin_id": admin_id,
        "correo": correo,
        "password": password,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


def _rol_id(client: TestClient, headers: dict, nombre: str) -> str:
    roles = client.get("/api/v1/roles", headers=headers).json()
    return next(r["id"] for r in roles if r["nombre"] == nombre)


def _crear_tecnico(client: TestClient, headers: dict, slug: str) -> dict:
    password = "Cl4veSegura!2026"
    correo = f"tec-{uuid.uuid4().hex[:8]}@cfg12.dev"
    creado = client.post(
        "/api/v1/usuarios",
        json={
            "nombre_completo": "Técnico de prueba",
            "correo": correo,
            "password": password,
            "rol_ids": [_rol_id(client, headers, "tecnico")],
        },
        headers=headers,
    )
    assert creado.status_code == 201, creado.text
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    return {"headers": {"Authorization": f"Bearer {login.json()['access_token']}"}, "correo": correo}


def _crear_equipo(client: TestClient, headers: dict, codigo: str = "EQ-CFG12", **overrides) -> dict:
    payload = {"codigo_interno": codigo, "nombre": "Equipo Config", **overrides}
    respuesta = client.post("/api/v1/equipos", json=payload, headers=headers)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# ---- RF-CFG-03 — umbrales -----------------------------------------------


def test_obtener_configuracion_sin_fila_devuelve_defaults(client: TestClient, contexto: dict):
    respuesta = client.get("/api/v1/configuracion", headers=contexto["headers"])
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo == {
        "umbral_alerta_calibracion_dias": 30,
        "umbral_alerta_mantenimiento_dias": 15,
        "umbral_alerta_documento_dias": 30,
        "dias_retencion_papelera_documentos": 30,
        "politica_password": None,
        "mapeo_estados_mantenimiento": None,
    }


def test_actualizar_umbrales_persiste(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    respuesta = client.patch(
        "/api/v1/configuracion/umbrales",
        json={
            "umbral_alerta_calibracion_dias": 45,
            "umbral_alerta_mantenimiento_dias": 20,
            "umbral_alerta_documento_dias": 10,
            "dias_retencion_papelera_documentos": 30,
        },
        headers=headers,
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["umbral_alerta_calibracion_dias"] == 45

    releido = client.get("/api/v1/configuracion", headers=headers)
    assert releido.json()["umbral_alerta_mantenimiento_dias"] == 20


def test_actualizar_umbrales_rechaza_valores_no_positivos(client: TestClient, contexto: dict):
    respuesta = client.patch(
        "/api/v1/configuracion/umbrales",
        json={
            "umbral_alerta_calibracion_dias": 0,
            "umbral_alerta_mantenimiento_dias": 20,
            "umbral_alerta_documento_dias": 10,
            "dias_retencion_papelera_documentos": 30,
        },
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422


def test_umbral_calibracion_configurado_afecta_el_semaforo_real(client: TestClient, contexto: dict):
    """Prueba de integración de extremo a extremo para RF-CFG-03: el umbral
    configurado debe reflejarse en el cálculo real de Calibraciones, no solo
    quedar guardado en la tabla de configuración."""
    headers = contexto["headers"]
    equipo = _crear_equipo(client, headers)
    creada = client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo["id"],
            "fecha_calibracion": date.today().isoformat(),
            "frecuencia_meses": 12,
            "resultado": "conforme",
        },
        headers=headers,
    )
    assert creada.status_code == 201, creada.text

    # ~365 días por delante y el umbral por defecto es 30 -> verde, y por
    # tanto excluido del listado de "críticas" (RF-CAL-05 solo trae
    # rojo/amarillo/gris).
    criticas_antes = client.get("/api/v1/calibraciones/criticas", headers=headers).json()
    assert equipo["id"] not in {c["equipo_id"] for c in criticas_antes}

    subir_umbral = client.patch(
        "/api/v1/configuracion/umbrales",
        json={
            "umbral_alerta_calibracion_dias": 400,
            "umbral_alerta_mantenimiento_dias": 15,
            "umbral_alerta_documento_dias": 30,
            "dias_retencion_papelera_documentos": 30,
        },
        headers=headers,
    )
    assert subir_umbral.status_code == 200

    criticas_despues = client.get("/api/v1/calibraciones/criticas", headers=headers).json()
    fila = next(c for c in criticas_despues if c["equipo_id"] == equipo["id"])
    assert fila["semaforo"] == "amarillo"


# ---- RF-CFG-03 / RF-USR-05 — política de contraseña ------------------------


def test_actualizar_politica_password_rechaza_clave_desconocida(client: TestClient, contexto: dict):
    respuesta = client.patch(
        "/api/v1/configuracion/politica-password",
        json={"politica_password": {"clave_invalida": True}},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "politica_password_invalida"


def test_politica_password_configurada_afecta_creacion_de_usuarios(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    configurar = client.patch(
        "/api/v1/configuracion/politica-password",
        json={"politica_password": {"longitud_minima": 20}},
        headers=headers,
    )
    assert configurar.status_code == 200

    # Cumple la política vieja (10 caracteres, todo tipo de carácter) pero no
    # la nueva (20 caracteres mínimo).
    respuesta = client.post(
        "/api/v1/usuarios",
        json={
            "nombre_completo": "Usuario corto",
            "correo": f"corto-{uuid.uuid4().hex[:8]}@cfg12.dev",
            "password": "Cort4!Pass",
            "rol_ids": [_rol_id(client, headers, "tecnico")],
        },
        headers=headers,
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "password_no_cumple_politica"


# ---- RF-CFG-01 — perfil propio ---------------------------------------------


def test_actualizar_mi_perfil(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    respuesta = client.patch(
        "/api/v1/usuarios/me",
        json={"nombre_completo": "Nombre Actualizado", "correo": contexto["correo"]},
        headers=headers,
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre_completo"] == "Nombre Actualizado"


def test_actualizar_mi_perfil_correo_duplicado_falla(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    tecnico = _crear_tecnico(client, headers, contexto["slug"])

    respuesta = client.patch(
        "/api/v1/usuarios/me",
        json={"nombre_completo": "Técnico", "correo": contexto["correo"]},
        headers=tecnico["headers"],
    )
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "correo_ya_registrado"


def test_cambiar_mi_password_con_password_actual_incorrecta_falla(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/usuarios/me/cambiar-password",
        json={"password_actual": "Incorrecta!123", "password_nueva": "NuevaClave!456"},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "password_actual_incorrecta"


def test_cambiar_mi_password_exitoso_revoca_sesiones_y_permite_login_con_la_nueva(
    client: TestClient, contexto: dict
):
    headers = contexto["headers"]
    nueva_password = "NuevaClaveSegura!789"
    respuesta = client.post(
        "/api/v1/usuarios/me/cambiar-password",
        json={"password_actual": contexto["password"], "password_nueva": nueva_password},
        headers=headers,
    )
    assert respuesta.status_code == 204

    # El access token viejo sigue siendo válido como JWT (no hay revocación
    # de access tokens, solo de sesiones/refresh — igual que RN-USR-01), pero
    # la contraseña vieja ya no debe servir para un login nuevo.
    login_password_vieja = client.post(
        "/api/v1/auth/login",
        json={
            "laboratorio_slug": contexto["slug"],
            "correo": contexto["correo"],
            "password": contexto["password"],
        },
    )
    assert login_password_vieja.status_code == 401

    login_password_nueva = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": contexto["slug"], "correo": contexto["correo"], "password": nueva_password},
    )
    assert login_password_nueva.status_code == 200


# ---- RF-CFG-04 — institución ------------------------------------------------


def test_obtener_y_actualizar_institucion(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    inicial = client.get("/api/v1/configuracion/institucion", headers=headers)
    assert inicial.status_code == 200
    assert inicial.json()["logo_url"] is None

    actualizada = client.patch(
        "/api/v1/configuracion/institucion",
        json={"nombre": "Laboratorio Renombrado", "logo_object_key": None},
        headers=headers,
    )
    assert actualizada.status_code == 200
    assert actualizada.json()["nombre"] == "Laboratorio Renombrado"


def test_solicitar_url_logo_formato_no_soportado_falla(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/configuracion/institucion/logo-upload-url",
        json={"nombre_archivo": "logo.gif", "tipo_mime": "image/gif", "tamano_bytes": 1000},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["codigo"] == "formato_logo_no_soportado"


def test_solicitar_url_logo_formato_valido_devuelve_url_de_subida(client: TestClient, contexto: dict):
    respuesta = client.post(
        "/api/v1/configuracion/institucion/logo-upload-url",
        json={"nombre_archivo": "logo.png", "tipo_mime": "image/png", "tamano_bytes": 1000},
        headers=contexto["headers"],
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["url_subida"].startswith("http")
    assert cuerpo["object_key"].endswith(".png")


# ---- RF-CFG-05 — categorías y áreas -----------------------------------------


def test_crud_categoria_equipo(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    creada = client.post(
        "/api/v1/categorias-equipo",
        json={"nombre": "Balanzas", "frecuencia_calibracion_default_meses": 6},
        headers=headers,
    )
    assert creada.status_code == 201, creada.text
    categoria_id = creada.json()["id"]

    duplicada = client.post(
        "/api/v1/categorias-equipo",
        json={"nombre": "Balanzas", "frecuencia_calibracion_default_meses": 6},
        headers=headers,
    )
    assert duplicada.status_code == 409

    frecuencia_invalida = client.patch(
        f"/api/v1/categorias-equipo/{categoria_id}",
        json={"nombre": "Balanzas", "frecuencia_calibracion_default_meses": 0},
        headers=headers,
    )
    assert frecuencia_invalida.status_code == 422

    actualizada = client.patch(
        f"/api/v1/categorias-equipo/{categoria_id}",
        json={"nombre": "Balanzas Analíticas", "frecuencia_calibracion_default_meses": 12},
        headers=headers,
    )
    assert actualizada.status_code == 200
    assert actualizada.json()["nombre"] == "Balanzas Analíticas"

    _crear_equipo(client, headers, "EQ-CFG12-BAL", categoria_id=categoria_id)
    en_uso = client.delete(f"/api/v1/categorias-equipo/{categoria_id}", headers=headers)
    assert en_uso.status_code == 409
    assert en_uso.json()["error"]["codigo"] == "categoria_en_uso"


def test_crud_area(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    creada = client.post("/api/v1/areas", json={"nombre": "Fisicoquímica"}, headers=headers)
    assert creada.status_code == 201, creada.text
    area_id = creada.json()["id"]

    actualizada = client.patch(
        f"/api/v1/areas/{area_id}", json={"nombre": "Fisicoquímica II"}, headers=headers
    )
    assert actualizada.status_code == 200

    eliminada = client.delete(f"/api/v1/areas/{area_id}", headers=headers)
    assert eliminada.status_code == 204

    obtener_areas = client.get("/api/v1/areas", headers=headers).json()
    assert area_id not in {a["id"] for a in obtener_areas}


def test_eliminar_area_en_uso_falla(client: TestClient, contexto: dict):
    headers = contexto["headers"]
    creada = client.post("/api/v1/areas", json={"nombre": "Microbiología"}, headers=headers)
    area_id = creada.json()["id"]
    _crear_equipo(client, headers, "EQ-CFG12-AREA", area_id=area_id)

    respuesta = client.delete(f"/api/v1/areas/{area_id}", headers=headers)
    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["codigo"] == "area_en_uso"


# ---- Permisos ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("GET", "/api/v1/configuracion", None),
        (
            "PATCH",
            "/api/v1/configuracion/umbrales",
            {
                "umbral_alerta_calibracion_dias": 30,
                "umbral_alerta_mantenimiento_dias": 15,
                "umbral_alerta_documento_dias": 30,
            },
        ),
        ("GET", "/api/v1/configuracion/institucion", None),
        ("POST", "/api/v1/categorias-equipo", {"nombre": "X", "frecuencia_calibracion_default_meses": None}),
        ("POST", "/api/v1/areas", {"nombre": "Y"}),
    ],
)
def test_endpoints_de_configuracion_requieren_permiso_dedicado(
    client: TestClient, contexto: dict, metodo: str, ruta: str, cuerpo: dict | None
):
    tecnico = _crear_tecnico(client, contexto["headers"], contexto["slug"])
    respuesta = client.request(metodo, ruta, json=cuerpo, headers=tecnico["headers"])
    assert respuesta.status_code == 403


def test_perfil_propio_no_requiere_permiso_de_configuracion(client: TestClient, contexto: dict):
    """A diferencia de `configuracion.gestionar`, RF-CFG-01 es de cualquier
    usuario autenticado sobre sí mismo — el técnico sin ese permiso sí debe
    poder editar su propio perfil."""
    tecnico = _crear_tecnico(client, contexto["headers"], contexto["slug"])
    respuesta = client.patch(
        "/api/v1/usuarios/me",
        json={"nombre_completo": "Técnico Renombrado", "correo": tecnico["correo"]},
        headers=tecnico["headers"],
    )
    assert respuesta.status_code == 200
