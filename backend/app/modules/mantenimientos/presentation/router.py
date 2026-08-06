"""Endpoints de Mantenimientos. Ver docs/15-api-design.md."""

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
from app.modules.configuracion.infrastructure.repositories import ConfiguracionRepositorySQLAlchemy
from app.modules.equipos.infrastructure.repositories import EquipoRepositorySQLAlchemy
from app.modules.mantenimientos.application.mantenimiento_service import (
    ActorContexto,
    DatosCierre,
    DatosMantenimiento,
    MantenimientoService,
)
from app.modules.mantenimientos.domain.entities import Mantenimiento
from app.modules.mantenimientos.domain.ports import FiltrosMantenimiento
from app.modules.mantenimientos.infrastructure.repositories import MantenimientoRepositorySQLAlchemy
from app.modules.mantenimientos.presentation.schemas import (
    ArchivoConfirmado,
    CancelarMantenimientoRequest,
    CerrarMantenimientoRequest,
    EvidenciaOut,
    InactividadOut,
    MantenimientoOut,
    MantenimientoRequest,
    PaginaMantenimientosOut,
    UrlArchivoOut,
    UrlArchivoRequest,
    UrlDescargaOut,
)

router = APIRouter(prefix="/api/v1", tags=["mantenimientos"])

_almacenamiento = AlmacenamientoMinIO(get_settings().minio_bucket_evidencias)


def _service(db: Session) -> MantenimientoService:
    return MantenimientoService(
        MantenimientoRepositorySQLAlchemy(db),
        EquipoRepositorySQLAlchemy(db),
        AdjuntoRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
        _almacenamiento,
        AlertaService(AlertaRepositorySQLAlchemy(db), NotificacionRepositorySQLAlchemy(db)),
        ConfiguracionRepositorySQLAlchemy(db),
    )


def _actor(request: Request, usuario: UsuarioContexto) -> ActorContexto:
    return ActorContexto(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )


def _a_datos(datos: MantenimientoRequest) -> DatosMantenimiento:
    return DatosMantenimiento(
        equipo_id=datos.equipo_id,
        tipo=datos.tipo,
        fecha_programada=datos.fecha_programada,
        tecnico_responsable_id=datos.tecnico_responsable_id,
        descripcion=datos.descripcion,
        frecuencia_meses=datos.frecuencia_meses,
    )


def _a_out(mantenimiento: Mantenimiento) -> MantenimientoOut:
    return MantenimientoOut(
        id=mantenimiento.id,
        equipo_id=mantenimiento.equipo_id,
        tipo=mantenimiento.tipo,
        estado=mantenimiento.estado,
        fecha_programada=mantenimiento.fecha_programada,
        fecha_ejecutada=mantenimiento.fecha_ejecutada,
        tecnico_responsable_id=mantenimiento.tecnico_responsable_id,
        descripcion=mantenimiento.descripcion,
        repuestos_utilizados=mantenimiento.repuestos_utilizados,
        tiempo_inactividad_horas=mantenimiento.tiempo_inactividad_horas,
        costo=mantenimiento.costo,
        tiene_informe=mantenimiento.informe_adjunto_id is not None,
        frecuencia_meses=mantenimiento.frecuencia_meses,
        generado_de_id=mantenimiento.generado_de_id,
        creado_en=mantenimiento.creado_en,
        actualizado_en=mantenimiento.actualizado_en,
    )


def _evidencia_a_out(adjunto) -> EvidenciaOut:  # type: ignore[no-untyped-def]
    return EvidenciaOut(
        id=adjunto.id, nombre_archivo=adjunto.nombre_archivo, tamano_bytes=adjunto.tamano_bytes,
        tipo_mime=adjunto.tipo_mime, creado_en=adjunto.creado_en,
    )


@router.post("/mantenimientos/upload-url/evidencia", response_model=UrlArchivoOut)
def solicitar_url_evidencia(
    datos: UrlArchivoRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("mantenimientos.crear")),
) -> UrlArchivoOut:
    url, object_key = _service(db).solicitar_url_evidencia(
        datos.nombre_archivo, datos.tipo_mime, datos.tamano_bytes
    )
    return UrlArchivoOut(url_subida=url, object_key=object_key)


@router.post("/mantenimientos/upload-url/informe", response_model=UrlArchivoOut)
def solicitar_url_informe(
    datos: UrlArchivoRequest,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("mantenimientos.crear")),
) -> UrlArchivoOut:
    url, object_key = _service(db).solicitar_url_informe(
        datos.nombre_archivo, datos.tipo_mime, datos.tamano_bytes
    )
    return UrlArchivoOut(url_subida=url, object_key=object_key)


@router.get("/mantenimientos/hoy", response_model=list[MantenimientoOut])
def mis_mantenimientos_de_hoy(
    db: Session = Depends(get_db), usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer"))
) -> list[MantenimientoOut]:
    """HU-TEC-01."""
    return [_a_out(m) for m in _service(db).mis_mantenimientos_de_hoy(usuario.id)]


