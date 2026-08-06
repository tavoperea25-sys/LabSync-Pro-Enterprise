"""Casos de uso del módulo Alertas. Ver docs/03-requerimientos-funcionales.md
(RF-ALT-01 a RF-ALT-06 — Sprint 8) y docs/07-reglas-de-negocio.md (RN-ALT-*).

`generar_si_no_existe` es el único punto de entrada para crear alertas —
tanto el barrido periódico del worker como las transiciones síncronas
(ej. un equipo que pasa a "fuera de servicio") pasan por aquí, así RN-ALT-01
(no duplicar) se cumple sin importar quién dispara la alerta. Cada alerta
nueva encola su propia notificación en el outbox en la MISMA transacción —
nunca se empuja un WebSocket directamente desde este servicio."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime

from app.core.errors import ConflictoDeNegocio, RecursoNoEncontrado
from app.modules.alertas.domain.entities import Alerta, NotificacionPendiente
from app.modules.alertas.domain.ports import (
    AlertaRepository,
    FiltrosAlerta,
    NotificacionRepository,
    PaginaAlertas,
)

_MODULO = "alertas"


@dataclass
class ActorContexto:
    usuario_id: uuid.UUID | None
    ip_origen: str | None


class AlertaNoEncontrada(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("alerta_no_encontrada", "La alerta no existe.")


class AlertaYaResuelta(ConflictoDeNegocio):
    def __init__(self) -> None:
        super().__init__("alerta_ya_resuelta", "Esta alerta ya fue resuelta.")


class AlertaService:
    def __init__(self, alertas: AlertaRepository, notificaciones: NotificacionRepository) -> None:
        self._alertas = alertas
        self._notificaciones = notificaciones

    def generar_si_no_existe(
        self, laboratorio_id: uuid.UUID, tipo: str, origen_tipo: str, origen_id: uuid.UUID, mensaje: str
    ) -> Alerta | None:
        """RN-ALT-01. None si ya había una alerta activa equivalente — el
        llamador no necesita distinguir "ya existía" de "se creó", ambos
        casos terminan con una alerta activa para ese origen."""
        if self._alertas.existe_activa(origen_tipo, origen_id, tipo):
            return None

        alerta = self._alertas.crear(
            Alerta(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio_id,
                tipo=tipo,
                origen_tipo=origen_tipo,
                origen_id=origen_id,
                mensaje=mensaje,
                estado="activa",
                leida_en=None,
                resuelta_por_id=None,
                resuelta_en=None,
                creado_en=datetime.utcnow(),
            )
        )
        self._notificaciones.encolar(
            NotificacionPendiente(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio_id,
                alerta_id=alerta.id,
                canal="websocket",
                payload={
                    "evento": "alerta.nueva",
                    "alerta_id": str(alerta.id),
                    "tipo": alerta.tipo,
                    "origen_tipo": alerta.origen_tipo,
                    "mensaje": alerta.mensaje,
                },
                estado="pendiente",
                intentos=0,
                procesado_en=None,
                creado_en=datetime.utcnow(),
            )
        )
        return alerta

    def resolver_por_origen(self, origen_tipo: str, origen_id: uuid.UUID, actor: ActorContexto) -> int:
        """RN-ALT-02 — resolución automática como efecto secundario de una
        acción humana real (ej. registrar la calibración pendiente)."""
        return self._alertas.resolver_por_origen(origen_tipo, origen_id, actor.usuario_id)

    def listar(self, laboratorio_id: uuid.UUID, filtros: FiltrosAlerta) -> PaginaAlertas:
        return self._alertas.listar(laboratorio_id, filtros)

    def contar_activas(self, laboratorio_id: uuid.UUID) -> int:
        return self._alertas.contar_activas(laboratorio_id)

    def marcar_leida(self, alerta_id: uuid.UUID) -> Alerta:
        alerta = self._obtener(alerta_id)
        if alerta.leida_en is not None:
            return alerta
        return self._alertas.actualizar(replace(alerta, leida_en=datetime.utcnow()))

    def resolver_manual(self, alerta_id: uuid.UUID, actor: ActorContexto) -> Alerta:
        """RN-ALT-02 — marcado manual explícito por un humano."""
        alerta = self._obtener(alerta_id)
        if not alerta.esta_activa():
            raise AlertaYaResuelta()
        return self._alertas.actualizar(
            replace(
                alerta, estado="resuelta", resuelta_por_id=actor.usuario_id, resuelta_en=datetime.utcnow()
            )
        )

    def _obtener(self, alerta_id: uuid.UUID) -> Alerta:
        alerta = self._alertas.obtener_por_id(alerta_id)
        if alerta is None:
            raise AlertaNoEncontrada()
        return alerta
