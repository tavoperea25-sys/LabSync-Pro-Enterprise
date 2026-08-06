"""Puertos del módulo Mantenimientos — ver docs/13-arquitectura.md sección 2."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Protocol

from app.modules.mantenimientos.domain.entities import Mantenimiento


@dataclass
class FiltrosMantenimiento:
    equipo_id: uuid.UUID | None = None
    tecnico_responsable_id: uuid.UUID | None = None
    estado: str | None = None
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    # RNF-PERF-03 — "listas con más de 50 elementos deben usar paginación o
    # virtualización". El valor por defecto (200) es generoso a propósito:
    # cubre sin romper el uso existente de listar-por-equipo (una sola
    # ficha rara vez supera unas pocas decenas de registros); el listado
    # general del laboratorio sí pagina de verdad, con tamano_pagina=20
    # explícito desde el router (ver `MantenimientosListPage`).
    pagina: int = 1
    tamano_pagina: int = 200


@dataclass
class PaginaMantenimientos:
    items: list[Mantenimiento] = field(default_factory=list)
    total: int = 0
    pagina: int = 1
    tamano_pagina: int = 200


class MantenimientoRepository(Protocol):
    def crear(self, mantenimiento: Mantenimiento) -> Mantenimiento: ...

    def obtener_por_id(self, mantenimiento_id: uuid.UUID) -> Mantenimiento | None: ...

    def listar(self, laboratorio_id: uuid.UUID, filtros: FiltrosMantenimiento) -> PaginaMantenimientos: ...

    def listar_todos(self, laboratorio_id: uuid.UUID, filtros: FiltrosMantenimiento) -> list[Mantenimiento]:
        """Como `listar`, pero sin paginar — para KPIs del Dashboard,
        reportes (RF-REP-05), exportación de datos del tenant (Sprint 13) y
        generación de eventos de Calendario: todos necesitan el conjunto
        completo, nunca solo la primera página (mismo criterio que
        `EquipoRepository.listar_todos`, RF-EQ-08)."""
        ...

    def contar_abiertos_por_equipo(self, equipo_id: uuid.UUID, excluir_id: uuid.UUID | None = None) -> int:
        """RN-MANT-01 — para decidir si el equipo puede volver a "operativo"
        al cerrar/cancelar uno de varios mantenimientos concurrentes."""
        ...

    def contar_abiertos_por_tipo(self) -> dict[str, int]:
        """Fase 2/M4 (docs/22-planificacion-fase2.md) — para el KPI
        `mantenimientos_correctivos_abiertos` del Dashboard, que antes traía
        TODOS los mantenimientos abiertos (dos `listar_todos()` sin límite,
        uno por estado) a Python solo para sumarlos por tipo. Mismos estados
        que `Mantenimiento.esta_abierto()` (ESTADOS_OPERATIVOS_ABIERTOS)."""
        ...

    def actualizar(self, mantenimiento: Mantenimiento) -> Mantenimiento: ...

    def sumar_inactividad(self, equipo_id: uuid.UUID, desde: date, hasta: date) -> Decimal:
        """RF-MANT-04/RN-MANT-03."""
        ...

    def listar_proximos_por_tecnico(self, tecnico_id: uuid.UUID, dia: date) -> list[Mantenimiento]:
        """HU-TEC-01 — mantenimientos programados de un técnico para un día."""
        ...

    def listar_proximos(self, laboratorio_id: uuid.UUID, dias_umbral: int) -> list[Mantenimiento]:
        """RF-ALT-02 — mantenimientos "programado" cuya fecha_programada
        vence dentro de `dias_umbral` días (incluye ya vencidos)."""
        ...

    def buscar_texto(self, consulta: str, limite: int) -> list[Mantenimiento]:
        """RF-SEARCH-02 — vía el índice GIN `ix_mantenimientos_busqueda` (0008)."""
        ...
