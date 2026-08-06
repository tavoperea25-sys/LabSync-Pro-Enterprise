"""Endpoints del Dashboard. Ver docs/03-requerimientos-funcionales.md
Módulo 2.

Agrega Equipos, Calibraciones, Documentos, Mantenimientos y Auditoría en un
único resumen — `DashboardService` reutiliza los repositorios de cada
módulo, nunca duplica sus reglas de negocio (rediseño Sprint 20, ver
docs/18-sprints.md)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.infrastructure.repositories import UsuarioRepositorySQLAlchemy
from app.modules.auth.presentation.dependencies import UsuarioContexto, requiere_permiso
from app.modules.calibraciones.infrastructure.repositories import CalibracionRepositorySQLAlchemy
from app.modules.dashboard.application.dashboard_service import DashboardService
from app.modules.dashboard.domain.entities import ActividadReciente, EquipoCritico, ResumenDashboard
from app.modules.dashboard.presentation.schemas import ActividadRecienteOut, EquipoCriticoOut, KpisOut
from app.modules.documentos.infrastructure.repositories import DocumentoRepositorySQLAlchemy
from app.modules.equipos.infrastructure.repositories import (
    AreaRepositorySQLAlchemy,
    EquipoRepositorySQLAlchemy,
)
from app.modules.mantenimientos.infrastructure.repositories import MantenimientoRepositorySQLAlchemy

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _service(db: Session) -> DashboardService:
    return DashboardService(
        EquipoRepositorySQLAlchemy(db),
        CalibracionRepositorySQLAlchemy(db),
        DocumentoRepositorySQLAlchemy(db),
        MantenimientoRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
        AreaRepositorySQLAlchemy(db),
        UsuarioRepositorySQLAlchemy(db),
    )


def _a_kpis_out(resumen: ResumenDashboard) -> KpisOut:
    return KpisOut(
        equipos_total=resumen.equipos_total,
        equipos_operativos=resumen.equipos_operativos,
        equipos_fuera_de_servicio=resumen.equipos_fuera_de_servicio,
        equipos_en_mantenimiento=resumen.equipos_en_mantenimiento,
        equipos_de_baja=resumen.equipos_de_baja,
        equipos_porcentaje_operativo=resumen.equipos_porcentaje_operativo,
        calibraciones_proximas_30_dias=resumen.calibraciones_proximas_30_dias,
        calibraciones_semaforo=resumen.calibraciones_semaforo,
        documentos_vencidos=resumen.documentos_vencidos,
        documentos_por_vencer=resumen.documentos_por_vencer,
        documentos_en_revision=resumen.documentos_en_revision,
        mantenimientos_preventivos_proximos=resumen.mantenimientos_preventivos_proximos,
        mantenimientos_correctivos_abiertos=resumen.mantenimientos_correctivos_abiertos,
        cumplimiento_documental_pct=resumen.cumplimiento_documental_pct,
    )


def _a_equipo_critico_out(fila: EquipoCritico) -> EquipoCriticoOut:
    return EquipoCriticoOut(
        equipo_id=fila.equipo_id,
        equipo_nombre=fila.equipo_nombre,
        equipo_codigo_interno=fila.equipo_codigo_interno,
        area_nombre=fila.area_nombre,
        estado_operativo=fila.estado_operativo,
        ultima_calibracion_fecha=fila.ultima_calibracion_fecha,
        proxima_calibracion_fecha=fila.proxima_calibracion_fecha,
        semaforo_calibracion=fila.semaforo_calibracion,
        responsable_nombre=fila.responsable_nombre,
    )


def _a_actividad_out(fila: ActividadReciente) -> ActividadRecienteOut:
    return ActividadRecienteOut(
        usuario_nombre=fila.usuario_nombre,
        accion=fila.accion,
        modulo=fila.modulo,
        entidad_tipo=fila.entidad_tipo,
        creado_en=fila.creado_en,
    )


@router.get("/kpis", response_model=KpisOut)
def obtener_kpis(
    db: Session = Depends(get_db), usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer"))
) -> KpisOut:
    return _a_kpis_out(_service(db).resumen(usuario.laboratorio_id))


@router.get("/equipos-criticos", response_model=list[EquipoCriticoOut])
def listar_equipos_criticos(
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
    limite: int = Query(default=10, ge=1, le=50),
) -> list[EquipoCriticoOut]:
    filas = _service(db).equipos_criticos(usuario.laboratorio_id, limite)
    return [_a_equipo_critico_out(f) for f in filas]


@router.get("/actividad-reciente", response_model=list[ActividadRecienteOut])
def listar_actividad_reciente(
    db: Session = Depends(get_db),
    # A diferencia de los otros dos endpoints, esto expone quién hizo qué
    # a través de todos los módulos — mismo permiso que la página de
    # Auditoría (RF-AUD-*), no "equipos.leer". El frontend solo renderiza
    # este widget si el rol del usuario tiene "auditoria.ver" (evita
    # solicitar un recurso que sabe de antemano que recibirá 403).
    usuario: UsuarioContexto = Depends(requiere_permiso("auditoria.ver")),
    limite: int = Query(default=8, ge=1, le=50),
) -> list[ActividadRecienteOut]:
    filas = _service(db).actividad_reciente(usuario.laboratorio_id, limite)
    return [_a_actividad_out(f) for f in filas]
