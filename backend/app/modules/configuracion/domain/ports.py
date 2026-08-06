"""Puertos del módulo Configuración."""

from __future__ import annotations

import uuid
from typing import Protocol

from app.modules.configuracion.domain.entities import ConfiguracionLaboratorio


class ConfiguracionRepository(Protocol):
    def obtener(self, laboratorio_id: uuid.UUID) -> ConfiguracionLaboratorio | None:
        """None si el laboratorio nunca guardó configuración propia — el
        llamador decide si aplicar los valores por defecto."""
        ...

    def guardar(self, config: ConfiguracionLaboratorio) -> ConfiguracionLaboratorio:
        """Upsert — crea la fila la primera vez, actualiza después."""
        ...
