"""Casos de uso del módulo QR. Ver docs/03-requerimientos-funcionales.md
Módulo 13 y docs/09-user-flows.md Flow 10."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass

from app.core.errors import ErrorDeDominio, RecursoNoEncontrado
from app.modules.auditoria.domain.ports import AuditoriaRepository
from app.modules.equipos.domain.entities import Equipo
from app.modules.equipos.domain.ports import EquipoRepository
from app.modules.qr.domain.entities import ESTADOS_INCIDENCIA, IncidenciaQr, IncidenciaQrConEquipo
from app.modules.qr.domain.ports import IncidenciaQrRepository, QrTokenRepository

_MODULO = "qr"


@dataclass
class ActorContexto:
    """Ver el mismo patrón en `equipos/application/equipo_service.py` —
    quién y desde dónde, ajeno a FastAPI/JWT."""

    usuario_id: uuid.UUID | None
    ip_origen: str | None


class TokenQrInvalido(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("token_qr_invalido", "Este código QR no es válido o fue revocado.")


class IncidenciaNoEncontrada(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("incidencia_no_encontrada", "La incidencia reportada no existe.")


class EstadoIncidenciaInvalido(ErrorDeDominio):
    def __init__(self, estado: str) -> None:
        super().__init__(
            "estado_incidencia_invalido",
            f"'{estado}' no es un estado válido de incidencia.",
            {"campo": "estado", "valores_permitidos": list(ESTADOS_INCIDENCIA)},
        )


@dataclass
class EquipoPublico:
    """RF-QR-02 — solo los campos que deben ser visibles sin autenticación.
    Deliberadamente NO incluye observaciones, proveedor, responsable ni
    ningún otro dato interno del laboratorio."""

    codigo_interno: str
    nombre: str
    estado_operativo: str
    marca: str | None
    modelo: str | None
    foto_url: str | None
    dado_de_baja: bool


class QrService:
    def __init__(
        self,
        qr_tokens: QrTokenRepository,
        incidencias: IncidenciaQrRepository,
        equipos: EquipoRepository,
        auditoria: AuditoriaRepository | None = None,
    ) -> None:
        self._qr_tokens = qr_tokens
        self._incidencias = incidencias
        self._equipos = equipos
        # Opcional: el flujo público (generar QR, ver equipo, reportar
        # incidencia) no necesita auditoría de "quién" porque no hay un
        # usuario autenticado detrás — solo los casos de uso autenticados
        # (`actualizar_estado_incidencia`) la requieren.
        self._auditoria = auditoria

    def generar_para_equipo(self, laboratorio_id: uuid.UUID, equipo_id: uuid.UUID) -> str:
        """RF-QR-01. RN-QR-01: token opaco de alta entropía, nunca el id
        incremental/UUID del equipo (evita enumeración)."""
        token = secrets.token_urlsafe(32)  # ~43 caracteres, cabe en VARCHAR(64)
        self._qr_tokens.crear(laboratorio_id, equipo_id, token)
        return token

    def resolver_equipo_id(self, token: str) -> tuple[uuid.UUID, uuid.UUID]:
        """Devuelve (laboratorio_id, equipo_id) — el llamador debe fijar el
        contexto de tenant con laboratorio_id ANTES de tocar `equipos`."""
        qr_token = self._qr_tokens.obtener_por_token(token)
        if qr_token is None or qr_token.revocado:
            raise TokenQrInvalido()
        return qr_token.laboratorio_id, qr_token.equipo_id

    def a_vista_publica(self, equipo: Equipo, foto_url: str | None = None) -> EquipoPublico:
        """RF-QR-02 — `foto_url` ya resuelta por el llamador (el propio
        servicio nunca toca MinIO, ver docstring de la clase). `None` en
        equipos sin fotografía cargada — la vista pública debe degradar con
        gracia, no romper."""
        return EquipoPublico(
            codigo_interno=equipo.codigo_interno,
            nombre=equipo.nombre,
            estado_operativo=equipo.estado_operativo,
            marca=equipo.marca,
            modelo=equipo.modelo,
            foto_url=foto_url,
            dado_de_baja=equipo.estado_operativo == "de_baja",
        )

    def reportar_incidencia(
        self,
        laboratorio_id: uuid.UUID,
        equipo_id: uuid.UUID,
        descripcion: str,
        contacto_nombre: str | None,
        contacto_medio: str | None,
    ) -> IncidenciaQr:
        """RF-QR-03 — sin autenticación, pero con contexto de tenant ya
        resuelto por el llamador vía `resolver_equipo_id`."""
        return self._incidencias.crear(
            laboratorio_id, equipo_id, descripcion, contacto_nombre, contacto_medio
        )

    def listar_incidencias(self, laboratorio_id: uuid.UUID) -> list[IncidenciaQrConEquipo]:
        """RF-QR-03 'Salidas' — la incidencia reportada por QR debe quedar
        visible como solicitud pendiente de triage; antes de este método no
        existía ningún camino de lectura, solo de escritura."""
        return self._incidencias.listar_con_equipo(laboratorio_id)

    def actualizar_estado_incidencia(
        self, incidencia_id: uuid.UUID, nuevo_estado: str, actor: ActorContexto
    ) -> IncidenciaQr:
        if nuevo_estado not in ESTADOS_INCIDENCIA:
            raise EstadoIncidenciaInvalido(nuevo_estado)

        actual = self._incidencias.obtener_por_id(incidencia_id)
        if actual is None:
            raise IncidenciaNoEncontrada()

        actualizada = self._incidencias.actualizar_estado(incidencia_id, nuevo_estado)

        if self._auditoria is not None:
            self._auditoria.registrar(
                laboratorio_id=actual.laboratorio_id,
                usuario_id=actor.usuario_id,
                ip_origen=actor.ip_origen,
                modulo=_MODULO,
                accion="actualizar_estado_incidencia",
                entidad_tipo="incidencia_qr",
                entidad_id=incidencia_id,
                valor_anterior={"estado": actual.estado},
                valor_nuevo={"estado": actualizada.estado},
            )
        return actualizada
