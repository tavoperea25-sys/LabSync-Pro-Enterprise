"""Caso de uso de Configuración — RF-CFG-03/04/05 (Sprint 12).

Centraliza la lectura/escritura de `configuraciones_laboratorio` en un único
servicio para que Calibraciones, Alertas, Reportes y Usuarios (los cuatro
módulos que antes tenían umbrales o política de contraseña hardcodeados)
lean todos del mismo lugar en vez de reimplementar el fallback a valores
por defecto cada uno por su cuenta."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from typing import Any

from app.core.errors import ErrorDeDominio
from app.modules.auditoria.domain.ports import AuditoriaRepository
from app.modules.auth.domain.entities import Laboratorio
from app.modules.auth.domain.ports import LaboratorioRepository
from app.modules.configuracion.domain.entities import ConfiguracionLaboratorio
from app.modules.configuracion.domain.ports import ConfiguracionRepository
from app.modules.mantenimientos.domain.entities import ESTADOS_OPERATIVOS_RESULTANTES, TIPOS_MANTENIMIENTO

_MODULO = "configuracion"

_LONGITUD_MINIMA_PISO = 8  # por debajo de esto, la política deja de ser "complejidad", es decorativa
_LONGITUD_MAXIMA_TECHO = 128
_CLAVES_POLITICA_VALIDAS = {
    "longitud_minima",
    "requiere_mayuscula",
    "requiere_minuscula",
    "requiere_digito",
    "requiere_simbolo",
}

# RF-CFG-04 — el logo se muestra en pantalla y (potencialmente) se embebe en
# encabezados de reportes; se restringe a formatos rasterizados web-safe,
# igual criterio que RF-CAL-06 restringe certificados a PDF.
_FORMATOS_LOGO_PERMITIDOS: dict[str, tuple[str, ...]] = {
    "png": ("image/png",),
    "jpg": ("image/jpeg",),
    "jpeg": ("image/jpeg",),
    "webp": ("image/webp",),
}
_TAMANO_MAXIMO_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB — es un logo, no una foto de alta resolución


class FormatoLogoNoSoportado(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "formato_logo_no_soportado",
            "El logo debe ser PNG, JPG o WEBP.",
            {"formatos_permitidos": sorted({e for exts in _FORMATOS_LOGO_PERMITIDOS.values() for e in exts})},
        )


class LogoDemasiadoGrande(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "logo_demasiado_grande",
            f"El logo no puede superar {_TAMANO_MAXIMO_LOGO_BYTES // (1024 * 1024)}MB.",
        )


@dataclass
class ActorContexto:
    usuario_id: uuid.UUID | None
    ip_origen: str | None


class UmbralInvalido(ErrorDeDominio):
    def __init__(self, campo: str) -> None:
        super().__init__("umbral_invalido", f"'{campo}' debe ser un número entero positivo.")


class PoliticaPasswordInvalida(ErrorDeDominio):
    def __init__(self, motivo: str) -> None:
        super().__init__("politica_password_invalida", motivo)


class MapeoEstadosMantenimientoInvalido(ErrorDeDominio):
    def __init__(self, motivo: str) -> None:
        super().__init__("mapeo_estados_mantenimiento_invalido", motivo)


class ConfiguracionService:
    def __init__(
        self,
        configuraciones: ConfiguracionRepository,
        laboratorios: LaboratorioRepository,
        almacenamiento_logos: Any,
        auditoria: AuditoriaRepository,
    ) -> None:
        self._configuraciones = configuraciones
        self._laboratorios = laboratorios
        self._almacenamiento = almacenamiento_logos
        self._auditoria = auditoria

    def obtener(self, laboratorio_id: uuid.UUID) -> ConfiguracionLaboratorio:
        return self._configuraciones.obtener(laboratorio_id) or ConfiguracionLaboratorio.por_defecto(
            laboratorio_id
        )

    def actualizar_umbrales(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        *,
        umbral_alerta_calibracion_dias: int,
        umbral_alerta_mantenimiento_dias: int,
        umbral_alerta_documento_dias: int,
        dias_retencion_papelera_documentos: int,
    ) -> ConfiguracionLaboratorio:
        """RF-CFG-03. Validación: 'los umbrales de alerta deben ser enteros
        positivos' (docs/03-requerimientos-funcionales.md Módulo 14). La
        ventana de retención de la papelera (RN-DOC-03) viaja en el mismo
        endpoint por ser, igual que los umbrales, un entero configurable por
        laboratorio sin sección propia — no amerita un endpoint dedicado."""
        for campo, valor in (
            ("umbral_alerta_calibracion_dias", umbral_alerta_calibracion_dias),
            ("umbral_alerta_mantenimiento_dias", umbral_alerta_mantenimiento_dias),
            ("umbral_alerta_documento_dias", umbral_alerta_documento_dias),
            ("dias_retencion_papelera_documentos", dias_retencion_papelera_documentos),
        ):
            if valor <= 0:
                raise UmbralInvalido(campo)

        actual = self.obtener(laboratorio_id)
        actualizado = self._configuraciones.guardar(
            replace(
                actual,
                laboratorio_id=laboratorio_id,
                umbral_alerta_calibracion_dias=umbral_alerta_calibracion_dias,
                umbral_alerta_mantenimiento_dias=umbral_alerta_mantenimiento_dias,
                umbral_alerta_documento_dias=umbral_alerta_documento_dias,
                dias_retencion_papelera_documentos=dias_retencion_papelera_documentos,
            )
        )
        self._auditar(laboratorio_id, actor, "actualizar_umbrales", actualizado)
        return actualizado

    def actualizar_politica_password(
        self, laboratorio_id: uuid.UUID, actor: ActorContexto, politica: dict[str, Any] | None
    ) -> ConfiguracionLaboratorio:
        """RF-CFG-03/RF-USR-05. `politica=None` restaura la política fija
        por defecto (`app/core/password_policy.py`)."""
        if politica is not None:
            self._validar_politica(politica)

        actual = self.obtener(laboratorio_id)
        actualizado = self._configuraciones.guardar(
            replace(actual, laboratorio_id=laboratorio_id, politica_password=politica)
        )
        self._auditar(laboratorio_id, actor, "actualizar_politica_password", actualizado)
        return actualizado

    def _validar_politica(self, politica: dict[str, Any]) -> None:
        claves_desconocidas = set(politica) - _CLAVES_POLITICA_VALIDAS
        if claves_desconocidas:
            claves = ", ".join(sorted(claves_desconocidas))
            raise PoliticaPasswordInvalida(f"Claves no reconocidas: {claves}.")

        if "longitud_minima" in politica:
            longitud = politica["longitud_minima"]
            if not isinstance(longitud, int) or isinstance(longitud, bool):
                raise PoliticaPasswordInvalida("'longitud_minima' debe ser un número entero.")
            if not (_LONGITUD_MINIMA_PISO <= longitud <= _LONGITUD_MAXIMA_TECHO):
                raise PoliticaPasswordInvalida(
                    f"'longitud_minima' debe estar entre {_LONGITUD_MINIMA_PISO} y {_LONGITUD_MAXIMA_TECHO}."
                )

        for clave in _CLAVES_POLITICA_VALIDAS - {"longitud_minima"}:
            if clave in politica and not isinstance(politica[clave], bool):
                raise PoliticaPasswordInvalida(f"'{clave}' debe ser verdadero o falso.")

    def actualizar_mapeo_estados_mantenimiento(
        self, laboratorio_id: uuid.UUID, actor: ActorContexto, mapeo: dict[str, str] | None
    ) -> ConfiguracionLaboratorio:
        """RN-MANT-01: "configurable por tipo". `mapeo=None` restaura la
        asignación fija por defecto (ver mantenimientos/domain/entities.py)."""
        if mapeo is not None:
            self._validar_mapeo_estados(mapeo)

        actual = self.obtener(laboratorio_id)
        actualizado = self._configuraciones.guardar(
            replace(actual, laboratorio_id=laboratorio_id, mapeo_estados_mantenimiento=mapeo)
        )
        self._auditar(laboratorio_id, actor, "actualizar_mapeo_estados_mantenimiento", actualizado)
        return actualizado

    def _validar_mapeo_estados(self, mapeo: dict[str, str]) -> None:
        tipos_desconocidos = set(mapeo) - set(TIPOS_MANTENIMIENTO)
        if tipos_desconocidos:
            tipos = ", ".join(sorted(tipos_desconocidos))
            raise MapeoEstadosMantenimientoInvalido(f"Tipos de mantenimiento no reconocidos: {tipos}.")
        for tipo, estado in mapeo.items():
            if estado not in ESTADOS_OPERATIVOS_RESULTANTES:
                raise MapeoEstadosMantenimientoInvalido(
                    f"'{estado}' no es válido para '{tipo}' — debe ser "
                    f"{' o '.join(ESTADOS_OPERATIVOS_RESULTANTES)}."
                )

    # ---- Institución (RF-CFG-04) -------------------------------------------

    def obtener_institucion(self, laboratorio_id: uuid.UUID) -> Laboratorio:
        laboratorio = self._laboratorios.obtener_por_id(laboratorio_id)
        assert laboratorio is not None  # el tenant del propio request, siempre existe
        return laboratorio

    def solicitar_url_logo(self, nombre_archivo: str, tipo_mime: str, tamano_bytes: int) -> tuple[str, str]:
        extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
        if extension not in _FORMATOS_LOGO_PERMITIDOS or tipo_mime not in _FORMATOS_LOGO_PERMITIDOS.get(
            extension, ()
        ):
            raise FormatoLogoNoSoportado()
        if tamano_bytes > _TAMANO_MAXIMO_LOGO_BYTES:
            raise LogoDemasiadoGrande()
        object_key = f"{uuid.uuid4()}.{extension}"
        url = self._almacenamiento.url_subida(object_key, tipo_mime)
        return url, object_key

    def actualizar_institucion(
        self, laboratorio_id: uuid.UUID, actor: ActorContexto, nombre: str, logo_object_key: str | None
    ) -> Laboratorio:
        laboratorio = self.obtener_institucion(laboratorio_id)
        actualizado = self._laboratorios.actualizar(
            replace(laboratorio, nombre=nombre, logo_object_key=logo_object_key)
        )
        self._auditoria.registrar(
            laboratorio_id=laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="actualizar_institucion",
            entidad_tipo="laboratorio",
            entidad_id=laboratorio_id,
            valor_anterior=None,
            valor_nuevo={"nombre": nombre, "tiene_logo": logo_object_key is not None},
        )
        return actualizado

    def url_logo(self, laboratorio: Laboratorio) -> str | None:
        if laboratorio.logo_object_key is None:
            return None
        return self._almacenamiento.url_descarga(laboratorio.logo_object_key, "logo")

    def _auditar(
        self, laboratorio_id: uuid.UUID, actor: ActorContexto, accion: str, config: ConfiguracionLaboratorio
    ) -> None:
        self._auditoria.registrar(
            laboratorio_id=laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion=accion,
            entidad_tipo="configuracion_laboratorio",
            entidad_id=None,
            valor_anterior=None,
            valor_nuevo={
                "umbral_alerta_calibracion_dias": config.umbral_alerta_calibracion_dias,
                "umbral_alerta_mantenimiento_dias": config.umbral_alerta_mantenimiento_dias,
                "umbral_alerta_documento_dias": config.umbral_alerta_documento_dias,
                "dias_retencion_papelera_documentos": config.dias_retencion_papelera_documentos,
                "politica_password_configurada": config.politica_password is not None,
                "mapeo_estados_mantenimiento": config.mapeo_estados_mantenimiento,
            },
        )
