"""Barrido periódico de vencimientos — RF-ALT-01/02. Este es el único
punto que el worker invoca (una vez por laboratorio, ver Sprint 8 nota de
arquitectura): recorre Calibraciones, Documentos y Mantenimientos buscando
condiciones ya vencidas (crítica) o próximas a vencer (preventiva, dentro
del umbral configurado) y delega en `AlertaService.generar_si_no_existe`
para que RN-ALT-01 (no duplicar) se aplique de forma uniforme.

La alerta de "equipo pasa a fuera de servicio" (RF-ALT-01) NO vive aquí —
es un evento discreto, no una condición para barrer repetidamente, así que
se dispara síncronamente desde el router de Mantenimientos en el momento
de la transición (ver `mantenimientos/presentation/router.py::iniciar_mantenimiento`)."""

from __future__ import annotations

import uuid
from datetime import date

from app.modules.alertas.application.alerta_service import AlertaService
from app.modules.calibraciones.domain.ports import CalibracionRepository
from app.modules.configuracion.domain.entities import ConfiguracionLaboratorio
from app.modules.configuracion.domain.ports import ConfiguracionRepository
from app.modules.documentos.domain.ports import DocumentoRepository
from app.modules.mantenimientos.domain.ports import MantenimientoRepository


class EvaluadorAlertasService:
    def __init__(
        self,
        alertas: AlertaService,
        calibraciones: CalibracionRepository,
        documentos: DocumentoRepository,
        mantenimientos: MantenimientoRepository,
        configuraciones: ConfiguracionRepository,
    ) -> None:
        self._alertas = alertas
        self._calibraciones = calibraciones
        self._documentos = documentos
        self._mantenimientos = mantenimientos
        self._configuraciones = configuraciones

    def evaluar_laboratorio(self, laboratorio_id: uuid.UUID) -> int:
        """Retorna cuántas alertas NUEVAS se generaron (ya deduplicadas)."""
        config = self._configuraciones.obtener(laboratorio_id) or ConfiguracionLaboratorio.por_defecto(
            laboratorio_id
        )
        generadas = 0
        # `_evaluar_calibraciones` no recibe el umbral explícitamente: ya lo
        # resuelve `CalibracionRepository.listar_criticos()` internamente
        # (RF-CFG-03, ver calibraciones/infrastructure/repositories.py).
        generadas += self._evaluar_calibraciones(laboratorio_id)
        generadas += self._evaluar_documentos(laboratorio_id, config.umbral_alerta_documento_dias)
        generadas += self._evaluar_mantenimientos(laboratorio_id, config.umbral_alerta_mantenimiento_dias)
        return generadas

    def _evaluar_calibraciones(self, laboratorio_id: uuid.UUID) -> int:
        # origen_id = equipo_id (no la calibración puntual): así RN-ALT-02
        # resuelve con solo mirar "¿este equipo tiene una calibración nueva?"
        # sin tener que rastrear cuál fue la calibración vencida que la originó.
        generadas = 0
        for equipo in self._calibraciones.listar_criticos(laboratorio_id):
            if equipo.semaforo not in ("rojo", "amarillo"):
                continue
            tipo = "critica" if equipo.semaforo == "rojo" else "preventiva"
            if equipo.semaforo == "rojo":
                mensaje = (
                    f"La calibración de {equipo.equipo_nombre} ({equipo.equipo_codigo_interno}) "
                    f"está vencida desde el {equipo.proxima_fecha}."
                )
            else:
                mensaje = (
                    f"La calibración de {equipo.equipo_nombre} ({equipo.equipo_codigo_interno}) "
                    f"vence el {equipo.proxima_fecha} (en {equipo.dias_restantes} días)."
                )
            alerta = self._alertas.generar_si_no_existe(
                laboratorio_id, tipo, "calibracion", equipo.equipo_id, mensaje
            )
            if alerta is not None:
                generadas += 1
        return generadas

    def _evaluar_documentos(self, laboratorio_id: uuid.UUID, umbral_dias: int) -> int:
        generadas = 0
        hoy = date.today()
        documentos = self._documentos.listar_vigencia_critica(laboratorio_id, umbral_dias)
        for documento in documentos:
            assert documento.fecha_vencimiento is not None
            vencido = documento.fecha_vencimiento < hoy
            tipo = "critica" if vencido else "preventiva"
            mensaje = (
                f"El documento '{documento.nombre}' está vencido desde el {documento.fecha_vencimiento}."
                if vencido
                else f"El documento '{documento.nombre}' vence el {documento.fecha_vencimiento}."
            )
            alerta = self._alertas.generar_si_no_existe(
                laboratorio_id, tipo, "documento", documento.id, mensaje
            )
            if alerta is not None:
                generadas += 1
        return generadas

    def _evaluar_mantenimientos(self, laboratorio_id: uuid.UUID, umbral_dias: int) -> int:
        generadas = 0
        for mantenimiento in self._mantenimientos.listar_proximos(laboratorio_id, umbral_dias):
            mensaje = f"El mantenimiento programado para el {mantenimiento.fecha_programada} se acerca."
            alerta = self._alertas.generar_si_no_existe(
                laboratorio_id, "preventiva", "mantenimiento", mantenimiento.id, mensaje
            )
            if alerta is not None:
                generadas += 1
        return generadas
