"""Endpoints de Configuración — RF-CFG-03/04 (Sprint 12). Ver docs/15-api-design.md.

RF-CFG-05 (categorías/áreas) vive en `equipos/presentation/router.py` — ver
docstring de `ReferenciaService`. RF-CFG-01/02 (perfil propio, tema) viven en
`auth/presentation/usuarios_router.py` (`/usuarios/me`) y el frontend
(`ThemeProvider`) respectivamente — Configuración expone aquí solo lo que
RF-CFG-03/04 asignan al Administrador: umbrales, política de contraseña y
datos institucionales."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.database import get_db
from app.core.ip import ip_valida
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.infrastructure.repositories import (
    LaboratorioRepositorySQLAlchemy,
    UsuarioRepositorySQLAlchemy,
)
from app.modules.auth.presentation.dependencies import UsuarioContexto, requiere_permiso
from app.modules.calibraciones.infrastructure.repositories import CalibracionRepositorySQLAlchemy
from app.modules.configuracion.application.configuracion_service import ActorContexto, ConfiguracionService
from app.modules.configuracion.application.exportacion_service import (
    ExportacionDatosService,
    RepositoriosExportacion,
)
from app.modules.configuracion.infrastructure.repositories import ConfiguracionRepositorySQLAlchemy
from app.modules.configuracion.presentation.schemas import (
    ActualizarInstitucionRequest,
    ActualizarMapeoEstadosMantenimientoRequest,
    ActualizarPoliticaPasswordRequest,
    ActualizarUmbralesRequest,
    ConfiguracionOut,
    InstitucionOut,
    SolicitarLogoRequest,
    UrlSubidaLogoOut,
)
from app.modules.documentos.infrastructure.repositories import DocumentoRepositorySQLAlchemy
from app.modules.equipos.infrastructure.repositories import (
    AreaRepositorySQLAlchemy,
    CategoriaEquipoRepositorySQLAlchemy,
    EquipoRepositorySQLAlchemy,
)
from app.modules.mantenimientos.infrastructure.repositories import MantenimientoRepositorySQLAlchemy

router = APIRouter(prefix="/api/v1/configuracion", tags=["configuracion"])

_almacenamiento_logos = AlmacenamientoMinIO(get_settings().minio_bucket_logos)


def _service(db: Session) -> ConfiguracionService:
    return ConfiguracionService(
        ConfiguracionRepositorySQLAlchemy(db),
        LaboratorioRepositorySQLAlchemy(db),
        _almacenamiento_logos,
        AuditoriaRepositorySQLAlchemy(db),
    )


def _exportacion_service(db: Session) -> ExportacionDatosService:
    repos = RepositoriosExportacion(
        equipos=EquipoRepositorySQLAlchemy(db),
        documentos=DocumentoRepositorySQLAlchemy(db),
        calibraciones=CalibracionRepositorySQLAlchemy(db),
        mantenimientos=MantenimientoRepositorySQLAlchemy(db),
        usuarios=UsuarioRepositorySQLAlchemy(db),
        categorias=CategoriaEquipoRepositorySQLAlchemy(db),
        areas=AreaRepositorySQLAlchemy(db),
    )
    return ExportacionDatosService(repos, AuditoriaRepositorySQLAlchemy(db))


def _actor(request: Request, usuario: UsuarioContexto) -> ActorContexto:
    return ActorContexto(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )


def _a_configuracion_out(config) -> ConfiguracionOut:  # type: ignore[no-untyped-def]
    return ConfiguracionOut(
        umbral_alerta_calibracion_dias=config.umbral_alerta_calibracion_dias,
        umbral_alerta_mantenimiento_dias=config.umbral_alerta_mantenimiento_dias,
        umbral_alerta_documento_dias=config.umbral_alerta_documento_dias,
        dias_retencion_papelera_documentos=config.dias_retencion_papelera_documentos,
        politica_password=config.politica_password,
        mapeo_estados_mantenimiento=config.mapeo_estados_mantenimiento,
    )


@router.get("", response_model=ConfiguracionOut)
def obtener_configuracion(
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> ConfiguracionOut:
    return _a_configuracion_out(_service(db).obtener(usuario.laboratorio_id))


@router.patch("/umbrales", response_model=ConfiguracionOut)
def actualizar_umbrales(
    datos: ActualizarUmbralesRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> ConfiguracionOut:
    config = _service(db).actualizar_umbrales(
        usuario.laboratorio_id,
        _actor(request, usuario),
        umbral_alerta_calibracion_dias=datos.umbral_alerta_calibracion_dias,
        umbral_alerta_mantenimiento_dias=datos.umbral_alerta_mantenimiento_dias,
        umbral_alerta_documento_dias=datos.umbral_alerta_documento_dias,
        dias_retencion_papelera_documentos=datos.dias_retencion_papelera_documentos,
    )
    db.commit()
    return _a_configuracion_out(config)


@router.patch("/politica-password", response_model=ConfiguracionOut)
def actualizar_politica_password(
    datos: ActualizarPoliticaPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> ConfiguracionOut:
    config = _service(db).actualizar_politica_password(
        usuario.laboratorio_id, _actor(request, usuario), datos.politica_password
    )
    db.commit()
    return _a_configuracion_out(config)


@router.patch("/mapeo-estados-mantenimiento", response_model=ConfiguracionOut)
def actualizar_mapeo_estados_mantenimiento(
    datos: ActualizarMapeoEstadosMantenimientoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> ConfiguracionOut:
    """RN-MANT-01."""
    config = _service(db).actualizar_mapeo_estados_mantenimiento(
        usuario.laboratorio_id, _actor(request, usuario), datos.mapeo_estados_mantenimiento
    )
    db.commit()
    return _a_configuracion_out(config)


def _a_institucion_out(service: ConfiguracionService, laboratorio) -> InstitucionOut:  # type: ignore[no-untyped-def]
    return InstitucionOut(
        id=laboratorio.id,
        nombre=laboratorio.nombre,
        slug=laboratorio.slug,
        logo_url=service.url_logo(laboratorio),
        logo_object_key=laboratorio.logo_object_key,
    )


@router.get("/institucion", response_model=InstitucionOut)
def obtener_institucion(
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> InstitucionOut:
    service = _service(db)
    laboratorio = service.obtener_institucion(usuario.laboratorio_id)
    return _a_institucion_out(service, laboratorio)


@router.patch("/institucion", response_model=InstitucionOut)
def actualizar_institucion(
    datos: ActualizarInstitucionRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> InstitucionOut:
    service = _service(db)
    laboratorio = service.actualizar_institucion(
        usuario.laboratorio_id, _actor(request, usuario), datos.nombre, datos.logo_object_key
    )
    db.commit()
    return _a_institucion_out(service, laboratorio)


@router.post("/institucion/logo-upload-url", response_model=UrlSubidaLogoOut)
def solicitar_url_logo(
    datos: SolicitarLogoRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> UrlSubidaLogoOut:
    url, object_key = _service(db).solicitar_url_logo(
        datos.nombre_archivo, datos.tipo_mime, datos.tamano_bytes
    )
    return UrlSubidaLogoOut(url_subida=url, object_key=object_key)


@router.get("/exportar-datos")
def exportar_datos_tenant(
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("configuracion.gestionar")),
) -> StreamingResponse:
    """Portabilidad de datos del tenant (Sprint 13, docs/17-roadmap.md Fase 5)
    — ZIP de CSVs de equipos/documentos/calibraciones/mantenimientos/usuarios/
    categorías/áreas. Síncrono (ver docstring de exportador_datos.py)."""
    contenido = _exportacion_service(db).generar_zip(usuario.laboratorio_id, _actor(request, usuario))
    db.commit()
    return StreamingResponse(
        iter([contenido]),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=labsync-exportacion-datos.zip"},
    )
