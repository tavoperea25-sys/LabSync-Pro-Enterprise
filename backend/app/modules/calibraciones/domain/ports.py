"""Puertos del módulo Calibraciones — ver docs/13-arquitectura.md sección 2."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Protocol

from app.modules.calibraciones.domain.entities import Calibracion, EquipoConSemaforo


class CalibracionRepository(Protocol):
    def crear(self, calibracion: Calibracion) -> Calibracion: ...

    def obtener_por_id(self, calibracion_id: uuid.UUID) -> Calibracion | None: ...

    def listar_todas(self, laboratorio_id: uuid.UUID) -> list[Calibracion]:
        """Sin agrupar por equipo — para exportación (portabilidad de datos
        del tenant, Sprint 13)."""
        ...

    def listar_por_equipo(self, equipo_id: uuid.UUID) -> list[Calibracion]:
        """Orden descendente por fecha_calibracion — historial para la
        tendencia (RF-CAL-04) y el listado en la ficha del equipo."""
        ...

    def listar_criticos(self, laboratorio_id: uuid.UUID) -> list[EquipoConSemaforo]:
        """RF-CAL-05 — un renglón por equipo activo con su última
        calibración (o ninguna, semáforo "gris")."""
        ...

    def listar_estado_todos(self, laboratorio_id: uuid.UUID) -> list[EquipoConSemaforo]:
        """RF-REP-02 — como `listar_criticos` pero sin excluir "verde"."""
        ...

    def listar_estado_a_fecha(
        self, laboratorio_id: uuid.UUID, fecha_corte: date
    ) -> list[EquipoConSemaforo]:
        """RF-REP-04 — el estado de cumplimiento tal como era en una fecha
        pasada, para el histórico mensual."""
        ...

    def listar_proximas(self, laboratorio_id: uuid.UUID, desde: date, hasta: date) -> list[EquipoConSemaforo]:
        """RF-CAL2-01 — próximas calibraciones (última por equipo) cuya
        `proxima_fecha` cae en un rango arbitrario (vista de calendario,
        a diferencia de `listar_criticos` que solo mira urgencia actual)."""
        ...

    def buscar_texto(self, consulta: str, limite: int) -> list[Calibracion]:
        """RF-SEARCH-02 ("certificados") — vía el índice GIN
        `ix_calibraciones_busqueda` (0008)."""
        ...
