"""Implementación SQLAlchemy del repositorio de Configuración."""

from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.modules.configuracion.domain.entities import ConfiguracionLaboratorio as ConfiguracionDominio
from app.modules.configuracion.infrastructure.models import ConfiguracionLaboratorio


def _a_dominio(fila: ConfiguracionLaboratorio) -> ConfiguracionDominio:
    return ConfiguracionDominio(
        laboratorio_id=fila.laboratorio_id,
        umbral_alerta_calibracion_dias=fila.umbral_alerta_calibracion_dias,
        umbral_alerta_mantenimiento_dias=fila.umbral_alerta_mantenimiento_dias,
        umbral_alerta_documento_dias=fila.umbral_alerta_documento_dias,
        dias_retencion_papelera_documentos=fila.dias_retencion_papelera_documentos,
        politica_password=fila.politica_password_json,
        mapeo_estados_mantenimiento=fila.mapeo_estados_mantenimiento_json,
    )


class ConfiguracionRepositorySQLAlchemy:
    def __init__(self, db: Session) -> None:
        self._db = db

    def obtener(self, laboratorio_id: uuid.UUID) -> ConfiguracionDominio | None:
        fila = self._db.get(ConfiguracionLaboratorio, laboratorio_id)
        return _a_dominio(fila) if fila else None

    def guardar(self, config: ConfiguracionDominio) -> ConfiguracionDominio:
        # Upsert: la primera vez que un laboratorio configura algo no existe
        # fila todavía (creada perezosamente, ver docstring de la migración
        # 0010) — INSERT ... ON CONFLICT evita un round-trip extra para
        # decidir si es un alta o una edición.
        valores = {
            "umbral_alerta_calibracion_dias": config.umbral_alerta_calibracion_dias,
            "umbral_alerta_mantenimiento_dias": config.umbral_alerta_mantenimiento_dias,
            "umbral_alerta_documento_dias": config.umbral_alerta_documento_dias,
            "dias_retencion_papelera_documentos": config.dias_retencion_papelera_documentos,
            "politica_password_json": config.politica_password,
            "mapeo_estados_mantenimiento_json": config.mapeo_estados_mantenimiento,
        }
        stmt = insert(ConfiguracionLaboratorio).values(laboratorio_id=config.laboratorio_id, **valores)
        stmt = stmt.on_conflict_do_update(index_elements=["laboratorio_id"], set_=valores)
        self._db.execute(stmt)
        self._db.flush()
        return self.obtener(config.laboratorio_id)  # type: ignore[return-value]
