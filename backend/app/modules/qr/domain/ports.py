"""Puertos del módulo QR."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.qr.domain.entities import IncidenciaQr, IncidenciaQrConEquipo, QrToken


class QrTokenRepository(Protocol):
    def crear(self, laboratorio_id: uuid.UUID, equipo_id: uuid.UUID, token: str) -> QrToken: ...

    def obtener_por_token(self, token: str) -> QrToken | None: ...

    def obtener_por_equipo(self, equipo_id: uuid.UUID) -> QrToken | None: ...


class IncidenciaQrRepository(Protocol):
    def crear(
        self,
        laboratorio_id: uuid.UUID,
        equipo_id: uuid.UUID,
        descripcion: str,
        contacto_nombre: str | None,
        contacto_medio: str | None,
    ) -> IncidenciaQr: ...

    def listar_con_equipo(self, laboratorio_id: uuid.UUID) -> list[IncidenciaQrConEquipo]: ...

    def obtener_por_id(self, incidencia_id: uuid.UUID) -> IncidenciaQr | None: ...

    def actualizar_estado(self, incidencia_id: uuid.UUID, nuevo_estado: str) -> IncidenciaQr: ...
