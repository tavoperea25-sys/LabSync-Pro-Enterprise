"""Casos de uso del módulo Equipos. Ver docs/03-requerimientos-funcionales.md
Módulo 3 y docs/07-reglas-de-negocio.md (RN-EQ-*)."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime

from app.core.errors import ConflictoDeNegocio, ErrorDeDominio, RecursoNoEncontrado
from app.modules.auditoria.domain.entities import LogAuditoria
from app.modules.auditoria.domain.ports import AuditoriaRepository
from app.modules.documentos.domain.ports import AlmacenamientoPort
from app.modules.equipos.domain.entities import (
    CLASIFICACIONES_RIESGO,
    CONDICIONES_FISICAS,
    CRITICIDADES,
    ESTADOS_OPERATIVOS,
    FORMAS_ADQUISICION,
    Equipo,
)
from app.modules.equipos.domain.ports import EquipoRepository, FiltrosEquipo, PaginaEquipos
from app.modules.equipos.infrastructure.repositories import (
    FabricanteRepositorySQLAlchemy,
    FichaTecnicaRepositorySQLAlchemy,
    ProveedorRepositorySQLAlchemy,
)

_MODULO = "equipos"

# RF-EQ-01 — "tipo de archivo permitido para fotografía (JPG/PNG/WEBP)".
FORMATOS_PERMITIDOS_FOTO: dict[str, tuple[str, ...]] = {
    "jpg": ("image/jpeg",),
    "jpeg": ("image/jpeg",),
    "png": ("image/png",),
    "webp": ("image/webp",),
}
TAMANO_MAXIMO_FOTO_BYTES = 5 * 1024 * 1024


class FormatoFotoNoSoportado(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "formato_foto_no_soportado",
            "La fotografía debe ser JPG, PNG o WEBP.",
            {"formatos_permitidos": sorted({e for exts in FORMATOS_PERMITIDOS_FOTO.values() for e in exts})},
        )


class FotoDemasiadoGrande(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "foto_demasiado_grande",
            f"La fotografía no puede superar {TAMANO_MAXIMO_FOTO_BYTES // (1024 * 1024)}MB.",
        )


# RF-EQ-01 — "manual de usuario (archivo)", validación "tipo de archivo
# permitido... manual (PDF)". Mismo límite que el informe de mantenimiento
# (Sprint 8), un tipo de documento comparable.
FORMATOS_PERMITIDOS_MANUAL: dict[str, tuple[str, ...]] = {"pdf": ("application/pdf",)}
TAMANO_MAXIMO_MANUAL_BYTES = 20 * 1024 * 1024


class FormatoManualNoSoportado(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "formato_manual_no_soportado",
            "El manual de usuario debe ser un archivo PDF.",
            {"formatos_permitidos": ["pdf"]},
        )


class ManualDemasiadoGrande(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "manual_demasiado_grande",
            f"El manual no puede superar {TAMANO_MAXIMO_MANUAL_BYTES // (1024 * 1024)}MB.",
        )


@dataclass
class DatosEquipo:
    codigo_interno: str
    nombre: str
    estado_operativo: str = "operativo"
    categoria_id: uuid.UUID | None = None
    area_id: uuid.UUID | None = None
    responsable_id: uuid.UUID | None = None
    marca: str | None = None
    modelo: str | None = None
    numero_serie: str | None = None
    fabricante: str | None = None
    proveedor: str | None = None
    fecha_adquisicion: date | None = None
    observaciones: str | None = None
    foto_object_key: str | None = None
    manual_object_key: str | None = None
    # Fase 2 de hojas de vida (docs/25-...md sección 2).
    proveedor_id: uuid.UUID | None = None
    fabricante_id: uuid.UUID | None = None
    capitulo: str | None = None
    grupo: str | None = None
    subgrupo: str | None = None
    ubicacion: str | None = None
    numero_inventario: str | None = None
    condicion_fisica: str | None = None
    clasificacion_riesgo: str | None = None
    criticidad: str | None = None
    forma_adquisicion: str | None = None
    garantia: bool | None = None
    garantia_inicio: date | None = None
    garantia_fin: date | None = None


@dataclass
class ActorContexto:
    """Quién y desde dónde — para auditoría. Deliberadamente ajeno a
    FastAPI/JWT: la capa de aplicación no debe conocer esos detalles
    (docs/13-arquitectura.md sección 2)."""

    usuario_id: uuid.UUID | None
    ip_origen: str | None


class EquipoNoEncontrado(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("equipo_no_encontrado", "El equipo no existe.")


class CodigoInternoDuplicado(ConflictoDeNegocio):
    def __init__(self, codigo_interno: str) -> None:
        super().__init__(
            "codigo_interno_duplicado",
            f"Ya existe un equipo con el código '{codigo_interno}' en este laboratorio.",
            {"campo": "codigo_interno"},
        )


class NoPuedeActivarseConCalibracionVencida(ConflictoDeNegocio):
    def __init__(self) -> None:
        super().__init__(
            "calibracion_vencida_bloquea_activacion",
            "No se puede pasar el equipo a 'Operativo': su categoría exige una calibración "
            "vigente y la última registrada está vencida.",
        )


class ProveedorInvalido(ErrorDeDominio):
    """Postgres evalúa las FK sin pasar por RLS — sin esta validación en el
    servicio, un `proveedor_id` de otro laboratorio solo fallaría con una
    violación de FK (500), no con un error de dominio legible."""

    def __init__(self) -> None:
        super().__init__(
            "proveedor_invalido",
            "El proveedor seleccionado no existe en este laboratorio.",
            {"campo": "proveedor_id"},
        )


class FabricanteInvalido(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "fabricante_invalido",
            "El fabricante seleccionado no existe en este laboratorio.",
            {"campo": "fabricante_id"},
        )


def _a_dict_auditable(equipo: Equipo) -> dict:
    datos = asdict(equipo)
    # laboratorio_id/id no aportan valor en un diff de auditoría legible.
    datos.pop("laboratorio_id", None)
    datos.pop("id", None)
    return datos


class EquipoService:
    def __init__(
        self,
        equipos: EquipoRepository,
        auditoria: AuditoriaRepository,
        proveedores: ProveedorRepositorySQLAlchemy,
        fabricantes: FabricanteRepositorySQLAlchemy,
        ficha_tecnica: FichaTecnicaRepositorySQLAlchemy,
        almacenamiento_fotos: AlmacenamientoPort | None = None,
        almacenamiento_manuales: AlmacenamientoPort | None = None,
    ) -> None:
        self._equipos = equipos
        self._auditoria = auditoria
        # Fase 2 de hojas de vida — para validar proveedor_id/fabricante_id
        # bajo RLS (sección "Aislamiento entre laboratorios en las FK" del
        # diseño) y para que `duplicar()` pueda copiar ficha técnica/
        # manuales (RN-EQ-04 extendida, ver `duplicar()` más abajo).
        self._proveedores = proveedores
        self._fabricantes = fabricantes
        self._ficha_tecnica = ficha_tecnica
        # Opcional: la mayoría de casos de uso (listar, duplicar, historial)
        # no necesitan tocar MinIO — mismo criterio que `QrService.auditoria`.
        # Dos instancias porque foto y manual viven en buckets distintos
        # (un tipo de contenido lógico por bucket, ver `core/config.py`).
        self._almacenamiento_fotos = almacenamiento_fotos
        self._almacenamiento_manuales = almacenamiento_manuales

    def solicitar_url_foto(self, nombre_archivo: str, tipo_mime: str, tamano_bytes: int) -> tuple[str, str]:
        assert self._almacenamiento_fotos is not None
        extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
        mimes_validos = FORMATOS_PERMITIDOS_FOTO.get(extension)
        if mimes_validos is None or tipo_mime not in mimes_validos:
            raise FormatoFotoNoSoportado()
        if tamano_bytes > TAMANO_MAXIMO_FOTO_BYTES:
            raise FotoDemasiadoGrande()
        object_key = f"{uuid.uuid4()}.{extension}"
        url = self._almacenamiento_fotos.url_subida(object_key, tipo_mime)
        return url, object_key

    def url_foto(self, equipo: Equipo) -> str | None:
        if equipo.foto_object_key is None or self._almacenamiento_fotos is None:
            return None
        return self._almacenamiento_fotos.url_vista_previa(equipo.foto_object_key)

    def solicitar_url_manual(self, nombre_archivo: str, tipo_mime: str, tamano_bytes: int) -> tuple[str, str]:
        assert self._almacenamiento_manuales is not None
        extension = nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""
        mimes_validos = FORMATOS_PERMITIDOS_MANUAL.get(extension)
        if mimes_validos is None or tipo_mime not in mimes_validos:
            raise FormatoManualNoSoportado()
        if tamano_bytes > TAMANO_MAXIMO_MANUAL_BYTES:
            raise ManualDemasiadoGrande()
        object_key = f"{uuid.uuid4()}.{extension}"
        url = self._almacenamiento_manuales.url_subida(object_key, tipo_mime)
        return url, object_key

    def url_manual(self, equipo: Equipo) -> str | None:
        """Descarga (disposición attachment), no vista previa — es un
        documento de referencia, no una imagen para mostrar inline (mismo
        criterio que `MantenimientoService.url_informe`)."""
        if equipo.manual_object_key is None or self._almacenamiento_manuales is None:
            return None
        return self._almacenamiento_manuales.url_descarga(
            equipo.manual_object_key, f"manual-{equipo.codigo_interno}.pdf"
        )

    def crear(self, laboratorio_id: uuid.UUID, datos: DatosEquipo, actor: ActorContexto) -> Equipo:
        self._validar_estado(datos.estado_operativo)
        self._validar_ficha_tecnica(datos)
        self._validar_proveedor_y_fabricante(datos)
        if self._equipos.existe_codigo(datos.codigo_interno):
            raise CodigoInternoDuplicado(datos.codigo_interno)  # RN-EQ-02

        equipo = self._equipos.crear(self._nuevo_equipo(laboratorio_id, datos))

        self._auditoria.registrar(
            laboratorio_id=laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="crear",
            entidad_tipo="equipo",
            entidad_id=equipo.id,
            valor_anterior=None,
            valor_nuevo=_a_dict_auditable(equipo),
        )
        return equipo

    def obtener(self, equipo_id: uuid.UUID) -> Equipo:
        equipo = self._equipos.obtener_por_id(equipo_id)
        if equipo is None or not equipo.esta_activo():
            raise EquipoNoEncontrado()
        return equipo

    def listar(self, filtros: FiltrosEquipo) -> PaginaEquipos:
        return self._equipos.listar(filtros)

    def actualizar(self, equipo_id: uuid.UUID, datos: DatosEquipo, actor: ActorContexto) -> Equipo:
        self._validar_estado(datos.estado_operativo)
        self._validar_ficha_tecnica(datos)
        self._validar_proveedor_y_fabricante(datos)
        actual = self._equipos.obtener_por_id(equipo_id)
        if actual is None or not actual.esta_activo():
            raise EquipoNoEncontrado()

        if datos.estado_operativo == "operativo" and self._equipos.tiene_calibracion_vencida_bloqueante(
            equipo_id
        ):
            raise NoPuedeActivarseConCalibracionVencida()  # RN-EQ-03

        if datos.codigo_interno != actual.codigo_interno and self._equipos.existe_codigo(
            datos.codigo_interno, excluir_id=equipo_id
        ):
            raise CodigoInternoDuplicado(datos.codigo_interno)

        actualizado = Equipo(
            id=actual.id,
            laboratorio_id=actual.laboratorio_id,
            codigo_interno=datos.codigo_interno,
            nombre=datos.nombre,
            estado_operativo=datos.estado_operativo,
            categoria_id=datos.categoria_id,
            area_id=datos.area_id,
            responsable_id=datos.responsable_id,
            marca=datos.marca,
            modelo=datos.modelo,
            numero_serie=datos.numero_serie,
            fabricante=datos.fabricante,
            proveedor=datos.proveedor,
            fecha_adquisicion=datos.fecha_adquisicion,
            observaciones=datos.observaciones,
            foto_object_key=datos.foto_object_key,
            manual_object_key=datos.manual_object_key,
            proveedor_id=datos.proveedor_id,
            fabricante_id=datos.fabricante_id,
            capitulo=datos.capitulo,
            grupo=datos.grupo,
            subgrupo=datos.subgrupo,
            ubicacion=datos.ubicacion,
            numero_inventario=datos.numero_inventario,
            condicion_fisica=datos.condicion_fisica,
            clasificacion_riesgo=datos.clasificacion_riesgo,
            criticidad=datos.criticidad,
            forma_adquisicion=datos.forma_adquisicion,
            garantia=datos.garantia,
            garantia_inicio=datos.garantia_inicio,
            garantia_fin=datos.garantia_fin,
            eliminado_en=actual.eliminado_en,
            creado_en=actual.creado_en,
            actualizado_en=datetime.utcnow(),
        )
        guardado = self._equipos.actualizar(actualizado)

        self._auditoria.registrar(
            laboratorio_id=actual.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="actualizar",
            entidad_tipo="equipo",
            entidad_id=equipo_id,
            valor_anterior=_a_dict_auditable(actual),
            valor_nuevo=_a_dict_auditable(guardado),
        )
        return guardado

    def eliminar(self, equipo_id: uuid.UUID, actor: ActorContexto) -> None:
        actual = self._equipos.obtener_por_id(equipo_id)
        if actual is None or not actual.esta_activo():
            raise EquipoNoEncontrado()
        self._equipos.eliminar(equipo_id)  # soft delete — RN-EQ-01

        self._auditoria.registrar(
            laboratorio_id=actual.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="eliminar",
            entidad_tipo="equipo",
            entidad_id=equipo_id,
            valor_anterior=_a_dict_auditable(actual),
            valor_nuevo=None,
        )

    def duplicar(self, equipo_id: uuid.UUID, actor: ActorContexto) -> Equipo:
        """RF-EQ-05. RN-EQ-04: copia solo la ficha técnica, nunca el
        historial (calibraciones/mantenimientos) del original.

        RN-EQ-04 extendida (Fase 2 de hojas de vida — docs/25-...md no cubre
        `duplicar()`, criterio acordado con Gustavo): se copia lo que
        describe el MODELO del equipo (igual que `marca`/`fabricante`/
        `manual_object_key`, ya copiados antes de esta fase): los campos de
        clasificación, `proveedor_id`/`fabricante_id`, la ficha técnica
        extendida y los manuales. No se copia lo específico de la UNIDAD
        FÍSICA original: `numero_inventario`/`garantia*` (mismo criterio que
        `fecha_adquisicion`, ya excluida) ni los accesorios (mismo criterio
        que la fotografía — los accesorios físicos de una unidad no son los
        de su copia).

        `manual_object_key` y el `object_key` de cada `equipo_manuales`
        quedan COMPARTIDOS entre el original y la copia (no se duplica el
        objeto en MinIO: verificado que ningún flujo de este módulo llama
        `AlmacenamientoPort.eliminar_objeto()` — ni el soft delete de
        `eliminar()` ni un reemplazo por PATCH lo tocan). Si en el futuro se
        agrega un flujo que SÍ borre ese objeto, debe primero verificar que
        ninguna otra fila (de `equipos` o de `equipo_manuales`) todavía lo
        referencie, o copiar el objeto en vez de compartir la referencia.
        """
        original = self._equipos.obtener_por_id(equipo_id)
        if original is None or not original.esta_activo():
            raise EquipoNoEncontrado()

        nuevo_codigo = self._generar_codigo_copia(original.codigo_interno)
        datos = DatosEquipo(
            codigo_interno=nuevo_codigo,
            nombre=f"{original.nombre} (copia)",
            estado_operativo="operativo",
            categoria_id=original.categoria_id,
            area_id=original.area_id,
            responsable_id=original.responsable_id,
            marca=original.marca,
            modelo=original.modelo,
            numero_serie=None,  # el n° de serie es único por unidad física
            fabricante=original.fabricante,
            proveedor=original.proveedor,
            fecha_adquisicion=None,
            observaciones=original.observaciones,
            # La fotografía es de la unidad física original, no de la copia
            # — mismo criterio que `numero_serie` (RN-EQ-04).
            foto_object_key=None,
            # El manual SÍ se copia, a diferencia de la foto: describe el
            # modelo/tipo de equipo, no una unidad física específica — es
            # tan válido para la copia como para el original (RN-EQ-04 solo
            # excluye historial, no campos de ficha técnica como este).
            # Comparte `object_key` con el original — ver nota de MinIO en
            # el docstring de este método.
            manual_object_key=original.manual_object_key,
            proveedor_id=original.proveedor_id,
            fabricante_id=original.fabricante_id,
            capitulo=original.capitulo,
            grupo=original.grupo,
            subgrupo=original.subgrupo,
            ubicacion=original.ubicacion,
            numero_inventario=None,  # específico de la unidad física original
            condicion_fisica=original.condicion_fisica,
            clasificacion_riesgo=original.clasificacion_riesgo,
            criticidad=original.criticidad,
            forma_adquisicion=original.forma_adquisicion,
            garantia=None,  # específico de la unidad física original
            garantia_inicio=None,
            garantia_fin=None,
        )
        copia = self.crear(original.laboratorio_id, datos, actor)

        ficha_original = self._ficha_tecnica.obtener_ficha_tecnica(equipo_id)
        if ficha_original is not None:
            campos = asdict(ficha_original)
            campos.pop("equipo_id", None)
            campos.pop("creado_en", None)
            campos.pop("actualizado_en", None)
            self._ficha_tecnica.guardar_ficha_tecnica(original.laboratorio_id, copia.id, campos)

        for manual in self._ficha_tecnica.listar_manuales(equipo_id):
            # Comparte `object_key` con el original — ver nota de MinIO en
            # el docstring de este método.
            self._ficha_tecnica.guardar_manual(
                original.laboratorio_id,
                copia.id,
                manual.tipo,
                manual.disponible,
                manual.idioma,
                manual.object_key,
            )

        return copia

    def historial(self, equipo_id: uuid.UUID) -> list[LogAuditoria]:
        """RF-EQ-09. A diferencia de `obtener()`, no exige que el equipo esté
        activo — el historial debe seguir siendo visible tras un soft delete
        (RN-EQ-01). El RLS de la sesión ya garantiza el aislamiento por
        tenant en `obtener_por_id`."""
        if self._equipos.obtener_por_id(equipo_id) is None:
            raise EquipoNoEncontrado()
        return self._auditoria.listar_por_entidad("equipo", equipo_id)

    def _generar_codigo_copia(self, codigo_original: str) -> str:
        base = f"{codigo_original}-COPIA"
        candidato = base
        sufijo = 2
        while self._equipos.existe_codigo(candidato):
            candidato = f"{base}-{sufijo}"
            sufijo += 1
        return candidato

    @staticmethod
    def _nuevo_equipo(laboratorio_id: uuid.UUID, datos: DatosEquipo) -> Equipo:
        ahora = datetime.utcnow()
        return Equipo(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            codigo_interno=datos.codigo_interno,
            nombre=datos.nombre,
            estado_operativo=datos.estado_operativo,
            categoria_id=datos.categoria_id,
            area_id=datos.area_id,
            responsable_id=datos.responsable_id,
            marca=datos.marca,
            modelo=datos.modelo,
            numero_serie=datos.numero_serie,
            fabricante=datos.fabricante,
            proveedor=datos.proveedor,
            fecha_adquisicion=datos.fecha_adquisicion,
            observaciones=datos.observaciones,
            foto_object_key=datos.foto_object_key,
            manual_object_key=datos.manual_object_key,
            proveedor_id=datos.proveedor_id,
            fabricante_id=datos.fabricante_id,
            capitulo=datos.capitulo,
            grupo=datos.grupo,
            subgrupo=datos.subgrupo,
            ubicacion=datos.ubicacion,
            numero_inventario=datos.numero_inventario,
            condicion_fisica=datos.condicion_fisica,
            clasificacion_riesgo=datos.clasificacion_riesgo,
            criticidad=datos.criticidad,
            forma_adquisicion=datos.forma_adquisicion,
            garantia=datos.garantia,
            garantia_inicio=datos.garantia_inicio,
            garantia_fin=datos.garantia_fin,
            eliminado_en=None,
            creado_en=ahora,
            actualizado_en=ahora,
        )

    @staticmethod
    def _validar_estado(estado: str) -> None:
        if estado not in ESTADOS_OPERATIVOS:
            raise ErrorDeDominio(
                "estado_operativo_invalido",
                f"'{estado}' no es un estado operativo válido.",
                {"valores_permitidos": list(ESTADOS_OPERATIVOS)},
            )

    @staticmethod
    def _validar_dominio_opcional(valor: str | None, dominio: tuple[str, ...], campo: str) -> None:
        if valor is not None and valor not in dominio:
            raise ErrorDeDominio(
                f"{campo}_invalido",
                f"'{valor}' no es un valor válido para '{campo}'.",
                {"campo": campo, "valores_permitidos": list(dominio)},
            )

    @classmethod
    def _validar_ficha_tecnica(cls, datos: DatosEquipo) -> None:
        # Fase 2 de hojas de vida — ningún campo técnico es obligatorio
        # (docs/24-...md sección 3.8), pero si se envía un valor debe estar
        # dentro del dominio cerrado que ya refuerza el CHECK de la BD
        # (migración 0019) — mismo criterio que `_validar_estado`.
        cls._validar_dominio_opcional(datos.condicion_fisica, CONDICIONES_FISICAS, "condicion_fisica")
        cls._validar_dominio_opcional(
            datos.clasificacion_riesgo, CLASIFICACIONES_RIESGO, "clasificacion_riesgo"
        )
        cls._validar_dominio_opcional(datos.criticidad, CRITICIDADES, "criticidad")
        cls._validar_dominio_opcional(datos.forma_adquisicion, FORMAS_ADQUISICION, "forma_adquisicion")
        if (
            datos.garantia_inicio is not None
            and datos.garantia_fin is not None
            and datos.garantia_fin < datos.garantia_inicio
        ):
            raise ErrorDeDominio(
                "garantia_fechas_invalidas",
                "La fecha de fin de garantía no puede ser anterior a la de inicio.",
                {"campo": "garantia_fin"},
            )

    def _validar_proveedor_y_fabricante(self, datos: DatosEquipo) -> None:
        # Aislamiento multi-tenant en la FK: la FK compuesta de la base de
        # datos (migración 0018) ya lo impide, pero sin esta validación una
        # referencia de otro laboratorio fallaría con una violación de FK
        # (500), no con un error de dominio legible. `obtener_por_id` busca
        # bajo RLS — una fila de otro laboratorio nunca aparece.
        if datos.proveedor_id is not None and self._proveedores.obtener_por_id(datos.proveedor_id) is None:
            raise ProveedorInvalido()
        if datos.fabricante_id is not None and self._fabricantes.obtener_por_id(datos.fabricante_id) is None:
            raise FabricanteInvalido()
