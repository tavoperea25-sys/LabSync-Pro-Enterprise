"""Endpoints de Reportes — RF-REP-01 a 08, RNF-PERF-04 (Sprint 11).
Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import RecursoNoEncontrado
from app.core.ip import ip_valida
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.infrastructure.repositories import LaboratorioRepositorySQLAlchemy
from app.modules.auth.presentation.dependencies import UsuarioContexto, requiere_permiso
from app.modules.calibraciones.infrastructure.repositories import CalibracionRepositorySQLAlchemy
from app.modules.documentos.infrastructure.repositories import DocumentoRepositorySQLAlchemy
from app.modules.equipos.infrastructure.repositories import (
    AreaRepositorySQLAlchemy,
    CategoriaEquipoRepositorySQLAlchemy,
    EquipoRepositorySQLAlchemy,
)
from app.modules.mantenimientos.infrastructure.repositories import MantenimientoRepositorySQLAlchemy
from app.modules.reportes.application.generadores import RepositoriosReporte
from app.modules.reportes.application.reporte_service import ActorContexto, ReporteService
from app.modules.reportes.domain.entities import FORMATOS_POR_TIPO, TIPOS_REPORTE, ReporteGenerado
from app.modules.reportes.infrastructure.repositories import ReporteRepositorySQLAlchemy
from app.modules.reportes.presentation.schemas import (
    GenerarReporteRequest,
    ReporteOut,
    TipoReporteOut,
    UrlDescargaOut,
)

router = APIRouter(prefix="/api/v1/reportes", tags=["reportes"])

_ETIQUETAS_TIPO = {
    "inventario": "Inventario de equipos",
    "calibraciones": "Estado de calibraciones",
    "vencidos": "Equipos vencidos",
    "cumplimiento": "Indicadores de cumplimiento",
    "mantenimiento": "Historial de mantenimiento",
    "trazabilidad_documental": "Trazabilidad documental",
    "paquete_auditoria": "Paquete de auditoría ISO 15189",
}

_almacenamiento = AlmacenamientoMinIO(get_settings().minio_bucket_reportes)
_almacenamiento_logos = AlmacenamientoMinIO(get_settings().minio_bucket_logos)


def _service(db: Session) -> ReporteService:
    categorias = {c.id: c.nombre for c in CategoriaEquipoRepositorySQLAlchemy(db).listar()}
    areas = {a.id: a.nombre for a in AreaRepositorySQLAlchemy(db).listar()}
    repos = RepositoriosReporte(
        equipos=EquipoRepositorySQLAlchemy(db),
        categorias_por_id=categorias,
        areas_por_id=areas,
        calibraciones=CalibracionRepositorySQLAlchemy(db),
        mantenimientos=MantenimientoRepositorySQLAlchemy(db),
        documentos=DocumentoRepositorySQLAlchemy(db),
    )
    return ReporteService(
        ReporteRepositorySQLAlchemy(db),
        repos,
        _almacenamiento,
        AuditoriaRepositorySQLAlchemy(db),
        LaboratorioRepositorySQLAlchemy(db),
        _almacenamiento_logos,
    )


def _actor(request: Request, usuario: UsuarioContexto) -> ActorContexto:
    return ActorContexto(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )


def _a_out(reporte: ReporteGenerado) -> ReporteOut:
    return ReporteOut(
        id=reporte.id,
        tipo=reporte.tipo,
        formato=reporte.formato,
        filtros=reporte.filtros,
        estado=reporte.estado,
        nombre_archivo=reporte.nombre_archivo,
        error=reporte.error,
        creado_en=reporte.creado_en,
        completado_en=reporte.completado_en,
    )


@router.get("/tipos", response_model=list[TipoReporteOut])
def listar_tipos(
    _usuario: UsuarioContexto = Depends(requiere_permiso("reportes.generar")),
) -> list[TipoReporteOut]:
    return [
        TipoReporteOut(tipo=t, etiqueta=_ETIQUETAS_TIPO[t], formatos_disponibles=list(FORMATOS_POR_TIPO[t]))
        for t in TIPOS_REPORTE
    ]


@router.get("/historial", response_model=list[ReporteOut])
def listar_historial(
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("reportes.generar")),
) -> list[ReporteOut]:
    return [_a_out(r) for r in _service(db).listar_historial(usuario.laboratorio_id)]


@router.post("/generar", response_model=ReporteOut, status_code=201)
def generar_reporte(
    datos: GenerarReporteRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("reportes.generar")),
) -> ReporteOut:
    reporte, _contenido = _service(db).generar(
        usuario.laboratorio_id, _actor(request, usuario), datos.tipo, datos.formato, datos.filtros
    )
    db.commit()
    return _a_out(reporte)


@router.get("/{reporte_id}", response_model=ReporteOut)
def obtener_reporte(
    reporte_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("reportes.generar")),
) -> ReporteOut:
    reporte = ReporteRepositorySQLAlchemy(db).obtener_por_id(reporte_id)
    if reporte is None:
        raise RecursoNoEncontrado("reporte_no_encontrado", "El reporte no existe.")
    return _a_out(reporte)


@router.get("/{reporte_id}/descargar", response_model=UrlDescargaOut)
def descargar_reporte(
    reporte_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("reportes.generar")),
) -> UrlDescargaOut:
    reporte = ReporteRepositorySQLAlchemy(db).obtener_por_id(reporte_id)
    if reporte is None:
        raise RecursoNoEncontrado("reporte_no_encontrado", "El reporte no existe.")
    if not reporte.esta_listo() or reporte.object_key is None:
        raise RecursoNoEncontrado(
            "reporte_no_disponible", "Este reporte todavía no está listo para descargar."
        )
    url = _almacenamiento.url_descarga(reporte.object_key, reporte.nombre_archivo or "reporte")
    return UrlDescargaOut(url=url)
