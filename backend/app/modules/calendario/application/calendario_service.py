"""Casos de uso del módulo Calendario. Ver docs/03-requerimientos-funcionales.md
(RF-CAL2-01 a 05 — Sprint 9).

`listar` es el único punto de lectura y fusiona 4 fuentes: los eventos
manuales persistidos (`EventoCalendarioRepository`) más 3 fuentes
sintetizadas en el momento (calibraciones, mantenimientos, documentos) —
ver docstring de la migración 0008 para el porqué de no materializarlas."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time

from app.core.errors import ErrorDeDominio, RecursoNoEncontrado
from app.modules.auditoria.domain.ports import AuditoriaRepository
from app.modules.calendario.domain.entities import TIPOS_EVENTO_MANUAL, EventoCalendario
from app.modules.calendario.domain.ports import EventoCalendarioRepository, FiltrosEventoCalendario
from app.modules.calibraciones.domain.ports import CalibracionRepository
from app.modules.documentos.domain.ports import DocumentoRepository
from app.modules.equipos.domain.ports import EquipoRepository, FiltrosEquipo
from app.modules.mantenimientos.domain.ports import FiltrosMantenimiento, MantenimientoRepository

_MODULO = "calendario"
# Los eventos sintetizados solo tienen una `date`, sin hora — se anclan al
# mediodía UTC (no medianoche) para que, al convertir a la zona horaria
# local del navegador, el día calendario mostrado siga siendo el correcto
# en cualquier huso horario razonable (medianoche UTC se corre un día hacia
# atrás en cualquier huso con offset negativo, ej. América).
_MEDIODIA_UTC = time(12, 0)


@dataclass
class ActorContexto:
    usuario_id: uuid.UUID | None
    ip_origen: str | None


@dataclass
class DatosEventoCalendario:
    tipo: str
    titulo: str
    fecha: datetime
    descripcion: str | None = None


@dataclass
class FiltrosCalendario:
    desde: datetime
    hasta: datetime
    tipo: str | None = None
    area_id: uuid.UUID | None = None
    responsable_id: uuid.UUID | None = None


class EventoNoEncontrado(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("evento_no_encontrado", "El evento no existe.")


def _validar_tipo_manual(tipo: str) -> None:
    if tipo not in TIPOS_EVENTO_MANUAL:
        raise ErrorDeDominio(
            "tipo_invalido",
            f"'{tipo}' no es un tipo de evento que se pueda crear manualmente.",
            {"valores_permitidos": list(TIPOS_EVENTO_MANUAL)},
        )


class CalendarioService:
    def __init__(
        self,
        eventos: EventoCalendarioRepository,
        calibraciones: CalibracionRepository,
        mantenimientos: MantenimientoRepository,
        documentos: DocumentoRepository,
        equipos: EquipoRepository,
        auditoria: AuditoriaRepository,
    ) -> None:
        self._eventos = eventos
        self._calibraciones = calibraciones
        self._mantenimientos = mantenimientos
        self._documentos = documentos
        self._equipos = equipos
        self._auditoria = auditoria

    # ---- CRUD de eventos manuales (RF-CAL2-03) ---------------------------

    def crear(
        self, laboratorio_id: uuid.UUID, actor: ActorContexto, datos: DatosEventoCalendario
    ) -> EventoCalendario:
        _validar_tipo_manual(datos.tipo)
        ahora = datetime.now(UTC)
        evento = self._eventos.crear(
            EventoCalendario(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio_id,
                tipo=datos.tipo,
                titulo=datos.titulo,
                descripcion=datos.descripcion,
                fecha=datos.fecha,
                origen_tipo=None,
                origen_id=None,
                creado_por_id=actor.usuario_id,
                creado_en=ahora,
                actualizado_en=ahora,
            )
        )
        self._auditar(evento, actor, "crear")
        return evento

    def actualizar(
        self, evento_id: uuid.UUID, actor: ActorContexto, datos: DatosEventoCalendario
    ) -> EventoCalendario:
        evento = self.obtener(evento_id)
        actualizado = self._eventos.actualizar(
            replace(evento, titulo=datos.titulo, descripcion=datos.descripcion, fecha=datos.fecha)
        )
        self._auditar(actualizado, actor, "actualizar")
        return actualizado

    def eliminar(self, evento_id: uuid.UUID, actor: ActorContexto) -> None:
        evento = self.obtener(evento_id)
        self._eventos.eliminar(evento_id)
        self._auditar(evento, actor, "eliminar")

    def obtener(self, evento_id: uuid.UUID) -> EventoCalendario:
        evento = self._eventos.obtener_por_id(evento_id)
        if evento is None:
            raise EventoNoEncontrado()
        return evento

    # ---- Lectura fusionada (RF-CAL2-01/02/04) ----------------------------

    def listar(self, laboratorio_id: uuid.UUID, filtros: FiltrosCalendario) -> list[EventoCalendario]:
        eventos: list[EventoCalendario] = []

        if filtros.tipo is None or filtros.tipo in TIPOS_EVENTO_MANUAL:
            tipo_manual = filtros.tipo if filtros.tipo in TIPOS_EVENTO_MANUAL else None
            eventos.extend(
                self._eventos.listar(
                    laboratorio_id, FiltrosEventoCalendario(filtros.desde, filtros.hasta, tipo_manual)
                )
            )

        equipos_permitidos: set[uuid.UUID] | None = None
        if filtros.area_id is not None or filtros.responsable_id is not None:
            candidatos = self._equipos.listar_todos(FiltrosEquipo(area_id=filtros.area_id))
            equipos_permitidos = {
                e.id
                for e in candidatos
                if filtros.responsable_id is None or e.responsable_id == filtros.responsable_id
            }

        desde_fecha, hasta_fecha = filtros.desde.date(), filtros.hasta.date()

        if filtros.tipo is None or filtros.tipo == "calibracion":
            eventos.extend(
                self._eventos_calibracion(laboratorio_id, desde_fecha, hasta_fecha, equipos_permitidos)
            )

        if filtros.tipo is None or filtros.tipo == "mantenimiento":
            eventos.extend(
                self._eventos_mantenimiento(laboratorio_id, desde_fecha, hasta_fecha, equipos_permitidos)
            )

        if filtros.tipo is None or filtros.tipo == "vencimiento_documental":
            if equipos_permitidos is None:
                eventos.extend(self._eventos_documento(laboratorio_id, desde_fecha, hasta_fecha))
            # Un filtro de área/responsable no aplica a documentos (no tienen
            # equipo asociado) — se excluyen en vez de mostrarlos sin filtrar,
            # más seguro que ignorar el filtro silenciosamente.

        eventos.sort(key=lambda e: e.fecha)
        return eventos

    def _eventos_calibracion(
        self,
        laboratorio_id: uuid.UUID,
        desde: date,
        hasta: date,
        equipos_permitidos: set[uuid.UUID] | None,
    ) -> list[EventoCalendario]:
        ahora = datetime.now(UTC)
        resultado = []
        for fila in self._calibraciones.listar_proximas(laboratorio_id, desde, hasta):
            if equipos_permitidos is not None and fila.equipo_id not in equipos_permitidos:
                continue
            assert fila.proxima_fecha is not None
            resultado.append(
                EventoCalendario(
                    id=fila.ultima_calibracion_id or fila.equipo_id,
                    laboratorio_id=laboratorio_id,
                    tipo="calibracion",
                    titulo=f"Calibración: {fila.equipo_nombre} ({fila.equipo_codigo_interno})",
                    descripcion=None,
                    fecha=datetime.combine(fila.proxima_fecha, _MEDIODIA_UTC, tzinfo=UTC),
                    origen_tipo="equipo",
                    origen_id=fila.equipo_id,
                    creado_por_id=None,
                    creado_en=ahora,
                    actualizado_en=ahora,
                )
            )
        return resultado

    def _eventos_mantenimiento(
        self,
        laboratorio_id: uuid.UUID,
        desde: date,
        hasta: date,
        equipos_permitidos: set[uuid.UUID] | None,
    ) -> list[EventoCalendario]:
        ahora = datetime.now(UTC)
        resultado = []
        mantenimientos = self._mantenimientos.listar_todos(
            laboratorio_id, FiltrosMantenimiento(estado="programado", fecha_desde=desde, fecha_hasta=hasta)
        )
        for mantenimiento in mantenimientos:
            if equipos_permitidos is not None and mantenimiento.equipo_id not in equipos_permitidos:
                continue
            if mantenimiento.fecha_programada is None:
                continue
            equipo = self._equipos.obtener_por_id(mantenimiento.equipo_id)
            nombre_equipo = equipo.nombre if equipo is not None else "equipo eliminado"
            resultado.append(
                EventoCalendario(
                    id=mantenimiento.id,
                    laboratorio_id=laboratorio_id,
                    tipo="mantenimiento",
                    titulo=f"Mantenimiento: {nombre_equipo}",
                    descripcion=mantenimiento.descripcion,
                    fecha=datetime.combine(mantenimiento.fecha_programada, _MEDIODIA_UTC, tzinfo=UTC),
                    origen_tipo="equipo",
                    origen_id=mantenimiento.equipo_id,
                    creado_por_id=None,
                    creado_en=ahora,
                    actualizado_en=ahora,
                )
            )
        return resultado

    def _eventos_documento(
        self,
        laboratorio_id: uuid.UUID,
        desde: date,
        hasta: date,
    ) -> list[EventoCalendario]:
        ahora = datetime.now(UTC)
        resultado = []
        for documento in self._documentos.listar_por_vencimiento_rango(laboratorio_id, desde, hasta):
            assert documento.fecha_vencimiento is not None
            resultado.append(
                EventoCalendario(
                    id=documento.id,
                    laboratorio_id=laboratorio_id,
                    tipo="vencimiento_documental",
                    titulo=f"Vence: {documento.nombre}",
                    descripcion=None,
                    fecha=datetime.combine(documento.fecha_vencimiento, _MEDIODIA_UTC, tzinfo=UTC),
                    origen_tipo="documento",
                    origen_id=documento.id,
                    creado_por_id=None,
                    creado_en=ahora,
                    actualizado_en=ahora,
                )
            )
        return resultado

    # ---- Auditoría --------------------------------------------------------

    def _auditar(self, evento: EventoCalendario, actor: ActorContexto, accion: str) -> None:
        self._auditoria.registrar(
            laboratorio_id=evento.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion=accion,
            entidad_tipo="evento_calendario",
            entidad_id=evento.id,
            valor_anterior=None,
            valor_nuevo={"tipo": evento.tipo, "titulo": evento.titulo},
        )
