"""Entidades del módulo Reportes. Ver docs/03-requerimientos-funcionales.md
(RF-REP-01 a 08 — Sprint 11)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

TIPOS_REPORTE = (
    "inventario",
    "calibraciones",
    "vencidos",
    "cumplimiento",
    "mantenimiento",
    "trazabilidad_documental",
    "paquete_auditoria",
)

FORMATOS_REPORTE = ("pdf", "xlsx", "csv")
ESTADOS_REPORTE = ("pendiente", "procesando", "listo", "fallido")

# El paquete de auditoría (RF-REP-07) es intrínsecamente multi-sección
# (ficha + calibraciones + mantenimientos + documentos vigentes) — RF-REP-07
# permite "PDF/ZIP"; se eligió un único PDF con secciones (más simple de
# abrir y compartir que un ZIP) en vez de empaquetar varios archivos.
FORMATOS_POR_TIPO: dict[str, tuple[str, ...]] = {
    "inventario": ("pdf", "xlsx", "csv"),
    "calibraciones": ("pdf", "xlsx", "csv"),
    "vencidos": ("pdf", "xlsx", "csv"),
    "cumplimiento": ("pdf", "xlsx", "csv"),
    "mantenimiento": ("pdf", "xlsx", "csv"),
    "trazabilidad_documental": ("pdf", "xlsx", "csv"),
    "paquete_auditoria": ("pdf",),
}

# RNF-PERF-04 — por encima de este umbral de registros, el reporte se
# encola como job async en vez de generarse en la misma petición HTTP.
UMBRAL_ASINCRONO = 1000

TIPOS_MIME_POR_FORMATO = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
}


@dataclass
class ReporteGenerado:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    tipo: str
    formato: str
    filtros: dict[str, Any] | None
    estado: str
    object_key: str | None
    nombre_archivo: str | None
    error: str | None
    solicitado_por_id: uuid.UUID | None
    creado_en: datetime
    completado_en: datetime | None

    def esta_listo(self) -> bool:
        return self.estado == "listo"
