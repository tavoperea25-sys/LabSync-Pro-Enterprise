"""Endpoints de Calibraciones. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.database import get_db
from app.core.ip import ip_valida
from app.modules.adjuntos.infrastructure.repositories import AdjuntoRepositorySQLAlchemy
from app.modules.alertas.application.alerta_service import AlertaService
from app.modules.alertas.infrastructure.repositories import (
    AlertaRepositorySQLAlchemy,
    NotificacionRepositorySQLAlchemy,
)
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.presentation.dependencies import UsuarioContexto, requiere_permiso
from app.modules.calibraciones.application.calibracion_service import (
    ActorContexto,
    CalibracionService,
    DatosCalibracion,
)
from app.modules.calibraciones.domain.entities import Calibracion, EquipoConSemaforo, semaforo
from app.modules.calibraciones.infrastructure.repositories import CalibracionRepositorySQLAlchemy
from app.modules.calibraciones.presentation.schemas import (
    ArchivoCertificadoConfirmado,
    CalibracionOut,
    CalibracionRequest,
    CorregirCalibracionRequest,
    EquipoConSemaforoOut,
    UrlCertificadoOut,
    UrlCertificadoRequest,
    UrlDescargaOut,
)
from app.modules.equipos.infrastructure.repositories import EquipoRepositorySQLAlchemy

router = APIRouter(prefix="/api/v1", tags=["calibraciones"])

_almacenamiento = AlmacenamientoMinIO(get_settings().minio_bucket_evidencias)


def _service(db: Session) -> CalibracionService:
    return CalibracionService(
        CalibracionRepositorySQLAlchemy(db),
        EquipoRepositorySQLAlchemy(db),
        AdjuntoRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
        _almacenamiento,
        AlertaService(AlertaRepositorySQLAlchemy(db), NotificacionRepositorySQLAlchemy(db)),
    )


def _actor(request: Request, usuario: UsuarioContexto) -> ActorContexto:
    return ActorContexto(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )


def _a_datos(datos: CalibracionRequest) -> DatosCalibracion:
    return DatosCalibracion(
        equipo_id=datos.equipo_id,
        fecha_calibracion=datos.fecha_calibracion,
        frecuencia_meses=datos.frecuencia_meses,
        laboratorio_proveedor=datos.laboratorio_proveedor,
        numero_certificado=datos.numero_certificado,
        resultado=datos.resultado,
        incertidumbre=datos.incertidumbre,
        observaciones=datos.observaciones,
    )


def _a_certificado_tupla(
    certificado: ArchivoCertificadoConfirmado | None,
) -> tuple[str, str, int, str] | None:
    if certificado is None:
        return None
    return certificado.object_key, certificado.nombre_archivo, certificado.tamano_bytes, certificado.tipo_mime


def _a_out(calibracion: Calibracion) -> CalibracionOut:
    hoy = date.today()
    return CalibracionOut(
        id=calibracion.id,
        equipo_id=calibracion.equipo_id,
        fecha_calibracion=calibracion.fecha_calibracion,
        frecuencia_meses=calibracion.frecuencia_meses,
        proxima_fecha=calibracion.proxima_fecha,
        laboratorio_proveedor=calibracion.laboratorio_proveedor,
        numero_certificado=calibracion.numero_certificado,
        resultado=calibracion.resultado,
        incertidumbre=calibracion.incertidumbre,
        responsable_id=calibracion.responsable_id,
        corrige_a_id=calibracion.corrige_a_id,
        motivo_correccion=calibracion.motivo_correccion,
        observaciones=calibracion.observaciones,
        tiene_certificado=calibracion.certificado_adjunto_id is not None,
        semaforo=semaforo(calibracion.proxima_fecha, hoy),
        dias_restantes=(calibracion.proxima_fecha - hoy).days,
        creado_en=calibracion.creado_en,
    )


def _equipo_a_out(fila: EquipoConSemaforo) -> EquipoConSemaforoOut:
    return EquipoConSemaforoOut(
        equipo_id=fila.equipo_id,
        equipo_nombre=fila.equipo_nombre,
        equipo_codigo_interno=fila.equipo_codigo_interno,
        ultima_calibracion_id=fila.ultima_calibracion_id,
        proxima_fecha=fila.proxima_fecha,
        dias_restantes=fila.dias_restantes,
        semaforo=fila.semaforo,
    )


@router.post("/calibraciones/upload-url", response_model=UrlCertificadoOut)
def solicitar_url_certificado(
    datos: UrlCertificadoRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("calibraciones.crear")),
) -> UrlCertificadoOut:
    url, object_key = _service(db).solicitar_url_certificado(
        datos.nombre_archivo, datos.tipo_mime, datos.tamano_bytes
    )
    return UrlCertificadoOut(url_subida=url, object_key=object_key)


@router.post("/calibraciones", response_model=CalibracionOut, status_code=201)
def crear_calibracion(
    datos: CalibracionRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("calibraciones.crear")),
) -> CalibracionOut:
    calibracion = _service(db).crear(
        usuario.laboratorio_id,
        _actor(request, usuario),
        _a_datos(datos),
        certificado=_a_certificado_tupla(datos.certificado),
    )
    db.commit()
    return _a_out(calibracion)


@router.get("/calibraciones/criticas", response_model=list[EquipoConSemaforoOut])
def listar_criticos(
    db: Session = Depends(get_db), usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer"))
) -> list[EquipoConSemaforoOut]:
    return [_equipo_a_out(f) for f in _service(db).listar_criticos(usuario.laboratorio_id)]


@router.get("/calibraciones", response_model=list[CalibracionOut])
def listar_calibraciones(
    equipo_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> list[CalibracionOut]:
    return [_a_out(c) for c in _service(db).listar_por_equipo(equipo_id)]


@router.get("/calibraciones/{calibracion_id}", response_model=CalibracionOut)
def obtener_calibracion(
    calibracion_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> CalibracionOut:
    return _a_out(_service(db).obtener(calibracion_id))


@router.get("/calibraciones/{calibracion_id}/certificado-url", response_model=UrlDescargaOut)
def obtener_url_certificado(
    calibracion_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> UrlDescargaOut:
    return UrlDescargaOut(url=_service(db).url_certificado(calibracion_id))


@router.post("/calibraciones/{calibracion_id}/corregir", response_model=CalibracionOut, status_code=201)
def corregir_calibracion(
    calibracion_id: uuid.UUID,
    datos: CorregirCalibracionRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("calibraciones.crear")),
) -> CalibracionOut:
    calibracion = _service(db).corregir(
        calibracion_id,
        _actor(request, usuario),
        _a_datos(datos),
        datos.motivo,
        certificado=_a_certificado_tupla(datos.certificado),
    )
    db.commit()
    return _a_out(calibracion)
