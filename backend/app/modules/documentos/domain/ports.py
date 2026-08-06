"""Puertos del módulo Documentos — ver docs/13-arquitectura.md sección 2."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from app.modules.documentos.domain.entities import Carpeta, Documento, Etiqueta, VersionDocumento


@dataclass
class FiltrosDocumento:
    carpeta_id: uuid.UUID | None = None
    categoria: str | None = None
    etiqueta_id: uuid.UUID | None = None
    q: str | None = None
    solo_favoritos_de: uuid.UUID | None = None
    incluir_eliminados: bool = False
    pagina: int = 1
    tamano_pagina: int = 20


@dataclass
class PaginaDocumentos:
    items: list[Documento] = field(default_factory=list)
    total: int = 0
    pagina: int = 1
    tamano_pagina: int = 20


class CarpetaRepository(Protocol):
    def crear(self, carpeta: Carpeta) -> Carpeta: ...

    def obtener_por_id(self, carpeta_id: uuid.UUID) -> Carpeta | None: ...

    def listar(self, laboratorio_id: uuid.UUID, carpeta_padre_id: uuid.UUID | None) -> list[Carpeta]: ...

    def existe_nombre(
        self, laboratorio_id: uuid.UUID, carpeta_padre_id: uuid.UUID | None, nombre: str,
        excluir_id: uuid.UUID | None = None,
    ) -> bool: ...

    def tiene_contenido(self, carpeta_id: uuid.UUID) -> bool:
        """True si tiene subcarpetas o documentos (activos) — RN de borrado seguro."""
        ...

    def actualizar(self, carpeta: Carpeta) -> Carpeta: ...

    def eliminar(self, carpeta_id: uuid.UUID) -> None: ...


class EtiquetaRepository(Protocol):
    def listar(self, laboratorio_id: uuid.UUID) -> list[Etiqueta]: ...

    def obtener_o_crear(self, laboratorio_id: uuid.UUID, nombre: str) -> Etiqueta: ...

    def asignar(self, documento_id: uuid.UUID, etiqueta_id: uuid.UUID) -> None: ...

    def quitar(self, documento_id: uuid.UUID, etiqueta_id: uuid.UUID) -> None: ...

    def listar_por_documento(self, documento_id: uuid.UUID) -> list[Etiqueta]: ...


class VersionDocumentoRepository(Protocol):
    def crear(self, version: VersionDocumento) -> VersionDocumento: ...

    def listar_por_documento(self, documento_id: uuid.UUID) -> list[VersionDocumento]: ...

    def obtener(self, documento_id: uuid.UUID, numero_version: int) -> VersionDocumento | None: ...

    def siguiente_numero_version(self, documento_id: uuid.UUID) -> int: ...

    def obtener_por_id(self, version_id: uuid.UUID) -> VersionDocumento | None: ...

    def marcar_aprobada(self, version_id: uuid.UUID, usuario_id: uuid.UUID | None) -> VersionDocumento:
        """RF-DOC-14 — registra quién aprobó esta versión y cuándo."""
        ...


class DocumentoRepository(Protocol):
    def crear(self, documento: Documento) -> Documento: ...

    def obtener_por_id(self, documento_id: uuid.UUID) -> Documento | None: ...

    def listar(self, laboratorio_id: uuid.UUID, filtros: FiltrosDocumento) -> PaginaDocumentos: ...

    def listar_todos(self, laboratorio_id: uuid.UUID) -> list[Documento]:
        """Sin filtro de carpeta ni paginar — para exportación (portabilidad
        de datos del tenant, Sprint 13)."""
        ...

    def listar_recientes(self, laboratorio_id: uuid.UUID, limite: int) -> list[Documento]: ...

    def listar_vigencia_critica(self, laboratorio_id: uuid.UUID, dias_umbral: int) -> list[Documento]:
        """RF-ALT-01/02 — documentos activos con fecha_vencimiento definida
        que ya vencieron o vencen dentro de `dias_umbral` días."""
        ...

    def contar_por_estado_efectivo(self, hoy: date) -> dict[str, int]:
        """Fase 2/M4 (docs/22-planificacion-fase2.md) — para los KPIs
        `documentos_en_revision` y `cumplimiento_documental_pct` del
        Dashboard, que antes traían hasta 5000 documentos (`listar_todos`) a
        Python solo para clasificarlos con `Documento.estado_efectivo(hoy)`.
        Réplica exacta de esa regla (RN-DOC-01: vencimiento tiene precedencia
        sobre el estado manual) expresada en SQL — si esa regla cambia, este
        método debe actualizarse junto con ella."""
        ...

    def listar_por_vencimiento_rango(
        self, laboratorio_id: uuid.UUID, desde: date, hasta: date
    ) -> list[Documento]:
        """RF-CAL2-01 — documentos activos cuya fecha_vencimiento cae dentro
        de un rango arbitrario (vista de calendario, no umbral de alerta)."""
        ...

    def listar_papelera(self, laboratorio_id: uuid.UUID) -> list[Documento]: ...

    def listar_vigentes(self, laboratorio_id: uuid.UUID) -> list[Documento]:
        """RF-REP-06/07 — trazabilidad documental y paquete de auditoría."""
        ...

    def buscar_texto(self, consulta: str, limite: int) -> list[Documento]:
        """RF-SEARCH-02 — vía el índice GIN `ix_documentos_busqueda` (0005)."""
        ...

    def actualizar(self, documento: Documento) -> Documento: ...

    def eliminar(self, documento_id: uuid.UUID) -> None:
        """Soft delete — RN-DOC-03."""
        ...

    def restaurar(self, documento_id: uuid.UUID) -> None: ...

    def listar_papelera_expirada(self, laboratorio_id: uuid.UUID, dias_retencion: int) -> list[Documento]:
        """RN-DOC-03 — documentos en papelera cuyo `eliminado_en` ya superó
        la ventana de retención configurada; candidatos a purga física."""
        ...

    def purgar(self, documento_id: uuid.UUID) -> list[str]:
        """RN-DOC-03 — elimina físicamente el documento y todas sus
        versiones (nunca se hace desde `eliminar()`, que es soft delete).
        Retorna los `object_key` de las versiones borradas para que el
        llamador limpie también el binario en MinIO — este puerto no conoce
        el almacenamiento, solo la base de datos."""
        ...

    def es_favorito(self, documento_id: uuid.UUID, usuario_id: uuid.UUID) -> bool: ...

    def alternar_favorito(self, documento_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
        """Retorna el nuevo estado (True = ahora es favorito)."""
        ...


class AlmacenamientoPort(Protocol):
    """Adaptador sobre el object storage (MinIO). El backend nunca transporta
    el binario del archivo — solo firma URLs (docs/13-arquitectura.md sección 5)."""

    def url_subida(self, object_key: str, tipo_mime: str) -> str: ...

    def url_descarga(self, object_key: str, nombre_descarga: str, tipo_mime: str | None = None) -> str: ...

    def url_vista_previa(self, object_key: str, tipo_mime: str | None = None) -> str:
        """Como `url_descarga` pero con disposición `inline` — para
        embeber PDF/imagen directamente en el visor (RF-DOC-07)."""
        ...

    def copiar_objeto(self, origen_key: str, destino_key: str) -> None:
        """Copia server-side dentro del bucket — usada por RF-DOC-09 (copiar
        documento) para no re-subir bytes que el backend nunca vio."""
        ...

    def eliminar_objeto(self, object_key: str) -> None:
        """RN-DOC-03 — borrado físico del binario al purgar la papelera
        vencida. Único caso de eliminación real de un objeto en el proyecto."""
        ...
