"""Puertos del módulo Alertas."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Protocol

from app.modules.alertas.domain.entities import Alerta, NotificacionPendiente


@dataclass
class FiltrosAlerta:
    estado: str | None = None
    tipo: str | None = None
    # RNF-PERF-03 — mismo criterio que FiltrosMantenimiento (Sprint 27):
    # `listar()` nunca traía todo el laboratorio sin límite. El default de
    # 20 sirve tanto a `AlertasPage` (paginación real) como a
    # `NotificacionesBell` (que pide un tamano_pagina más chico, 8).
    pagina: int = 1
    tamano_pagina: int = 20


@dataclass
class PaginaAlertas:
    items: list[Alerta] = field(default_factory=list)
    total: int = 0
    pagina: int = 1
    tamano_pagina: int = 20


class AlertaRepository(Protocol):
    def crear(self, alerta: Alerta) -> Alerta: ...

    def obtener_por_id(self, alerta_id: uuid.UUID) -> Alerta | None: ...

    def existe_activa(self, origen_tipo: str, origen_id: uuid.UUID, tipo: str) -> bool:
        """RN-ALT-01 — verificación a nivel de aplicación; el índice único
        parcial en la migración es la garantía real contra condiciones de
        carrera, esto solo evita una excepción de integridad innecesaria
        en el camino feliz."""
        ...

    def listar(self, laboratorio_id: uuid.UUID, filtros: FiltrosAlerta) -> PaginaAlertas: ...

    def contar_activas(self, laboratorio_id: uuid.UUID) -> int: ...

    def actualizar(self, alerta: Alerta) -> Alerta: ...

    def resolver_por_origen(
        self, origen_tipo: str, origen_id: uuid.UUID, resuelta_por_id: uuid.UUID | None
    ) -> int:
        """RN-ALT-02 — resolución automática como efecto secundario de una
        acción humana (ej. registrar la calibración pendiente). Retorna
        cuántas alertas activas se resolvieron."""
        ...


class NotificacionRepository(Protocol):
    def encolar(self, notificacion: NotificacionPendiente) -> NotificacionPendiente: ...

    def listar_pendientes(self, limite: int) -> list[NotificacionPendiente]: ...

    def marcar_enviada(self, notificacion_id: uuid.UUID) -> None: ...

    def marcar_fallida(self, notificacion_id: uuid.UUID) -> None: ...
