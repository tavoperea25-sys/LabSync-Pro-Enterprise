"""Worker de barrido periódico — RF-ALT-01/02 (outbox de notificaciones) y
RF-REP/RNF-PERF-04 (reportes asíncronos grandes).

Proceso Docker Compose separado (ver docker-compose.yml, servicio `worker`),
NO comparte memoria con la API. Cada ciclo, por laboratorio: (1) evalúa
vencimientos generando alertas nuevas vía `EvaluadorAlertasService`,
(2) drena el outbox `notificaciones_pendientes` haciendo `pg_notify` por
cada una, (3) genera los reportes 'pendiente' en `reportes_generados`
(RNF-PERF-04: >1000 registros no se generan en la petición HTTP que los
solicita), y (4) purga físicamente los documentos de la papelera que ya
superaron su ventana de retención (RN-DOC-03) — la única eliminación
irreversible de todo el proyecto, deliberadamente aislada a este barrido
programado en vez de disparada por acción de usuario. La API
(`app/core/ws_gateway.py`) está LISTEN-ando el mismo canal
`canal_alertas` y reenvía a los WebSocket conectados del laboratorio
correspondiente — un reporte listo se notifica con un `pg_notify` directo
(no pasa por `notificaciones_pendientes`, cuyo `alerta_id` es NOT NULL y no
aplica aquí) justo después de confirmarse 'listo' en la misma transacción,
así que la garantía del outbox ("nunca notificar algo que no ocurrió
realmente") se cumple igual sin reutilizar esa tabla.

Se conecta como `labsync_app` (RLS activo, igual que la API) — nunca como
el rol superusuario de migraciones. El barrido en sí es inherentemente
cross-tenant (recorre TODOS los laboratorios), así que se itera
`laboratorios` (la única tabla sin RLS, ver alembic/versions/0001) y se fija
`set_tenant_context` antes de cada bloque de queries por-tenant — el mismo
patrón que ya usan los fixtures de pruebas."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import replace
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.database import SessionLocal, set_tenant_context
from app.core.logging import configurar_logging, fijar_trace_id
from app.core.ws_gateway import CANAL_ALERTAS
from app.modules.alertas.application.alerta_service import AlertaService
from app.modules.alertas.application.evaluador_service import EvaluadorAlertasService
from app.modules.alertas.infrastructure.repositories import (
    AlertaRepositorySQLAlchemy,
    NotificacionRepositorySQLAlchemy,
)
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.infrastructure.models import Laboratorio
from app.modules.auth.infrastructure.repositories import LaboratorioRepositorySQLAlchemy
from app.modules.calibraciones.infrastructure.repositories import CalibracionRepositorySQLAlchemy
from app.modules.configuracion.infrastructure.repositories import ConfiguracionRepositorySQLAlchemy
from app.modules.documentos.application.documento_service import DocumentoService
from app.modules.documentos.infrastructure.repositories import (
    CarpetaRepositorySQLAlchemy,
    DocumentoRepositorySQLAlchemy,
    EtiquetaRepositorySQLAlchemy,
    VersionDocumentoRepositorySQLAlchemy,
)
from app.modules.equipos.infrastructure.repositories import (
    AreaRepositorySQLAlchemy,
    CategoriaEquipoRepositorySQLAlchemy,
    EquipoRepositorySQLAlchemy,
)
from app.modules.mantenimientos.infrastructure.repositories import MantenimientoRepositorySQLAlchemy
from app.modules.reportes.application.generadores import RepositoriosReporte, generar_datos_por_tipo
from app.modules.reportes.application.reporte_service import (
    exportar_bytes,
    nombre_archivo_de,
    object_key_de,
    obtener_logo_bytes,
)
from app.modules.reportes.domain.entities import TIPOS_MIME_POR_FORMATO
from app.modules.reportes.infrastructure.repositories import ReporteRepositorySQLAlchemy

INTERVALO_SEGUNDOS = 300  # 5 minutos entre barridos completos — RF-ALT no exige tiempo real en la detección
LIMITE_NOTIFICACIONES_POR_TICK = 100
LIMITE_REPORTES_POR_TICK = 5  # PDFs/Excel grandes son costosos — no acaparar un ciclo entero

# El worker no expone un puerto HTTP (a diferencia de la API, que tiene
# `/health`) — docker-compose.yml verifica que este archivo se actualizó
# recientemente en vez de sondear un endpoint que no existe (Sprint 15,
# gate de docs/19-checklist.md "Health check expuesto para todo servicio").
ARCHIVO_HEARTBEAT = "/tmp/worker_heartbeat"

configurar_logging()
_logger = logging.getLogger("worker")

_almacenamiento_reportes = AlmacenamientoMinIO(get_settings().minio_bucket_reportes)
_almacenamiento_logos = AlmacenamientoMinIO(get_settings().minio_bucket_logos)
_almacenamiento_documentos = AlmacenamientoMinIO(get_settings().minio_bucket_documentos)


def _actualizar_heartbeat() -> None:
    with open(ARCHIVO_HEARTBEAT, "w") as archivo:
        archivo.write(str(time.time()))


def _repos_reporte(db: Session) -> RepositoriosReporte:
    categorias = {c.id: c.nombre for c in CategoriaEquipoRepositorySQLAlchemy(db).listar()}
    areas = {a.id: a.nombre for a in AreaRepositorySQLAlchemy(db).listar()}
    return RepositoriosReporte(
        equipos=EquipoRepositorySQLAlchemy(db),
        categorias_por_id=categorias,
        areas_por_id=areas,
        calibraciones=CalibracionRepositorySQLAlchemy(db),
        mantenimientos=MantenimientoRepositorySQLAlchemy(db),
        documentos=DocumentoRepositorySQLAlchemy(db),
    )


def _procesar_reportes_pendientes(db: Session, laboratorio_id: uuid.UUID) -> None:
    reportes_repo = ReporteRepositorySQLAlchemy(db)
    pendientes = reportes_repo.listar_pendientes(LIMITE_REPORTES_POR_TICK)
    for reporte in pendientes:
        # `SET LOCAL` muere con cada `COMMIT`/`ROLLBACK` — el reporte anterior
        # del mismo lote ya hizo al menos uno (éxito o fallo), así que hay que
        # refijar el tenant antes de tocar la base para ESTE reporte. Sin
        # esto, un reporte perfectamente válido podía terminar marcado
        # 'fallido' con un AssertionError genérico solo por su posición en
        # el lote — bug real encontrado y corregido en Fase 1/I12
        # (2026-08-04), mismo patrón que ya se había corregido para el
        # bucle de notificaciones en Fase 0/C1.
        set_tenant_context(db, laboratorio_id)
        try:
            datos = generar_datos_por_tipo(
                reporte.tipo, laboratorio_id, reporte.filtros or {}, _repos_reporte(db)
            )
            ahora = datetime.utcnow()
            logo_bytes = obtener_logo_bytes(
                LaboratorioRepositorySQLAlchemy(db), _almacenamiento_logos, laboratorio_id
            )
            contenido = exportar_bytes(reporte.tipo, reporte.formato, datos, ahora, logo_bytes)
            object_key = object_key_de(laboratorio_id, reporte.id, reporte.formato)
            nombre_archivo = nombre_archivo_de(reporte.tipo, reporte.formato, ahora)
            _almacenamiento_reportes.subir_bytes(
                object_key, contenido, TIPOS_MIME_POR_FORMATO[reporte.formato]
            )
            actualizado = reportes_repo.actualizar(
                replace(
                    reporte,
                    estado="listo",
                    object_key=object_key,
                    nombre_archivo=nombre_archivo,
                    completado_en=ahora,
                )
            )
            db.commit()
            payload = json.dumps(
                {
                    "laboratorio_id": str(laboratorio_id),
                    "evento": "reporte.listo",
                    "reporte_id": str(actualizado.id),
                    "tipo": actualizado.tipo,
                    "mensaje": f"Tu reporte de {actualizado.tipo} ya está listo para descargar.",
                }
            )
            db.execute(
                text("SELECT pg_notify(:canal, :payload)"), {"canal": CANAL_ALERTAS, "payload": payload}
            )
            db.commit()
            _logger.info("laboratorio=%s reporte=%s listo", laboratorio_id, reporte.id)
        except Exception as exc:
            db.rollback()
            set_tenant_context(db, laboratorio_id)
            reportes_repo.actualizar(replace(reporte, estado="fallido", error=str(exc)[:500]))
            db.commit()
            _logger.exception("laboratorio=%s reporte=%s falló", laboratorio_id, reporte.id)


def _documento_service(db: Session) -> DocumentoService:
    return DocumentoService(
        DocumentoRepositorySQLAlchemy(db),
        VersionDocumentoRepositorySQLAlchemy(db),
        CarpetaRepositorySQLAlchemy(db),
        EtiquetaRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
        _almacenamiento_documentos,
        ConfiguracionRepositorySQLAlchemy(db),
    )


def _purgar_papelera_documentos(db: Session, laboratorio_id: uuid.UUID) -> None:
    """RN-DOC-03 — purga física de documentos que superaron la ventana de
    retención de la papelera. Irreversible a propósito (ver docstring de
    `DocumentoService.purgar_papelera_vencida`)."""
    purgados = _documento_service(db).purgar_papelera_vencida(laboratorio_id)
    db.commit()
    if purgados:
        _logger.info("laboratorio=%s documentos_purgados=%d", laboratorio_id, purgados)


def _procesar_laboratorio(laboratorio_id: uuid.UUID) -> None:
    # Un trace_id por laboratorio-por-ciclo: todo lo que este barrido loguea
    # para este tenant queda correlacionado en un solo trace_id, igual que
    # el trace_id por-petición de la API (app/core/logging.py).
    fijar_trace_id(f"worker-{uuid.uuid4()}")
    db = SessionLocal()
    try:
        set_tenant_context(db, laboratorio_id)

        evaluador = EvaluadorAlertasService(
            AlertaService(AlertaRepositorySQLAlchemy(db), NotificacionRepositorySQLAlchemy(db)),
            CalibracionRepositorySQLAlchemy(db),
            DocumentoRepositorySQLAlchemy(db),
            MantenimientoRepositorySQLAlchemy(db),
            ConfiguracionRepositorySQLAlchemy(db),
        )
        generadas = evaluador.evaluar_laboratorio(laboratorio_id)
        db.commit()
        if generadas:
            _logger.info("laboratorio=%s alertas_nuevas=%d", laboratorio_id, generadas)

        # `SET LOCAL` muere con el COMMIT anterior — sin fijarlo de nuevo,
        # esta consulta corre sin contexto de tenant y RLS la deja en 0 filas.
        set_tenant_context(db, laboratorio_id)
        notif_repo = NotificacionRepositorySQLAlchemy(db)
        notificaciones = notif_repo.listar_pendientes(LIMITE_NOTIFICACIONES_POR_TICK)
        enviadas = 0
        for notificacion in notificaciones:
            # Commit por notificación (no por lote): si `pg_notify` o
            # `marcar_enviada` fallan para una, la excepción deja la
            # transacción abortada y un rollback aquí solo revierte ESTA
            # notificación — las ya comprometidas en iteraciones previas
            # quedan a salvo. Antes, un solo ítem tóxico (p. ej. un payload
            # que excede el límite de 8000 bytes de NOTIFY) revertía el lote
            # completo y volvía a quedar primero en el siguiente ciclo,
            # bloqueando la cola del tenant indefinidamente.
            set_tenant_context(db, laboratorio_id)
            try:
                payload = json.dumps({"laboratorio_id": str(laboratorio_id), **notificacion.payload})
                db.execute(
                    text("SELECT pg_notify(:canal, :payload)"), {"canal": CANAL_ALERTAS, "payload": payload}
                )
                notif_repo.marcar_enviada(notificacion.id)
                db.commit()
                enviadas += 1
            except Exception:
                db.rollback()
                set_tenant_context(db, laboratorio_id)
                notif_repo.marcar_fallida(notificacion.id)
                db.commit()
                _logger.exception(
                    "laboratorio=%s notificacion=%s falló al enviarse, marcada como fallida.",
                    laboratorio_id,
                    notificacion.id,
                )
        if enviadas:
            _logger.info("laboratorio=%s notificaciones_enviadas=%d", laboratorio_id, enviadas)

        set_tenant_context(db, laboratorio_id)
        _procesar_reportes_pendientes(db, laboratorio_id)

        set_tenant_context(db, laboratorio_id)
        _purgar_papelera_documentos(db, laboratorio_id)
    except Exception:
        db.rollback()
        _logger.exception(
            "Fallo procesando laboratorio=%s, se reintenta en el próximo ciclo.", laboratorio_id
        )
    finally:
        db.close()


def ejecutar_ciclo() -> None:
    db = SessionLocal()
    try:
        ids = list(db.execute(select(Laboratorio.id)).scalars())
    finally:
        db.close()

    for laboratorio_id in ids:
        _procesar_laboratorio(laboratorio_id)


def main() -> None:
    _logger.info("Worker de alertas iniciado (intervalo=%ds).", INTERVALO_SEGUNDOS)
    _actualizar_heartbeat()
    # Espera breve de arranque: docker-compose ya condiciona este servicio a
    # que `backend` esté "healthy" (su `/health` solo responde tras aplicar
    # migraciones en el entrypoint, ver docker-compose.yml) — este sleep es
    # ahora una segunda red de seguridad, no la única, por si el esquema
    # tarda en propagarse por cualquier otro motivo.
    time.sleep(10)
    while True:
        try:
            ejecutar_ciclo()
        except Exception:
            _logger.exception("Fallo el ciclo de barrido completo, se reintenta.")
        _actualizar_heartbeat()
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    main()