@router.get("/mantenimientos/inactividad", response_model=InactividadOut)
def inactividad_por_equipo(
    equipo_id: uuid.UUID = Query(...),
    desde: date = Query(...),
    hasta: date = Query(...),
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> InactividadOut:
    """RF-MANT-04."""
    horas = _service(db).inactividad_por_equipo(equipo_id, desde, hasta)
    return InactividadOut(equipo_id=equipo_id, desde=desde, hasta=hasta, horas=horas)


@router.get("/mantenimientos/evidencias/{adjunto_id}/url", response_model=UrlDescargaOut)
def obtener_url_evidencia(
    adjunto_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> UrlDescargaOut:
    return UrlDescargaOut(url=_service(db).url_evidencia(adjunto_id))


@router.post("/mantenimientos", response_model=MantenimientoOut, status_code=201)
def crear_mantenimiento(
    datos: MantenimientoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("mantenimientos.crear")),
) -> MantenimientoOut:
    mantenimiento = _service(db).crear(usuario.laboratorio_id, _actor(request, usuario), _a_datos(datos))
    db.commit()
    return _a_out(mantenimiento)


@router.get("/mantenimientos", response_model=PaginaMantenimientosOut)
def listar_mantenimientos(
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
    equipo_id: uuid.UUID | None = Query(default=None),
    tecnico_responsable_id: uuid.UUID | None = Query(default=None),
    estado: str | None = Query(default=None),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    # RNF-PERF-03 — el listado general del laboratorio (sin `equipo_id`)
    # pagina de verdad; una ficha de equipo individual sigue pidiendo todo
    # su propio historial en una sola página (tamano_pagina por defecto,
    # 200, generoso a propósito — ver FiltrosMantenimiento).
    pagina: int = Query(default=1, ge=1),
    tamano_pagina: int | None = Query(default=None, ge=1, le=200),
) -> PaginaMantenimientosOut:
    filtros = FiltrosMantenimiento(
        equipo_id=equipo_id,
        tecnico_responsable_id=tecnico_responsable_id,
        estado=estado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        pagina=pagina,
        # El listado general (sin equipo_id) usa el tamaño de página real de
        # 20 (RNF-PERF-03); una ficha de equipo individual sigue pidiendo
        # todo su historial en una sola página (mismo default generoso que
        # FiltrosMantenimiento ya trae, 200).
        tamano_pagina=tamano_pagina if tamano_pagina is not None else (20 if equipo_id is None else 200),
    )
    resultado = _service(db).listar(usuario.laboratorio_id, filtros)
    return PaginaMantenimientosOut(
        items=[_a_out(m) for m in resultado.items],
        total=resultado.total,
        pagina=resultado.pagina,
        tamano_pagina=resultado.tamano_pagina,
    )


@router.get("/mantenimientos/{mantenimiento_id}", response_model=MantenimientoOut)
def obtener_mantenimiento(
    mantenimiento_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> MantenimientoOut:
    return _a_out(_service(db).obtener(mantenimiento_id))


@router.post("/mantenimientos/{mantenimiento_id}/iniciar", response_model=MantenimientoOut)
def iniciar_mantenimiento(
    mantenimiento_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("mantenimientos.crear")),
) -> MantenimientoOut:
    mantenimiento = _service(db).iniciar(mantenimiento_id, _actor(request, usuario))
    db.commit()
    return _a_out(mantenimiento)


@router.post("/mantenimientos/{mantenimiento_id}/cerrar", response_model=MantenimientoOut)
def cerrar_mantenimiento(
    mantenimiento_id: uuid.UUID,
    datos: CerrarMantenimientoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("mantenimientos.crear")),
) -> MantenimientoOut:
    mantenimiento = _service(db).cerrar(
        mantenimiento_id,
        _actor(request, usuario),
        DatosCierre(
            fecha_ejecutada=datos.fecha_ejecutada,
            repuestos_utilizados=datos.repuestos_utilizados,
            tiempo_inactividad_horas=datos.tiempo_inactividad_horas,
            costo=datos.costo,
            descripcion=datos.descripcion,
        ),
    )
    db.commit()
    return _a_out(mantenimiento)


@router.post("/mantenimientos/{mantenimiento_id}/cancelar", response_model=MantenimientoOut)
def cancelar_mantenimiento(
    mantenimiento_id: uuid.UUID,
    datos: CancelarMantenimientoRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("mantenimientos.crear")),
) -> MantenimientoOut:
    mantenimiento = _service(db).cancelar(mantenimiento_id, _actor(request, usuario), datos.motivo)
    db.commit()
    return _a_out(mantenimiento)


@router.post("/mantenimientos/{mantenimiento_id}/evidencias", response_model=EvidenciaOut, status_code=201)
def agregar_evidencia(
    mantenimiento_id: uuid.UUID,
    datos: ArchivoConfirmado,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("mantenimientos.crear")),
) -> EvidenciaOut:
    adjunto = _service(db).agregar_evidencia(
        mantenimiento_id,
        _actor(request, usuario),
        datos.object_key,
        datos.nombre_archivo,
        datos.tamano_bytes,
        datos.tipo_mime,
    )
    db.commit()
    return _evidencia_a_out(adjunto)


@router.get("/mantenimientos/{mantenimiento_id}/evidencias", response_model=list[EvidenciaOut])
def listar_evidencias(
    mantenimiento_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> list[EvidenciaOut]:
    return [_evidencia_a_out(a) for a in _service(db).listar_evidencias(mantenimiento_id)]


@router.post("/mantenimientos/{mantenimiento_id}/informe", response_model=MantenimientoOut)
def asignar_informe(
    mantenimiento_id: uuid.UUID,
    datos: ArchivoConfirmado,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("mantenimientos.crear")),
) -> MantenimientoOut:
    mantenimiento = _service(db).asignar_informe(
        mantenimiento_id,
        _actor(request, usuario),
        datos.object_key,
        datos.nombre_archivo,
        datos.tamano_bytes,
        datos.tipo_mime,
    )
    db.commit()
    return _a_out(mantenimiento)


@router.get("/mantenimientos/{mantenimiento_id}/informe-url", response_model=UrlDescargaOut)
def obtener_url_informe(
    mantenimiento_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> UrlDescargaOut:
    return UrlDescargaOut(url=_service(db).url_informe(mantenimiento_id))
