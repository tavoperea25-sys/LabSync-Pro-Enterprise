"""Entidades del módulo Documentos. Ver docs/14-base-de-datos.md y
docs/03-requerimientos-funcionales.md (RF-DOC-01 a RF-DOC-14 — Sprints 5-6)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

ESTADOS_DOCUMENTO = ("vigente", "obsoleto", "en_revision")

# RF-DOC-02. Mapea extensión -> tipos MIME aceptados para esa extensión; se
# valida tanto al pedir la URL de subida como al confirmar el documento.
FORMATOS_PERMITIDOS: dict[str, tuple[str, ...]] = {
    "pdf": ("application/pdf",),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document",),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",),
    "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation",),
    "csv": ("text/csv", "application/vnd.ms-excel"),
    "txt": ("text/plain",),
    "jpg": ("image/jpeg",),
    "jpeg": ("image/jpeg",),
    "png": ("image/png",),
    "webp": ("image/webp",),
}

# Formatos con previsualización nativa en el visor del frontend (RF-DOC-07);
# el resto muestra solo metadatos — no hay conversor a v1.
FORMATOS_CON_PREVISUALIZACION = frozenset({"pdf", "jpg", "jpeg", "png", "webp"})

TAMANO_MAXIMO_BYTES = 50 * 1024 * 1024  # 50 MB — límite de producto para v1, no técnico.


@dataclass
class Carpeta:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    nombre: str
    carpeta_padre_id: uuid.UUID | None
    creado_en: datetime


@dataclass
class Etiqueta:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    nombre: str


@dataclass
class VersionDocumento:
    id: uuid.UUID
    documento_id: uuid.UUID
    numero_version: int
    object_key: str
    nombre_archivo: str
    tamano_bytes: int
    tipo_mime: str
    subido_por_id: uuid.UUID | None
    aprobado_por_id: uuid.UUID | None
    aprobado_en: datetime | None
    creado_en: datetime


@dataclass
class Documento:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    carpeta_id: uuid.UUID | None
    nombre: str
    categoria: str | None
    estado: str
    fecha_emision: date | None
    fecha_vencimiento: date | None
    responsable_aprobacion_id: uuid.UUID | None
    version_vigente_id: uuid.UUID | None
    eliminado_en: datetime | None
    creado_en: datetime
    actualizado_en: datetime

    def esta_activo(self) -> bool:
        return self.eliminado_en is None

    def estado_efectivo(self, hoy: date) -> str:
        """RF-DOC-13 / RN-DOC-01: la fecha de vencimiento tiene precedencia
        sobre cualquier marca manual — un documento vencido nunca puede
        mostrarse como "vigente", ni siquiera si alguien fuerza `estado`
        manualmente. "vencido" es un estado derivado, no se persiste."""
        if self.fecha_vencimiento is not None and self.fecha_vencimiento < hoy:
            return "vencido"
        return self.estado
