"""Puertos del módulo Reportes — ver docs/13-arquitectura.md sección 2."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.reportes.domain.entities import ReporteGenerado


class ReporteRepository(Protocol):
    def crear(self, reporte: ReporteGenerado) -> ReporteGenerado: ...

    def obtener_por_id(self, reporte_id: uuid.UUID) -> ReporteGenerado | None: ...

    def listar(self, laboratorio_id: uuid.UUID, limite: int) -> list[ReporteGenerado]:
        """Historial — RF-REP (`/reportes/historial`)."""
        ...

    def actualizar(self, reporte: ReporteGenerado) -> ReporteGenerado: ...

    def listar_pendientes(self, limite: int) -> list[ReporteGenerado]:
        """Outbox del worker (RNF-PERF-04) — mismo patrón que
        `NotificacionRepository.listar_pendientes` (Sprint 8): el worker
        fija el contexto de tenant por laboratorio antes de llamar esto,
        nunca hace una consulta cross-tenant directa."""
        ...
