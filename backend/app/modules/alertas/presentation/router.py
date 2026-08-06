"""Endpoints de Alertas. Ver docs/15-api-design.md.

`POST /alertas/evaluar` es el disparador manual del barrido (RF-ALT-01/02) —
existe para administración/pruebas y como red de seguridad si el worker
(Sprint 8, tarea 63) no está corriendo; en producción el barrido periódico
lo hace el worker, no un usuario golpeando este endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.ip import ip_valida
from app.modules.alertas.application.alerta_service import ActorContexto, AlertaService
from app.modules.alertas.application.evaluador_service import EvaluadorAlertasService
from app.modules.alertas.domain.entities import Alerta
from app.modules.alertas.domain.ports import FiltrosAlerta
from app.modules.alertas.infrastructure.repositories import (
    AlertaRepositorySQLAlchemy,
    NotificacionRepositorySQLAlchemy,
)
from app.modules.alertas.presentation.schemas import (
    AlertaOut,
    ContadorActivasOut,
    EvaluarOut,
    PaginaAlertasOut,
)
from app.modules.auth.presentation.dependencies import UsuarioContexto, requiere_permiso
from app.modules.calibraciones.infrastructure.repositories import CalibracionRepositorySQLAlchemy
from app.modules.configuracion.infrastructure.repositories import ConfiguracionRepositorySQLAlchemy
from app.modules.documentos.infrastructure.repositories import DocumentoRepositorySQLAlchemy
from app.modules.mantenimientos.infrastructure.repositories import MantenimientoRepositorySQLAlchemy

router = APIRouter(prefix="/api/v1", tags=["alertas"])


def _service(db: Session) -> AlertaService:
    return AlertaService(AlertaRepositorySQLAlchemy(db), NotificacionRepositorySQLAlchemy(db))


def _evaluador(db: Session) -> EvaluadorAlertasService:
    return EvaluadorAlertasService(
        _service(db),
        CalibracionRepositorySQLAlchemy(db),
        DocumentoRepositorySQLAlchemy(db),
        MantenimientoRepositorySQLAlchemy(db),
        ConfiguracionRepositorySQLAlchemy(db),
    )


def _actor(request: Request, usuario: UsuarioContexto) -> ActorContexto:
    return ActorContexto(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )


def _a_out(alerta: Alerta) -> AlertaOut:
    return AlertaOut(
        id=alerta.id,
        tipo=alerta.tipo,
        origen_tipo=alerta.origen_tipo,
        origen_id=alerta.origen_id,
        mensaje=alerta.mensaje,
        estado=alerta.estado,
        leida_en=alerta.leida_en,
        resuelta_por_id=alerta.resuelta_por_id,
        resuelta_en=alerta.resuelta_en,
        creado_en=alerta.creado_en,
    )


@router.get("/alertas/contar-activas", response_model=ContadorActivasOut)
def contar_activas(
    db: Session = Depends(get_db), usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer"))
) -> ContadorActivasOut:
    """RF-ALT-04 — badge de la campana en el Navbar."""
    return ContadorActivasOut(activas=_service(db).contar_activas(usuario.laboratorio_id))


@router.get("/alertas", response_model=PaginaAlertasOut)
def listar_alertas(
    estado: str | None = Query(default=None),
    tipo: str | None = Query(default=None),
    # RNF-PERF-03 — `AlertasPage` pagina de verdad (20 por página, el
    # default); `NotificacionesBell` pide un tamano_pagina más chico (8) en
    # vez de traer todo y recortar del lado del cliente.
    pagina: int = Query(default=1, ge=1),
    tamano_pagina: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> PaginaAlertasOut:
    resultado = _service(db).listar(
        usuario.laboratorio_id,
        FiltrosAlerta(estado=estado, tipo=tipo, pagina=pagina, tamano_pagina=tamano_pagina),
    )
    return PaginaAlertasOut(
        items=[_a_out(a) for a in resultado.items],
        total=resultado.total,
        pagina=resultado.pagina,
        tamano_pagina=resultado.tamano_pagina,
    )


@router.post("/alertas/evaluar", response_model=EvaluarOut)
def evaluar_alertas(
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("alertas.gestionar")),
) -> EvaluarOut:
    generadas = _evaluador(db).evaluar_laboratorio(usuario.laboratorio_id)
    db.commit()
    return EvaluarOut(generadas=generadas)


@router.post("/alertas/{alerta_id}/leer", response_model=AlertaOut)
def marcar_leida(
    alerta_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> AlertaOut:
    alerta = _service(db).marcar_leida(alerta_id)
    db.commit()
    return _a_out(alerta)


@router.post("/alertas/{alerta_id}/resolver", response_model=AlertaOut)
def resolver_manual(
    alerta_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("alertas.gestionar")),
) -> AlertaOut:
    alerta = _service(db).resolver_manual(alerta_id, _actor(request, usuario))
    db.commit()
    return _a_out(alerta)
