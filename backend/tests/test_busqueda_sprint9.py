"""Pruebas de Sprint 9: Búsqueda Global (RF-SEARCH-01 a 05)."""

from __future__ import annotations

import uuid

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.core.security import hash_password
from app.main import app
from app.modules.auth.infrastructure.models import Rol, Usuario, UsuarioRol


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def contexto(client: TestClient, crear_laboratorio_con_admin):
    sufijo = uuid.uuid4().hex[:8]
    slug = f"lab-search9-{sufijo}"
    laboratorio_id, _, correo, password = crear_laboratorio_con_admin(
        "Lab Search9", slug, f"admin-{sufijo}@search9.dev"
    )
    login = client.post(
        "/api/v1/auth/login", json={"laboratorio_slug": slug, "correo": correo, "password": password}
    )
    assert login.status_code == 200
    headers_admin = {"Authorization": f"Bearer {login.json()['access_token']}"}

    return {"laboratorio_id": laboratorio_id, "slug": slug, "headers_admin": headers_admin}


def _crear_usuario_consulta(db: Session, laboratorio_id: uuid.UUID, correo: str, password: str) -> None:
    """RF-SEARCH-05 — un rol sin `usuarios.administrar` (consulta) se usa
    para verificar que la categoría "usuario" se excluye de sus resultados."""
    set_tenant_context(db, laboratorio_id)
    rol_consulta = db.query(Rol).filter_by(nombre="consulta", laboratorio_id=None).one()
    usuario = Usuario(
        id=uuid.uuid4(),
        laboratorio_id=laboratorio_id,
        correo=correo,
        password_hash=hash_password(password),
        nombre_completo="Usuario Consulta",
        estado="activo",
        debe_cambiar_password=False,
    )
    db.add(usuario)
    db.flush()
    db.add(UsuarioRol(usuario_id=usuario.id, rol_id=rol_consulta.id, laboratorio_id=laboratorio_id))
    db.commit()


def _crear_equipo(client: TestClient, headers: dict, codigo: str) -> str:
    respuesta = client.post(
        "/api/v1/equipos",
        json={"codigo_interno": codigo, "nombre": "Espectrofotómetro UV-Vis"},
        headers=headers,
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def _buscar(client: TestClient, headers: dict, q: str) -> list[dict]:
    respuesta = client.get("/api/v1/busqueda", params={"q": q}, headers=headers)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def test_busqueda_encuentra_equipo_por_nombre_y_codigo(client: TestClient, contexto: dict):
    headers = contexto["headers_admin"]
    equipo_id = _crear_equipo(client, headers, "EQ-SEARCH9-1")

    por_nombre = _buscar(client, headers, "Espectrofotómetro")
    assert any(r["tipo"] == "equipo" and r["id"] == equipo_id for r in por_nombre)

    por_codigo = _buscar(client, headers, "EQ-SEARCH9-1")
    assert any(r["tipo"] == "equipo" and r["id"] == equipo_id for r in por_codigo)


def test_busqueda_encuentra_documento_por_nombre(client: TestClient, contexto: dict):
    headers = contexto["headers_admin"]
    contenido = b"%PDF-1.4 prueba busqueda"
    solicitud = client.post(
        "/api/v1/documentos/upload-url",
        json={"nombre_archivo": "manual.pdf", "tipo_mime": "application/pdf", "tamano_bytes": len(contenido)},
        headers=headers,
    )
    datos = solicitud.json()
    httpx.put(datos["url_subida"], content=contenido, headers={"Content-Type": "application/pdf"})
    creado = client.post(
        "/api/v1/documentos",
        json={
            "nombre": "Manual de bioseguridad institucional",
            "archivo": {
                "object_key": datos["object_key"],
                "nombre_archivo": "manual.pdf",
                "tamano_bytes": len(contenido),
                "tipo_mime": "application/pdf",
            },
        },
        headers=headers,
    ).json()

    resultados = _buscar(client, headers, "bioseguridad")
    assert any(r["tipo"] == "documento" and r["id"] == creado["id"] for r in resultados)


def test_busqueda_encuentra_certificado_de_calibracion(client: TestClient, contexto: dict):
    headers = contexto["headers_admin"]
    equipo_id = _crear_equipo(client, headers, "EQ-SEARCH9-2")
    client.post(
        "/api/v1/calibraciones",
        json={
            "equipo_id": equipo_id,
            "fecha_calibracion": "2026-01-01",
            "frecuencia_meses": 12,
            "resultado": "conforme",
            "numero_certificado": "CERT-SEARCH9-XYZ",
        },
        headers=headers,
    )

    resultados = _buscar(client, headers, "CERT-SEARCH9-XYZ")
    assert any(r["tipo"] == "calibracion" and r["ruta"] == f"/equipos/{equipo_id}" for r in resultados)


def test_busqueda_encuentra_mantenimiento_por_descripcion(client: TestClient, contexto: dict):
    headers = contexto["headers_admin"]
    equipo_id = _crear_equipo(client, headers, "EQ-SEARCH9-3")
    client.post(
        "/api/v1/mantenimientos",
        json={"equipo_id": equipo_id, "tipo": "correctivo", "descripcion": "Cambio de fusible principal"},
        headers=headers,
    )

    resultados = _buscar(client, headers, "fusible")
    assert any(r["tipo"] == "mantenimiento" and r["ruta"] == f"/equipos/{equipo_id}" for r in resultados)


def test_busqueda_con_consulta_corta_devuelve_vacio(client: TestClient, contexto: dict):
    assert _buscar(client, contexto["headers_admin"], "a") == []


def test_busqueda_de_usuarios_restringida_por_permiso(client: TestClient, contexto: dict, db: Session):
    headers_admin = contexto["headers_admin"]

    # El admin (usuarios.administrar) sí ve resultados de tipo "usuario".
    # `crear_laboratorio_con_admin` nombra al usuario "Admin {nombre_lab}" —
    # "Search9" (parte de "Lab Search9") es el término único de esta prueba.
    resultados_admin = _buscar(client, headers_admin, "Search9")
    assert any(r["tipo"] == "usuario" for r in resultados_admin)

    # Un usuario con rol "consulta" (sin usuarios.administrar) no debe ver
    # esa categoría, aunque la consulta coincida con un nombre real.
    correo_consulta = f"consulta-{uuid.uuid4().hex[:8]}@search9.dev"
    password_consulta = "Passw0rd!Segura"
    _crear_usuario_consulta(db, contexto["laboratorio_id"], correo_consulta, password_consulta)

    login_consulta = client.post(
        "/api/v1/auth/login",
        json={"laboratorio_slug": contexto["slug"], "correo": correo_consulta, "password": password_consulta},
    )
    assert login_consulta.status_code == 200
    headers_consulta = {"Authorization": f"Bearer {login_consulta.json()['access_token']}"}

    resultados_consulta = _buscar(client, headers_consulta, "Search9")
    assert all(r["tipo"] != "usuario" for r in resultados_consulta)
