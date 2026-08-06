"""Entidades de Configuración — RF-CFG-03/04/05 (Sprint 12)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

UMBRAL_ALERTA_CALIBRACION_DIAS_DEFAULT = 30
UMBRAL_ALERTA_MANTENIMIENTO_DIAS_DEFAULT = 15
UMBRAL_ALERTA_DOCUMENTO_DIAS_DEFAULT = 30
# RN-DOC-03 — ventana de restauración de la papelera de documentos.
DIAS_RETENCION_PAPELERA_DOCUMENTOS_DEFAULT = 30


@dataclass
class ConfiguracionLaboratorio:
    laboratorio_id: uuid.UUID
    umbral_alerta_calibracion_dias: int
    umbral_alerta_mantenimiento_dias: int
    umbral_alerta_documento_dias: int
    dias_retencion_papelera_documentos: int
    politica_password: dict[str, Any] | None
    mapeo_estados_mantenimiento: dict[str, str] | None

    @staticmethod
    def por_defecto(laboratorio_id: uuid.UUID) -> ConfiguracionLaboratorio:
        """RF-CFG-03, RN implícita (docs/05-casos-de-uso.md 3a): mientras el
        Administrador no configure nada, el sistema opera con estos valores
        — los mismos que estaban hardcodeados antes de este sprint."""
        return ConfiguracionLaboratorio(
            laboratorio_id=laboratorio_id,
            umbral_alerta_calibracion_dias=UMBRAL_ALERTA_CALIBRACION_DIAS_DEFAULT,
            umbral_alerta_mantenimiento_dias=UMBRAL_ALERTA_MANTENIMIENTO_DIAS_DEFAULT,
            umbral_alerta_documento_dias=UMBRAL_ALERTA_DOCUMENTO_DIAS_DEFAULT,
            dias_retencion_papelera_documentos=DIAS_RETENCION_PAPELERA_DOCUMENTOS_DEFAULT,
            politica_password=None,
            mapeo_estados_mantenimiento=None,
        )
