"""Caso de uso central del módulo Reportes — RF-REP-01 a 08, RNF-PERF-04.

`generar` es el único punto de entrada: decide síncrono vs. asíncrono según
el volumen de datos (RNF-PERF-04, umbral en domain/entities.py) y en ambos
casos dejar un registro en `reportes_generados` (RF-REP, historial) — la
única diferencia es que en el camino síncrono los bytes ya vienen listos
para responder en la misma petición, y en el asíncrono el worker los
produce después (ver app/worker/main.py)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.errors import ErrorDeDominio
from app.modules.auditoria.domain.ports import AuditoriaRepository
from app.modules.auth.domain.ports import LaboratorioRepository
from app.modules.reportes.application.generadores import (
    PaqueteAuditoria,
    RepositoriosReporte,
    generar_datos_por_tipo,
)
from app.modules.reportes.domain.entities import (
    FORMATOS_POR_TIPO,
    TIPOS_MIME_POR_FORMATO,
    TIPOS_REPORTE,
    UMBRAL_ASINCRONO,
    ReporteGenerado,
)
from app.modules.reportes.domain.ports import ReporteRepository
from app.modules.reportes.infrastructure.exportadores import (
    exportar_reporte_tabular,
    generar_paquete_auditoria_pdf,
)

_MODULO = "reportes"
_logger = logging.getLogger(__name__)


@dataclass
class ActorContexto:
    usuario_id: uuid.UUID | None
    ip_origen: str | None


class TipoDeReporteInvalido(ErrorDeDominio):
    def __init__(self, tipo: str) -> None:
        super().__init__(
            "tipo_reporte_invalido",
            f"'{tipo}' no es un tipo de reporte válido.",
            {"tipos_validos": list(TIPOS_REPORTE)},
        )


class FormatoNoDisponibleParaTipo(ErrorDeDominio):
    def __init__(self, tipo: str, formato: str) -> None:
        super().__init__(
            "formato_no_disponible",
            f"El reporte '{tipo}' no está disponible en formato '{formato}'.",
            {"formatos_disponibles": list(FORMATOS_POR_TIPO.get(tipo, ()))},
        )


def object_key_de(laboratorio_id: uuid.UUID, reporte_id: uuid.UUID, formato: str) -> str:
    return f"{laboratorio_id}/{reporte_id}.{formato}"


def nombre_archivo_de(tipo: str, formato: str, generado_en: datetime) -> str:
    marca = generado_en.strftime("%Y%m%d_%H%M%S")
    return f"{tipo}_{marca}.{formato}"


def _validar(tipo: str, formato: str) -> None:
    if tipo not in TIPOS_REPORTE:
        raise TipoDeReporteInvalido(tipo)
    if formato not in FORMATOS_POR_TIPO[tipo]:
        raise FormatoNoDisponibleParaTipo(tipo, formato)


def exportar_bytes(
    tipo: str,
    formato: str,
    datos: list[Any] | PaqueteAuditoria,
    generado_en: datetime,
    logo_bytes: bytes | None = None,
) -> bytes:
    """Compartido entre el flujo síncrono y el worker — ver docstring del
    módulo. `paquete_auditoria` tiene su propio renderizador multi-sección
    (no es una tabla plana como los otros 6 tipos). `logo_bytes` es RF-CFG-04
    — ninguno de los dos formatos que no son PDF lo usa."""
    if isinstance(datos, PaqueteAuditoria):
        return generar_paquete_auditoria_pdf(datos, logo_bytes)
    return exportar_reporte_tabular(tipo, formato, datos, generado_en, logo_bytes)


def obtener_logo_bytes(
    laboratorios: LaboratorioRepository, almacenamiento_logos: Any, laboratorio_id: uuid.UUID
) -> bytes | None:
    """Resuelve "¿este laboratorio tiene logo institucional configurado, y
    si sí, cuáles son sus bytes?" — compartido entre el flujo síncrono y el
    worker, igual que `exportar_bytes`. Cualquier fallo (objeto borrado del
    bucket, MinIO caído) degrada a "sin logo" en vez de tumbar el reporte
    completo: el logo es un adorno del encabezado, no un dato del reporte."""
    laboratorio = laboratorios.obtener_por_id(laboratorio_id)
    if laboratorio is None or laboratorio.logo_object_key is None:
        return None
    try:
        return almacenamiento_logos.descargar_bytes(laboratorio.logo_object_key)
    except Exception:
        _logger.warning("No se pudo descargar el logo institucional para el reporte.", exc_info=True)
        return None


class ReporteService:
    def __init__(
        self,
        reportes: ReporteRepository,
        repos: RepositoriosReporte,
        almacenamiento: Any,
        auditoria: AuditoriaRepository,
        laboratorios: LaboratorioRepository,
        almacenamiento_logos: Any,
    ) -> None:
        self._reportes = reportes
        self._repos = repos
        self._almacenamiento = almacenamiento
        self._auditoria = auditoria
        self._laboratorios = laboratorios
        self._almacenamiento_logos = almacenamiento_logos

    def generar(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        tipo: str,
        formato: str,
        filtros: dict[str, Any],
    ) -> tuple[ReporteGenerado, bytes | None]:
        _validar(tipo, formato)
        datos = generar_datos_por_tipo(tipo, laboratorio_id, filtros, self._repos)
        cantidad = 1 if isinstance(datos, PaqueteAuditoria) else len(datos)
        ahora = datetime.utcnow()

        if cantidad > UMBRAL_ASINCRONO:
            reporte = self._reportes.crear(
                ReporteGenerado(
                    id=uuid.uuid4(),
                    laboratorio_id=laboratorio_id,
                    tipo=tipo,
                    formato=formato,
                    filtros=filtros,
                    estado="pendiente",
                    object_key=None,
                    nombre_archivo=None,
                    error=None,
                    solicitado_por_id=actor.usuario_id,
                    creado_en=ahora,
                    completado_en=None,
                )
            )
            self._auditar(reporte, actor, "solicitar_async")
            return reporte, None

        logo_bytes = obtener_logo_bytes(self._laboratorios, self._almacenamiento_logos, laboratorio_id)
        contenido = exportar_bytes(tipo, formato, datos, ahora, logo_bytes)
        reporte_id = uuid.uuid4()
        object_key = object_key_de(laboratorio_id, reporte_id, formato)
        nombre_archivo = nombre_archivo_de(tipo, formato, ahora)
        self._almacenamiento.subir_bytes(object_key, contenido, TIPOS_MIME_POR_FORMATO[formato])

        reporte = self._reportes.crear(
            ReporteGenerado(
                id=reporte_id,
                laboratorio_id=laboratorio_id,
                tipo=tipo,
                formato=formato,
                filtros=filtros,
                estado="listo",
                object_key=object_key,
                nombre_archivo=nombre_archivo,
                error=None,
                solicitado_por_id=actor.usuario_id,
                creado_en=ahora,
                completado_en=ahora,
            )
        )
        self._auditar(reporte, actor, "generar")
        return reporte, contenido

    def listar_historial(self, laboratorio_id: uuid.UUID, limite: int = 100) -> list[ReporteGenerado]:
        return self._reportes.listar(laboratorio_id, limite)

    def _auditar(self, reporte: ReporteGenerado, actor: ActorContexto, accion: str) -> None:
        self._auditoria.registrar(
            laboratorio_id=reporte.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion=accion,
            entidad_tipo="reporte",
            entidad_id=reporte.id,
            valor_anterior=None,
            valor_nuevo={"tipo": reporte.tipo, "formato": reporte.formato},
        )
