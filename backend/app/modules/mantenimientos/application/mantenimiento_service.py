"""Casos de uso del módulo Mantenimientos. Ver docs/03-requerimientos-funcionales.md
(RF-MANT-01 a RF-MANT-05 — Sprint 8) y docs/07-reglas-de-negocio.md (RN-MANT-*).

Máquina de estados explícita en 3 acciones (`iniciar`/`cerrar`/`cancelar`)
en vez de dejar que el estado se infiera de qué campos vienen en un PATCH
genérico — cada transición tiene su propia regla de negocio (RN-MANT-01/02)
y así queda auditada como una acción concreta, no como "una edición más"."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal

from app.core.errors import ConflictoDeNegocio, ErrorDeDominio, RecursoNoEncontrado
from app.modules.adjuntos.domain.entities import Adjunto
from app.modules.adjuntos.domain.ports import AdjuntoRepository
from app.modules.alertas.application.alerta_service import ActorContexto as ActorAlerta
from app.modules.alertas.application.alerta_service import AlertaService
from app.modules.auditoria.domain.ports import AuditoriaRepository
from app.modules.configuracion.domain.ports import ConfiguracionRepository
from app.modules.documentos.domain.ports import AlmacenamientoPort
from app.modules.equipos.domain.ports import EquipoRepository
from app.modules.mantenimientos.domain.entities import (
    TIPOS_MANTENIMIENTO,
    Mantenimiento,
    estado_operativo_para_tipo,
)
from app.modules.mantenimientos.domain.ports import (
    FiltrosMantenimiento,
    MantenimientoRepository,
    PaginaMantenimientos,
)

_MODULO = "mantenimientos"
# Resoluciones automáticas (RN-ALT-02) disparadas por transiciones de estado,
# no por un usuario resolviendo la alerta a mano — de ahí el actor "sistema".
_ACTOR_SISTEMA = ActorAlerta(usuario_id=None, ip_origen=None)
_ENTIDAD_TIPO_EVIDENCIA = "mantenimiento_evidencia"
_ENTIDAD_TIPO_INFORME = "mantenimiento_informe"

FORMATOS_PERMITIDOS_EVIDENCIA: dict[str, tuple[str, ...]] = {
    "jpg": ("image/jpeg",),
    "jpeg": ("image/jpeg",),
    "png": ("image/png",),
    "webp": ("image/webp",),
}
FORMATOS_PERMITIDOS_INFORME: dict[str, tuple[str, ...]] = {"pdf": ("application/pdf",)}
TAMANO_MAXIMO_EVIDENCIA_BYTES = 10 * 1024 * 1024
TAMANO_MAXIMO_INFORME_BYTES = 20 * 1024 * 1024


@dataclass
class ActorContexto:
    usuario_id: uuid.UUID | None
    ip_origen: str | None


class MantenimientoNoEncontrado(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("mantenimiento_no_encontrado", "El mantenimiento no existe.")


class EquipoNoEncontradoParaMantenimiento(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("equipo_no_encontrado", "El equipo no existe.")


class TransicionInvalida(ConflictoDeNegocio):
    def __init__(self, mensaje: str) -> None:
        super().__init__("transicion_invalida", mensaje)


class FaltaFechaEjecutada(ConflictoDeNegocio):
    def __init__(self) -> None:
        super().__init__(
            "falta_fecha_ejecutada",
            "No se puede cerrar un mantenimiento sin fecha de ejecución (RN-MANT-02).",
        )


@dataclass
class DatosMantenimiento:
    equipo_id: uuid.UUID
    tipo: str
    fecha_programada: date | None
    tecnico_responsable_id: uuid.UUID | None
    descripcion: str | None
    frecuencia_meses: int | None


@dataclass
class DatosCierre:
    fecha_ejecutada: date
    repuestos_utilizados: str | None
    tiempo_inactividad_horas: Decimal | None
    costo: Decimal | None
    descripcion: str | None


def _validar_tipo(tipo: str) -> None:
    if tipo not in TIPOS_MANTENIMIENTO:
        raise ErrorDeDominio(
            "tipo_invalido",
            f"'{tipo}' no es un tipo de mantenimiento válido.",
            {"valores_permitidos": list(TIPOS_MANTENIMIENTO)},
        )


class MantenimientoService:
    def __init__(
        self,
        mantenimientos: MantenimientoRepository,
        equipos: EquipoRepository,
        adjuntos: AdjuntoRepository,
        auditoria: AuditoriaRepository,
        almacenamiento: AlmacenamientoPort,
        alertas: AlertaService,
        configuraciones: ConfiguracionRepository,
    ) -> None:
        self._mantenimientos = mantenimientos
        self._equipos = equipos
        self._adjuntos = adjuntos
        self._auditoria = auditoria
        self._almacenamiento = almacenamiento
        self._alertas = alertas
        self._configuraciones = configuraciones

    def _mapeo_estados(self, laboratorio_id: uuid.UUID) -> dict[str, str] | None:
        config = self._configuraciones.obtener(laboratorio_id)
        return config.mapeo_estados_mantenimiento if config else None

    # ---- Adjuntos (evidencias fotográficas + informe — RF-MANT-05) -------

    def solicitar_url_evidencia(
        self, nombre_archivo: str, tipo_mime: str, tamano_bytes: int
    ) -> tuple[str, str]:
        return self._solicitar_url(
            nombre_archivo,
            tipo_mime,
            tamano_bytes,
            FORMATOS_PERMITIDOS_EVIDENCIA,
            TAMANO_MAXIMO_EVIDENCIA_BYTES,
            "evidencias",
        )

    def solicitar_url_informe(
        self, nombre_archivo: str, tipo_mime: str, tamano_bytes: int
    ) -> tuple[str, str]:
        return self._solicitar_url(
            nombre_archivo,
            tipo_mime,
            tamano_bytes,
            FORMATOS_PERMITIDOS_INFORME,
            TAMANO_MAXIMO_INFORME_BYTES,
            "informes",
        )

    def _solicitar_url(
        self,
        nombre_archivo: str,
        tipo_mime: str,
        tamano_bytes: int,
        formatos: dict[str, tuple[str, ...]],
        tamano_maximo: int,
        carpeta: str,
    ) -> tuple[str, str]:
        extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
        mimes_validos = formatos.get(extension)
        if mimes_validos is None or tipo_mime not in mimes_validos:
            raise ErrorDeDominio(
                "formato_no_permitido", f"El formato '.{extension}' no está permitido para {carpeta}."
            )
        if tamano_bytes > tamano_maximo:
            raise ErrorDeDominio(
                "archivo_demasiado_grande",
                f"El archivo supera el límite de {tamano_maximo // (1024 * 1024)} MB.",
            )
        object_key = f"mantenimientos/{carpeta}/{uuid.uuid4()}/{nombre_archivo}"
        url = self._almacenamiento.url_subida(object_key, tipo_mime)
        return url, object_key

    def agregar_evidencia(
        self,
        mantenimiento_id: uuid.UUID,
        actor: ActorContexto,
        object_key: str,
        nombre_archivo: str,
        tamano_bytes: int,
        tipo_mime: str,
    ) -> Adjunto:
        mantenimiento = self.obtener(mantenimiento_id)
        return self._adjuntos.crear(
            Adjunto(
                id=uuid.uuid4(),
                laboratorio_id=mantenimiento.laboratorio_id,
                entidad_tipo=_ENTIDAD_TIPO_EVIDENCIA,
                entidad_id=mantenimiento_id,
                object_key=object_key,
                nombre_archivo=nombre_archivo,
                tamano_bytes=tamano_bytes,
                tipo_mime=tipo_mime,
                subido_por_id=actor.usuario_id,
                creado_en=datetime.utcnow(),
            )
        )

    def listar_evidencias(self, mantenimiento_id: uuid.UUID) -> list[Adjunto]:
        self.obtener(mantenimiento_id)
        return self._adjuntos.listar_por_entidad(_ENTIDAD_TIPO_EVIDENCIA, mantenimiento_id)

    def asignar_informe(
        self,
        mantenimiento_id: uuid.UUID,
        actor: ActorContexto,
        object_key: str,
        nombre_archivo: str,
        tamano_bytes: int,
        tipo_mime: str,
    ) -> Mantenimiento:
        mantenimiento = self.obtener(mantenimiento_id)
        adjunto = self._adjuntos.crear(
            Adjunto(
                id=uuid.uuid4(),
                laboratorio_id=mantenimiento.laboratorio_id,
                entidad_tipo=_ENTIDAD_TIPO_INFORME,
                entidad_id=mantenimiento_id,
                object_key=object_key,
                nombre_archivo=nombre_archivo,
                tamano_bytes=tamano_bytes,
                tipo_mime=tipo_mime,
                subido_por_id=actor.usuario_id,
                creado_en=datetime.utcnow(),
            )
        )
        return self._mantenimientos.actualizar(replace(mantenimiento, informe_adjunto_id=adjunto.id))

    def url_evidencia(self, adjunto_id: uuid.UUID) -> str:
        adjunto = self._adjuntos.obtener_por_id(adjunto_id)
        if adjunto is None:
            raise RecursoNoEncontrado("evidencia_no_encontrada", "La evidencia no existe.")
        return self._almacenamiento.url_vista_previa(adjunto.object_key)

    def url_informe(self, mantenimiento_id: uuid.UUID) -> str:
        mantenimiento = self.obtener(mantenimiento_id)
        if mantenimiento.informe_adjunto_id is None:
            raise RecursoNoEncontrado("informe_no_disponible", "Este mantenimiento no tiene informe adjunto.")
        adjunto = self._adjuntos.obtener_por_id(mantenimiento.informe_adjunto_id)
        assert adjunto is not None
        return self._almacenamiento.url_descarga(adjunto.object_key, adjunto.nombre_archivo)

    # ---- Ciclo de vida --------------------------------------------------

    def crear(
        self, laboratorio_id: uuid.UUID, actor: ActorContexto, datos: DatosMantenimiento
    ) -> Mantenimiento:
        """RF-MANT-01 — siempre nace "programado"; `iniciar()` es la
        transición explícita que dispara RN-MANT-01."""
        _validar_tipo(datos.tipo)
        equipo = self._equipos.obtener_por_id(datos.equipo_id)
        if equipo is None or not equipo.esta_activo():
            raise EquipoNoEncontradoParaMantenimiento()

        ahora = datetime.utcnow()
        mantenimiento = self._mantenimientos.crear(
            Mantenimiento(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio_id,
                equipo_id=datos.equipo_id,
                tipo=datos.tipo,
                estado="programado",
                fecha_programada=datos.fecha_programada,
                fecha_ejecutada=None,
                tecnico_responsable_id=datos.tecnico_responsable_id or actor.usuario_id,
                descripcion=datos.descripcion,
                repuestos_utilizados=None,
                tiempo_inactividad_horas=None,
                costo=None,
                informe_adjunto_id=None,
                frecuencia_meses=datos.frecuencia_meses,
                generado_de_id=None,
                creado_en=ahora,
                actualizado_en=ahora,
            )
        )
        self._auditar(mantenimiento, actor, "crear", None)
        return mantenimiento

    def iniciar(self, mantenimiento_id: uuid.UUID, actor: ActorContexto) -> Mantenimiento:
        """RF-MANT-03/RN-MANT-01."""
        mantenimiento = self.obtener(mantenimiento_id)
        if mantenimiento.estado != "programado":
            raise TransicionInvalida("Solo se puede iniciar un mantenimiento en estado 'programado'.")

        guardado = self._mantenimientos.actualizar(replace(mantenimiento, estado="en_ejecucion"))
        mapeo = self._mapeo_estados(mantenimiento.laboratorio_id)
        self._cambiar_estado_equipo(
            mantenimiento.equipo_id, estado_operativo_para_tipo(mantenimiento.tipo, mapeo)
        )
        self._auditar(guardado, actor, "iniciar", None)
        return guardado

    def cerrar(self, mantenimiento_id: uuid.UUID, actor: ActorContexto, datos: DatosCierre) -> Mantenimiento:
        """RF-MANT-01/03/RN-MANT-01/02. Si es preventivo con
        `frecuencia_meses`, autogenera el siguiente (RF-MANT-02)."""
        mantenimiento = self.obtener(mantenimiento_id)
        if mantenimiento.estado not in ("programado", "en_ejecucion"):
            raise TransicionInvalida("Solo se puede cerrar un mantenimiento programado o en ejecución.")
        if datos.fecha_ejecutada is None:
            raise FaltaFechaEjecutada()

        guardado = self._mantenimientos.actualizar(
            replace(
                mantenimiento,
                estado="completado",
                fecha_ejecutada=datos.fecha_ejecutada,
                repuestos_utilizados=datos.repuestos_utilizados,
                tiempo_inactividad_horas=datos.tiempo_inactividad_horas,
                costo=datos.costo,
                descripcion=datos.descripcion or mantenimiento.descripcion,
            )
        )
        self._revertir_estado_equipo_si_corresponde(mantenimiento.equipo_id, mantenimiento.id)
        self._alertas.resolver_por_origen("mantenimiento", mantenimiento.id, _ACTOR_SISTEMA)
        self._auditar(guardado, actor, "cerrar", None)

        if mantenimiento.tipo == "preventivo" and mantenimiento.frecuencia_meses:
            self._generar_siguiente(guardado, actor)

        return guardado

    def cancelar(self, mantenimiento_id: uuid.UUID, actor: ActorContexto, motivo: str) -> Mantenimiento:
        mantenimiento = self.obtener(mantenimiento_id)
        if mantenimiento.estado not in ("programado", "en_ejecucion"):
            raise TransicionInvalida("Solo se puede cancelar un mantenimiento programado o en ejecución.")

        guardado = self._mantenimientos.actualizar(replace(mantenimiento, estado="cancelado"))
        if mantenimiento.estado == "en_ejecucion":
            self._revertir_estado_equipo_si_corresponde(mantenimiento.equipo_id, mantenimiento.id)
        self._alertas.resolver_por_origen("mantenimiento", mantenimiento.id, _ACTOR_SISTEMA)
        self._auditar(guardado, actor, "cancelar", {"motivo": motivo})
        return guardado

    def _generar_siguiente(self, cerrado: Mantenimiento, actor: ActorContexto) -> Mantenimiento:
        from app.modules.calibraciones.domain.entities import calcular_proxima_fecha

        assert cerrado.frecuencia_meses is not None
        siguiente_fecha = calcular_proxima_fecha(
            cerrado.fecha_ejecutada or date.today(), cerrado.frecuencia_meses
        )
        ahora = datetime.utcnow()
        siguiente = self._mantenimientos.crear(
            Mantenimiento(
                id=uuid.uuid4(),
                laboratorio_id=cerrado.laboratorio_id,
                equipo_id=cerrado.equipo_id,
                tipo=cerrado.tipo,
                estado="programado",
                fecha_programada=siguiente_fecha,
                fecha_ejecutada=None,
                tecnico_responsable_id=cerrado.tecnico_responsable_id,
                descripcion=cerrado.descripcion,
                repuestos_utilizados=None,
                tiempo_inactividad_horas=None,
                costo=None,
                informe_adjunto_id=None,
                frecuencia_meses=cerrado.frecuencia_meses,
                generado_de_id=cerrado.id,
                creado_en=ahora,
                actualizado_en=ahora,
            )
        )
        self._auditar(siguiente, actor, "generar_recurrente", {"generado_de_id": str(cerrado.id)})
        return siguiente

    def _cambiar_estado_equipo(self, equipo_id: uuid.UUID, nuevo_estado: str) -> None:
        equipo = self._equipos.obtener_por_id(equipo_id)
        assert equipo is not None
        self._equipos.actualizar(replace(equipo, estado_operativo=nuevo_estado))
        if nuevo_estado == "fuera_de_servicio":
            # RF-ALT-01 — evento discreto, no una condición de barrido: se
            # dispara en el momento exacto de la transición.
            self._alertas.generar_si_no_existe(
                equipo.laboratorio_id,
                "critica",
                "equipo",
                equipo_id,
                f"{equipo.nombre} ({equipo.codigo_interno}) está fuera de servicio.",
            )

    def _revertir_estado_equipo_si_corresponde(
        self, equipo_id: uuid.UUID, mantenimiento_id: uuid.UUID
    ) -> None:
        """RN-MANT-01 — vuelve a "operativo" solo si no quedan OTROS
        mantenimientos abiertos para el mismo equipo."""
        if self._mantenimientos.contar_abiertos_por_equipo(equipo_id, excluir_id=mantenimiento_id) == 0:
            self._cambiar_estado_equipo(equipo_id, "operativo")
            self._alertas.resolver_por_origen("equipo", equipo_id, _ACTOR_SISTEMA)

    # ---- Lectura ----------------------------------------------------

    def obtener(self, mantenimiento_id: uuid.UUID) -> Mantenimiento:
        mantenimiento = self._mantenimientos.obtener_por_id(mantenimiento_id)
        if mantenimiento is None:
            raise MantenimientoNoEncontrado()
        return mantenimiento

    def listar(self, laboratorio_id: uuid.UUID, filtros: FiltrosMantenimiento) -> PaginaMantenimientos:
        return self._mantenimientos.listar(laboratorio_id, filtros)

    def inactividad_por_equipo(self, equipo_id: uuid.UUID, desde: date, hasta: date) -> Decimal:
        return self._mantenimientos.sumar_inactividad(equipo_id, desde, hasta)

    def mis_mantenimientos_de_hoy(self, tecnico_id: uuid.UUID) -> list[Mantenimiento]:
        return self._mantenimientos.listar_proximos_por_tecnico(tecnico_id, date.today())

    # ---- Auditoría ------------------------------------------------------

    def _auditar(
        self, mantenimiento: Mantenimiento, actor: ActorContexto, accion: str, extra: dict | None
    ) -> None:
        self._auditoria.registrar(
            laboratorio_id=mantenimiento.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion=accion,
            entidad_tipo="mantenimiento",
            entidad_id=mantenimiento.id,
            valor_anterior=None,
            valor_nuevo={
                "equipo_id": str(mantenimiento.equipo_id),
                "estado": mantenimiento.estado,
                **(extra or {}),
            },
        )
