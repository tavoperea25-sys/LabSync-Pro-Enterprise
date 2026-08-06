"""Puerto de Auditoría — implementado por AuditoriaRepositorySQLAlchemy,
consumido por cualquier módulo que necesite dejar rastro (RN-AUD-02)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from app.modules.auditoria.domain.entities import LogAuditoria


@dataclass
class FiltrosAuditoria:
    usuario_id: uuid.UUID | None = None
    modulo: str | None = None
    accion: str | None = None
    desde: datetime | None = None
    hasta: datetime | None = None


@dataclass
class PaginaAuditoria:
    """Fase 2/M3 — ver PaginaEquipos (equipos/domain/ports.py) para el mismo
    patrón, ya usado en el proyecto."""

    items: list[LogAuditoria] = field(default_factory=list)
    total: int = 0
    pagina: int = 1
    tamano_pagina: int = 20


class AuditoriaRepository(Protocol):
    def registrar(
        self,
        laboratorio_id: uuid.UUID,
        usuario_id: uuid.UUID | None,
        ip_origen: str | None,
        modulo: str,
        accion: str,
        entidad_tipo: str,
        entidad_id: uuid.UUID | None,
        valor_anterior: dict[str, Any] | None = None,
        valor_nuevo: dict[str, Any] | None = None,
    ) -> None: ...

    def listar_por_entidad(self, entidad_tipo: str, entidad_id: uuid.UUID) -> list[LogAuditoria]: ...

    def buscar_texto(self, consulta: str, limite: int) -> list[LogAuditoria]:
        """RF-SEARCH-02 — vía el índice GIN `ix_logs_auditoria_busqueda` (0008)."""
        ...

    def listar_filtrado(self, filtros: FiltrosAuditoria, limite: int) -> list[LogAuditoria]:
        """Sin paginar, con un tope fijo — usado solo por `/export` (RF-AUD-03),
        que necesita todas las filas hasta `limite`, no una página."""
        ...

    def listar_filtrado_paginado(
        self, filtros: FiltrosAuditoria, pagina: int, tamano_pagina: int
    ) -> PaginaAuditoria:
        """RF-AUD-02 — pantalla de auditoría avanzada. Fase 2/M3: reemplaza
        el límite fijo de 2000 filas sin paginar que tenía el endpoint de
        listado (el de `/export` sigue usando `listar_filtrado` tal cual)."""
        ...

    def listar_modulos_distintos(self) -> list[str]:
        """Valores reales presentes en la bitácora — para poblar el filtro
        sin mantener a mano una lista que se desactualiza."""
        ...

    def listar_acciones_distintas(self) -> list[str]: ...
