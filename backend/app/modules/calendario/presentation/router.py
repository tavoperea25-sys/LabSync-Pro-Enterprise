"""Endpoints de Calendario. Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.ip import ip_valida
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.presentation.dependencies import UsuarioContexto, requiere_permiso
from app.modules.calendario.application.calendario_service import (
    ActorContexto,
    CalendarioService,
    DatosEventoCalendario,
    FiltrosCalendario,
)
from app.modules.calendario.domain.entities import TIPOS_EVENTO_MANUAL, EventoCalendario
from app.modules.calendario.infrastructure.repositories import EventoCalendarioRepositorySQLAlchemy
from app.modules.calendario.presentation.schemas import EventoCalendarioOut, EventoCalendarioRequest
from app.modules.calibraciones.infrastructure.repositories import CalibracionRepositorySQLAlchemy
from app.modules.documentos.infrastructure.repositories import DocumentoRepositorySQLAlchemy
from app.modules.equipos.infrastructure.repositories import EquipoRepositorySQLAlchemy
from app.modules.mantenimientos.infrastructure.repositories import MantenimientoRepositorySQLAlchemy

router = APIRouter(prefix="/api/v1", tags=["calendario"])


def _service(db: Session) -> CalendarioService:
    return CalendarioService(
        EventoCalendarioRepositorySQLAlchemy(db),
        CalibracionRepositorySQLAlchemy(db),
        MantenimientoRepositorySQLAlchemy(db),
        DocumentoRepositorySQLAlchemy(db),
        EquipoRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
    )


def _actor(request: Request, usuario: UsuarioContexto) -> ActorContexto:
    return ActorContexto(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )


def _a_datos(datos: EventoCalendarioRequest) -> DatosEventoCalendario:
    return DatosEventoCalendario(
        tipo=datos.tipo, titulo=datos.titulo, fecha=datos.fecha, descripcion=datos.descripcion
    )


def _a_out(evento: EventoCalendario) -> EventoCalendarioOut:
    return EventoCalendarioOut(
        id=evento.id,
        tipo=evento.tipo,
        titulo=evento.titulo,
        descripcion=evento.descripcion,
        fecha=evento.fecha,
        origen_tipo=evento.origen_tipo,
        origen_id=evento.origen_id,
        editable=evento.es_manual(),
    )


@router.get("/calendario/eventos", response_model=list[EventoCalendarioOut])
def listar_eventos(
    desde: datetime = Query(...),
    hasta: datetime = Query(...),
    tipo: str | None = Query(default=None),
    area_id: uuid.UUID | None = Query(default=None),
    responsable_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> list[EventoCalendarioOut]:
    eventos = _service(db).listar(
        usuario.laboratorio_id,
        FiltrosCalendario(
            desde=desde, hasta=hasta, tipo=tipo, area_id=area_id, responsable_id=responsable_id
        ),
    )
    return [_a_out(e) for e in eventos]


@router.post("/calendario/eventos", response_model=EventoCalendarioOut, status_code=201)
def crear_evento(
    datos: EventoCalendarioRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("calendario.gestionar")),
) -> EventoCalendarioOut:
    evento = _service(db).crear(usuario.laboratorio_id, _actor(request, usuario), _a_datos(datos))
    db.commit()
    return _a_out(evento)


@router.patch("/calendario/eventos/{evento_id}", response_model=EventoCalendarioOut)
def actualizar_evento(
    evento_id: uuid.UUID,
    datos: EventoCalendarioRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("calendario.gestionar")),
) -> EventoCalendarioOut:
    evento = _service(db).actualizar(evento_id, _actor(request, usuario), _a_datos(datos))
    db.commit()
    return _a_out(evento)


@router.delete("/calendario/eventos/{evento_id}", status_code=204, response_model=None)
def eliminar_evento(
    evento_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("calendario.gestionar")),
) -> None:
    _service(db).eliminar(evento_id, _actor(request, usuario))
    db.commit()


@router.get("/calendario/tipos-evento", response_model=list[str])
def tipos_evento_manual(
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> list[str]:
    return list(TIPOS_EVENTO_MANUAL)
