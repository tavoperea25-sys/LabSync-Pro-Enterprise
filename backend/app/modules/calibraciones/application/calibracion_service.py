"""Casos de uso del módulo Calibraciones. Ver docs/03-requerimientos-funcionales.md
(RF-CAL-01 a RF-CAL-07 — Sprint 7) y docs/07-reglas-de-negocio.md (RN-CAL-*).

RN-CAL-02 es la regla que más distingue este módulo de Equipos/Documentos:
una calibración jamás se actualiza ni se elimina — "corregir" siempre
INSERTA una fila nueva con `corrige_a_id` apuntando a la original. No existe
`actualizar()` en este servicio a propósito."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.core.errors import ErrorDeDominio, RecursoNoEncontrado
from app.modules.adjuntos.domain.entities import Adjunto
from app.modules.adjuntos.domain.ports import AdjuntoRepository
from app.modules.alertas.application.alerta_service import ActorContexto as ActorAlerta
from app.modules.alertas.application.alerta_service import AlertaService
from app.modules.auditoria.domain.ports import AuditoriaRepository
from app.modules.calibraciones.domain.entities import (
    FORMATOS_PERMITIDOS_CERTIFICADO,
    RESULTADOS_CALIBRACION,
    TAMANO_MAXIMO_CERTIFICADO_BYTES,
    Calibracion,
    EquipoConSemaforo,
    calcular_proxima_fecha,
)
from app.modules.calibraciones.domain.ports import CalibracionRepository
from app.modules.documentos.domain.ports import AlmacenamientoPort
from app.modules.equipos.domain.ports import EquipoRepository

_ENTIDAD_TIPO_ADJUNTO = "calibracion_certificado"
_MODULO = "calibraciones"
_ACTOR_SISTEMA = ActorAlerta(usuario_id=None, ip_origen=None)


@dataclass
class ActorContexto:
    usuario_id: uuid.UUID | None
    ip_origen: str | None


class CalibracionNoEncontrada(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("calibracion_no_encontrada", "La calibración no existe.")


class EquipoNoEncontradoParaCalibracion(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("equipo_no_encontrado", "El equipo no existe.")


class CertificadoNoDisponible(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("certificado_no_disponible", "Esta calibración no tiene certificado adjunto.")


class FormatoDeCertificadoInvalido(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "formato_certificado_invalido", "El certificado de calibración debe ser un archivo PDF."
        )


class CertificadoDemasiadoGrande(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "certificado_demasiado_grande",
            f"El certificado supera el límite de {TAMANO_MAXIMO_CERTIFICADO_BYTES // (1024 * 1024)} MB.",
        )


def _validar_datos(fecha_calibracion: date, frecuencia_meses: int, resultado: str) -> None:
    if fecha_calibracion > date.today():
        raise ErrorDeDominio(
            "fecha_calibracion_futura", "La fecha de calibración no puede ser posterior a hoy."
        )
    if frecuencia_meses <= 0:
        raise ErrorDeDominio("frecuencia_invalida", "La frecuencia debe ser mayor a cero meses.")
    if resultado not in RESULTADOS_CALIBRACION:
        raise ErrorDeDominio(
            "resultado_invalido",
            f"'{resultado}' no es un resultado válido.",
            {"valores_permitidos": list(RESULTADOS_CALIBRACION)},
        )


@dataclass
class DatosCalibracion:
    equipo_id: uuid.UUID
    fecha_calibracion: date
    frecuencia_meses: int
    laboratorio_proveedor: str | None
    numero_certificado: str | None
    resultado: str
    incertidumbre: Decimal | None
    observaciones: str | None


class CalibracionService:
    def __init__(
        self,
        calibraciones: CalibracionRepository,
        equipos: EquipoRepository,
        adjuntos: AdjuntoRepository,
        auditoria: AuditoriaRepository,
        almacenamiento: AlmacenamientoPort,
        alertas: AlertaService,
    ) -> None:
        self._calibraciones = calibraciones
        self._equipos = equipos
        self._adjuntos = adjuntos
        self._auditoria = auditoria
        self._almacenamiento = almacenamiento
        self._alertas = alertas

    def solicitar_url_certificado(
        self, nombre_archivo: str, tipo_mime: str, tamano_bytes: int
    ) -> tuple[str, str]:
        extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
        mimes_validos = FORMATOS_PERMITIDOS_CERTIFICADO.get(extension)
        if mimes_validos is None or tipo_mime not in mimes_validos:
            raise FormatoDeCertificadoInvalido()
        if tamano_bytes > TAMANO_MAXIMO_CERTIFICADO_BYTES:
            raise CertificadoDemasiadoGrande()
        object_key = f"calibraciones/{uuid.uuid4()}/{nombre_archivo}"
        url = self._almacenamiento.url_subida(object_key, tipo_mime)
        return url, object_key

    def crear(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        datos: DatosCalibracion,
        certificado: tuple[str, str, int, str] | None = None,
    ) -> Calibracion:
        """RF-CAL-01/02/03. `certificado`, si se da, es
        (object_key, nombre_archivo, tamano_bytes, tipo_mime) ya subido a
        MinIO — mismo patrón de confirmación en dos pasos que Documentos."""
        return self._crear_fila(laboratorio_id, actor, datos, certificado, corrige_a_id=None, motivo=None)

    def corregir(
        self,
        calibracion_id: uuid.UUID,
        actor: ActorContexto,
        datos: DatosCalibracion,
        motivo: str,
        certificado: tuple[str, str, int, str] | None = None,
    ) -> Calibracion:
        """RN-CAL-02 — nunca se edita ni se elimina la original; se inserta
        una fila nueva referenciándola. `motivo` es obligatorio."""
        original = self.obtener(calibracion_id)
        return self._crear_fila(
            original.laboratorio_id, actor, datos, certificado, corrige_a_id=original.id, motivo=motivo
        )

    def _crear_fila(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        datos: DatosCalibracion,
        certificado: tuple[str, str, int, str] | None,
        corrige_a_id: uuid.UUID | None,
        motivo: str | None,
    ) -> Calibracion:
        _validar_datos(datos.fecha_calibracion, datos.frecuencia_meses, datos.resultado)
        equipo = self._equipos.obtener_por_id(datos.equipo_id)
        if equipo is None or not equipo.esta_activo():
            raise EquipoNoEncontradoParaCalibracion()

        calibracion_id = uuid.uuid4()

        certificado_adjunto_id = None
        if certificado is not None:
            object_key, nombre_archivo, tamano_bytes, tipo_mime = certificado
            adjunto = self._adjuntos.crear(
                Adjunto(
                    id=uuid.uuid4(),
                    laboratorio_id=laboratorio_id,
                    entidad_tipo=_ENTIDAD_TIPO_ADJUNTO,
                    entidad_id=calibracion_id,
                    object_key=object_key,
                    nombre_archivo=nombre_archivo,
                    tamano_bytes=tamano_bytes,
                    tipo_mime=tipo_mime,
                    subido_por_id=actor.usuario_id,
                    creado_en=datetime.utcnow(),
                )
            )
            certificado_adjunto_id = adjunto.id

        calibracion = self._calibraciones.crear(
            Calibracion(
                id=calibracion_id,
                laboratorio_id=laboratorio_id,
                equipo_id=datos.equipo_id,
                fecha_calibracion=datos.fecha_calibracion,
                frecuencia_meses=datos.frecuencia_meses,
                proxima_fecha=calcular_proxima_fecha(datos.fecha_calibracion, datos.frecuencia_meses),
                laboratorio_proveedor=datos.laboratorio_proveedor,
                numero_certificado=datos.numero_certificado,
                resultado=datos.resultado,
                incertidumbre=datos.incertidumbre,
                responsable_id=actor.usuario_id,
                certificado_adjunto_id=certificado_adjunto_id,
                corrige_a_id=corrige_a_id,
                motivo_correccion=motivo,
                observaciones=datos.observaciones,
                creado_en=datetime.utcnow(),
            )
        )

        if datos.resultado == "no_conforme":
            # RN-CAL-04 (docs/07-reglas-de-negocio.md) — evento discreto, no
            # una condición de barrido: se dispara síncronamente en el
            # momento del registro, mismo patrón que "equipo fuera de
            # servicio" en Mantenimientos. `origen_id=calibracion.id` (no
            # `equipo_id`) a propósito — el origen "calibracion"/`equipo_id`
            # ya está reservado para las alertas de vencimiento del barrido
            # periódico (`evaluador_service.py`); reutilizar esa misma clave
            # aquí colisionaría con RN-ALT-01 (deduplicación) y la resolvería
            # por accidente en la línea de abajo. Se resuelve solo a mano
            # (`alertas.gestionar`) — un resultado fallido debe revisarse
            # explícitamente, nunca taparse solo porque llegó una calibración
            # posterior.
            self._alertas.generar_si_no_existe(
                laboratorio_id,
                "critica",
                "calibracion",
                calibracion.id,
                f"{equipo.nombre} ({equipo.codigo_interno}) no superó su calibración del "
                f"{datos.fecha_calibracion} — revisar antes de continuar en uso.",
            )

        # RN-ALT-02 — un registro nuevo (crear o corregir) es la señal de
        # "esta calibración ya no está pendiente"; se resuelve por equipo,
        # no por la calibración vencida puntual (ver evaluador_service.py).
        self._alertas.resolver_por_origen("calibracion", datos.equipo_id, _ACTOR_SISTEMA)

        self._auditoria.registrar(
            laboratorio_id=laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="corregir" if corrige_a_id else "crear",
            entidad_tipo="calibracion",
            entidad_id=calibracion.id,
            valor_anterior={"corrige_a_id": str(corrige_a_id), "motivo": motivo} if corrige_a_id else None,
            valor_nuevo={"equipo_id": str(datos.equipo_id), "resultado": datos.resultado},
        )
        return calibracion

    def obtener(self, calibracion_id: uuid.UUID) -> Calibracion:
        calibracion = self._calibraciones.obtener_por_id(calibracion_id)
        if calibracion is None:
            raise CalibracionNoEncontrada()
        return calibracion

    def listar_por_equipo(self, equipo_id: uuid.UUID) -> list[Calibracion]:
        return self._calibraciones.listar_por_equipo(equipo_id)

    def listar_criticos(self, laboratorio_id: uuid.UUID) -> list[EquipoConSemaforo]:
        return self._calibraciones.listar_criticos(laboratorio_id)

    def url_certificado(self, calibracion_id: uuid.UUID) -> str:
        calibracion = self.obtener(calibracion_id)
        if calibracion.certificado_adjunto_id is None:
            raise CertificadoNoDisponible()
        adjunto = self._adjuntos.obtener_por_id(calibracion.certificado_adjunto_id)
        if adjunto is None:
            raise CertificadoNoDisponible()
        return self._almacenamiento.url_descarga(adjunto.object_key, adjunto.nombre_archivo)
