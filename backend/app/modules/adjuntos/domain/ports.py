"""Puerto del módulo Adjuntos."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.adjuntos.domain.entities import Adjunto


class AdjuntoRepository(Protocol):
    def crear(self, adjunto: Adjunto) -> Adjunto: ...

    def obtener_por_id(self, adjunto_id: uuid.UUID) -> Adjunto | None: ...

    def listar_por_entidad(self, entidad_tipo: str, entidad_id: uuid.UUID) -> list[Adjunto]: ...
