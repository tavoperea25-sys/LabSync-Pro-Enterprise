"""Puertos del módulo Equipos — ver docs/13-arquitectura.md sección 2."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Protocol

from app.modules.equipos.domain.entities import Equipo


@dataclass
class FiltrosEquipo:
    q: str | None = None
    categoria_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    estado_operativo: str | None = None
    incluir_eliminados: bool = False
    pagina: int = 1
    tamano_pagina: int = 20


@dataclass
class PaginaEquipos:
    items: list[Equipo] = field(default_factory=list)
    total: int = 0
    pagina: int = 1
    tamano_pagina: int = 20


class EquipoRepository(Protocol):
    def crear(self, equipo: Equipo) -> Equipo: ...

    def obtener_por_id(self, equipo_id: uuid.UUID) -> Equipo | None: ...

    def existe_codigo(self, codigo_interno: str, excluir_id: uuid.UUID | None = None) -> bool: ...

    def listar(self, filtros: FiltrosEquipo) -> PaginaEquipos: ...

    def listar_todos(self, filtros: FiltrosEquipo) -> list[Equipo]:
        """Como `listar`, pero sin paginar — para exportación (RF-EQ-08)."""
        ...

    def buscar_texto(self, consulta: str, limite: int) -> list[Equipo]:
        """RF-SEARCH-02 — vía el índice GIN `ix_equipos_busqueda` (0002)."""
        ...

    def contar_por_estado(self) -> dict[str, int]:
        """KPIs del Dashboard (docs/03-requerimientos-funcionales.md Módulo 2)."""
        ...

    def existe_con_categoria(self, categoria_id: uuid.UUID) -> bool:
        """RF-CFG-05 — bloquea eliminar una categoría todavía en uso."""
        ...

    def existe_con_area(self, area_id: uuid.UUID) -> bool:
        """RF-CFG-05 — bloquea eliminar un área todavía en uso."""
        ...

    def actualizar(self, equipo: Equipo) -> Equipo: ...

    def tiene_calibracion_vencida_bloqueante(self, equipo_id: uuid.UUID) -> bool:
        """RN-EQ-03 — True si la categoría del equipo tiene el bloqueo de
        activación configurado y su última calibración está vencida."""
        ...

    def eliminar(self, equipo_id: uuid.UUID) -> None:
        """Soft delete — RN-EQ-01. Nunca hay eliminación física expuesta."""
        ...
