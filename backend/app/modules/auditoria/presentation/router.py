"""Endpoints de Auditoría avanzada — RF-AUD-02/03 (Sprint 10).
Ver docs/15-api-design.md."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ErrorDeDominio
from app.core.pagination import TAMANO_PAGINA_MAXIMO, TAMANO_PAGINA_POR_DEFECTO
from app.modules.auditoria.domain.entities import LogAuditoria
from app.modules.auditoria.domain.ports import FiltrosAuditoria
from app.modules.auditoria.infrastructure.exportador import generar_csv, generar_excel, generar_pdf
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auditoria.presentation.schemas import (
    LogAuditoriaOut,
    PaginaAuditoriaOut,
    ValoresFiltroOut,
)
from app.modules.auth.presentation.dependencies import UsuarioContexto, requiere_permiso

router = APIRouter(prefix="/api/v1/auditoria", tags=["auditoria"])

_LIMITE = 2000
_FORMATOS = {
    "csv": ("text/csv", generar_csv),
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        generar_excel,
    ),
}


def _a_out(log: LogAuditoria) -> LogAuditoriaOut:
    return LogAuditoriaOut(
        id=log.id,
        usuario_id=log.usuario_id,
        ip_origen=log.ip_origen,
        modulo=log.modulo,
        accion=log.accion,
        entidad_tipo=log.entidad_tipo,
        entidad_id=log.entidad_id,
        valor_anterior=log.valor_anterior,
        valor_nuevo=log.valor_nuevo,
        creado_en=log.creado_en,
    )


def _filtros(
    usuario_id: uuid.UUID | None,
    modulo: str | None,
    accion: str | None,
    desde: datetime | None,
    hasta: datetime | None,
) -> FiltrosAuditoria:
    return FiltrosAuditoria(
        usuario_id=usuario_id, modulo=modulo, accion=accion, desde=desde, hasta=hasta
    )


@router.get("/valores-filtro", response_model=ValoresFiltroOut)
def valores_filtro(
    db: Session = Depends(get_db), _usuario: UsuarioContexto = Depends(requiere_permiso("auditoria.ver"))
) -> ValoresFiltroOut:
    repo = AuditoriaRepositorySQLAlchemy(db)
    return ValoresFiltroOut(
        modulos=repo.listar_modulos_distintos(), acciones=repo.listar_acciones_distintas()
    )


@router.get("", response_model=PaginaAuditoriaOut)
def listar_auditoria(
    usuario_id: uuid.UUID | None = Query(default=None),
    modulo: str | None = Query(default=None),
    accion: str | None = Query(default=None),
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    tamano_pagina: int = Query(default=TAMANO_PAGINA_POR_DEFECTO, ge=1, le=TAMANO_PAGINA_MAXIMO),
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("auditoria.ver")),
) -> PaginaAuditoriaOut:
    resultado = AuditoriaRepositorySQLAlchemy(db).listar_filtrado_paginado(
        _filtros(usuario_id, modulo, accion, desde, hasta), pagina, tamano_pagina
    )
    return PaginaAuditoriaOut(
        items=[_a_out(log) for log in resultado.items],
        total=resultado.total,
        pagina=resultado.pagina,
        tamano_pagina=resultado.tamano_pagina,
    )


@router.get("/export")
def exportar_auditoria(
    formato: str = Query(default="csv"),
    usuario_id: uuid.UUID | None = Query(default=None),
    modulo: str | None = Query(default=None),
    accion: str | None = Query(default=None),
    desde: datetime | None = Query(default=None),
    hasta: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("auditoria.ver")),
) -> StreamingResponse:
    logs = AuditoriaRepositorySQLAlchemy(db).listar_filtrado(
        _filtros(usuario_id, modulo, accion, desde, hasta), _LIMITE
    )

    if formato == "pdf":
        contenido = generar_pdf(logs, datetime.utcnow())
        media_type = "application/pdf"
    elif formato in _FORMATOS:
        media_type, generador = _FORMATOS[formato]
        contenido = generador(logs)
    else:
        raise ErrorDeDominio(
            "formato_no_soportado",
            f"'{formato}' no es un formato de exportación soportado.",
            {"formatos_disponibles": ["csv", "xlsx", "pdf"]},
        )

    extension = formato
    nombre_archivo = f"auditoria_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{extension}"
    return StreamingResponse(
        iter([contenido]),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )
