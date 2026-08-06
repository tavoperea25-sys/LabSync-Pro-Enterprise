"""Casos de uso del módulo Documentos. Ver docs/03-requerimientos-funcionales.md
(RF-DOC-01 a RF-DOC-14 — Sprints 5-6) y docs/07-reglas-de-negocio.md (RN-DOC-*).

Máquina de estados (Sprint 6): tanto `crear_documento` como
`subir_nueva_version` dejan el documento en "en_revision" — nunca "vigente"
directo. Solo `aprobar()` transiciona a "vigente" (RF-DOC-12/14). `estado`
en el modelo de datos se mantiene fiel a los 3 valores declarados en
docs/14-base-de-datos.md (vigente/obsoleto/en_revision); un rechazo NO
introduce un 4° valor — permanece en "en_revision" para corrección, y el
motivo queda auditado (ver `ultimo_rechazo`), reutilizando la bitácora
genérica en vez de añadir una columna nueva solo para esto.

"Recientes" se define como los documentos con actividad más reciente
(creación o nueva versión); no existe una tabla de "vistos por usuario" en
el esquema, así que no se inventa ese seguimiento — ver docs/14-base-de-datos.md.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime

from app.core.errors import ConflictoDeNegocio, ErrorDeDominio, RecursoNoEncontrado
from app.modules.auditoria.domain.entities import LogAuditoria
from app.modules.auditoria.domain.ports import AuditoriaRepository
from app.modules.configuracion.domain.entities import DIAS_RETENCION_PAPELERA_DOCUMENTOS_DEFAULT
from app.modules.configuracion.domain.ports import ConfiguracionRepository
from app.modules.documentos.domain.entities import (
    FORMATOS_CON_PREVISUALIZACION,
    FORMATOS_PERMITIDOS,
    TAMANO_MAXIMO_BYTES,
    Carpeta,
    Documento,
    Etiqueta,
    VersionDocumento,
)
from app.modules.documentos.domain.ports import (
    AlmacenamientoPort,
    CarpetaRepository,
    DocumentoRepository,
    EtiquetaRepository,
    FiltrosDocumento,
    PaginaDocumentos,
    VersionDocumentoRepository,
)

_MODULO = "documentos"


@dataclass
class ActorContexto:
    usuario_id: uuid.UUID | None
    ip_origen: str | None


class DocumentoNoEncontrado(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("documento_no_encontrado", "El documento no existe.")


class PapeleraVentanaExpirada(ConflictoDeNegocio):
    def __init__(self, dias_retencion: int) -> None:
        super().__init__(
            "papelera_ventana_expirada",
            f"No se puede restaurar: superó la ventana de retención de {dias_retencion} días "
            "en la papelera (RN-DOC-03).",
        )


class CarpetaNoEncontrada(RecursoNoEncontrado):
    def __init__(self) -> None:
        super().__init__("carpeta_no_encontrada", "La carpeta no existe.")


class FormatoNoPermitido(ErrorDeDominio):
    def __init__(self, extension: str) -> None:
        super().__init__(
            "formato_no_permitido",
            f"El formato '.{extension}' no está permitido (RF-DOC-02).",
            {"formatos_permitidos": sorted(FORMATOS_PERMITIDOS)},
        )


class ArchivoDemasiadoGrande(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "archivo_demasiado_grande",
            f"El archivo supera el límite de {TAMANO_MAXIMO_BYTES // (1024 * 1024)} MB.",
        )


class NombreDeCarpetaDuplicado(ConflictoDeNegocio):
    def __init__(self, nombre: str) -> None:
        super().__init__(
            "nombre_carpeta_duplicado",
            f"Ya existe una carpeta llamada '{nombre}' en esta ubicación.",
            {"campo": "nombre"},
        )


class CarpetaNoVacia(ConflictoDeNegocio):
    def __init__(self) -> None:
        super().__init__(
            "carpeta_no_vacia", "La carpeta contiene documentos o subcarpetas; no se puede eliminar."
        )


class DocumentoNoEnRevision(ConflictoDeNegocio):
    def __init__(self) -> None:
        super().__init__(
            "documento_no_en_revision",
            "Solo se pueden aprobar o rechazar documentos en estado 'en revisión'.",
        )


def _extension(nombre_archivo: str) -> str:
    return nombre_archivo.rsplit(".", 1)[-1].lower() if "." in nombre_archivo else ""


def _validar_formato(nombre_archivo: str, tipo_mime: str) -> None:
    extension = _extension(nombre_archivo)
    mimes_validos = FORMATOS_PERMITIDOS.get(extension)
    if mimes_validos is None or tipo_mime not in mimes_validos:
        raise FormatoNoPermitido(extension or "?")


class DocumentoService:
    def __init__(
        self,
        documentos: DocumentoRepository,
        versiones: VersionDocumentoRepository,
        carpetas: CarpetaRepository,
        etiquetas: EtiquetaRepository,
        auditoria: AuditoriaRepository,
        almacenamiento: AlmacenamientoPort,
        configuraciones: ConfiguracionRepository,
    ) -> None:
        self._documentos = documentos
        self._versiones = versiones
        self._carpetas = carpetas
        self._etiquetas = etiquetas
        self._auditoria = auditoria
        self._almacenamiento = almacenamiento
        self._configuraciones = configuraciones

    # ---- Subida ---------------------------------------------------------

    def solicitar_url_subida(
        self, laboratorio_id: uuid.UUID, nombre_archivo: str, tipo_mime: str, tamano_bytes: int
    ) -> tuple[str, str]:
        """RF-DOC-01/02. Retorna (url_subida, object_key); el frontend hace
        el PUT directo a MinIO con esa URL — el backend nunca ve los bytes."""
        _validar_formato(nombre_archivo, tipo_mime)
        if tamano_bytes > TAMANO_MAXIMO_BYTES:
            raise ArchivoDemasiadoGrande()
        object_key = f"{laboratorio_id}/{uuid.uuid4()}/{nombre_archivo}"
        url = self._almacenamiento.url_subida(object_key, tipo_mime)
        return url, object_key

    def crear_documento(
        self,
        laboratorio_id: uuid.UUID,
        actor: ActorContexto,
        *,
        nombre: str,
        carpeta_id: uuid.UUID | None,
        categoria: str | None,
        fecha_emision: date | None,
        fecha_vencimiento: date | None,
        object_key: str,
        nombre_archivo: str,
        tamano_bytes: int,
        tipo_mime: str,
    ) -> Documento:
        """RF-DOC-01/11 — confirma una subida ya hecha a MinIO y crea el
        documento lógico junto con su primera versión. Queda "en_revision"
        (RF-DOC-12): solo `aprobar()` lo deja vigente."""
        self._validar_fechas(fecha_emision, fecha_vencimiento)
        if carpeta_id is not None and self._carpetas.obtener_por_id(carpeta_id) is None:
            raise CarpetaNoEncontrada()

        ahora = datetime.utcnow()
        documento = self._documentos.crear(
            Documento(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio_id,
                carpeta_id=carpeta_id,
                nombre=nombre,
                categoria=categoria,
                estado="en_revision",
                fecha_emision=fecha_emision,
                fecha_vencimiento=fecha_vencimiento,
                responsable_aprobacion_id=None,
                version_vigente_id=None,
                eliminado_en=None,
                creado_en=ahora,
                actualizado_en=ahora,
            )
        )
        version = self._crear_version(
            documento.id, actor, object_key, nombre_archivo, tamano_bytes, tipo_mime
        )
        documento = self._documentos.actualizar(replace(documento, version_vigente_id=version.id))

        self._auditoria.registrar(
            laboratorio_id=laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="crear",
            entidad_tipo="documento",
            entidad_id=documento.id,
            valor_anterior=None,
            valor_nuevo={"nombre": documento.nombre, "version": version.numero_version},
        )
        return documento

    def subir_nueva_version(
        self,
        documento_id: uuid.UUID,
        actor: ActorContexto,
        *,
        object_key: str,
        nombre_archivo: str,
        tamano_bytes: int,
        tipo_mime: str,
    ) -> VersionDocumento:
        """RF-DOC-11. Una versión nueva siempre vuelve a poner el documento
        "en_revision" (RN-DOC-02) — incluso si la anterior ya estaba
        vigente, no puede quedar una versión sin revisar mostrándose como
        vigente por inercia."""
        documento = self.obtener(documento_id)
        version = self._crear_version(
            documento.id, actor, object_key, nombre_archivo, tamano_bytes, tipo_mime
        )
        self._documentos.actualizar(
            replace(documento, version_vigente_id=version.id, estado="en_revision")
        )

        self._auditoria.registrar(
            laboratorio_id=documento.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="nueva_version",
            entidad_tipo="documento",
            entidad_id=documento.id,
            valor_anterior=None,
            valor_nuevo={"version": version.numero_version},
        )
        return version

    def _crear_version(
        self,
        documento_id: uuid.UUID,
        actor: ActorContexto,
        object_key: str,
        nombre_archivo: str,
        tamano_bytes: int,
        tipo_mime: str,
    ) -> VersionDocumento:
        _validar_formato(nombre_archivo, tipo_mime)
        numero = self._versiones.siguiente_numero_version(documento_id)
        return self._versiones.crear(
            VersionDocumento(
                id=uuid.uuid4(),
                documento_id=documento_id,
                numero_version=numero,
                object_key=object_key,
                nombre_archivo=nombre_archivo,
                tamano_bytes=tamano_bytes,
                tipo_mime=tipo_mime,
                subido_por_id=actor.usuario_id,
                aprobado_por_id=None,
                aprobado_en=None,
                creado_en=datetime.utcnow(),
            )
        )

    # ---- Lectura ----------------------------------------------------

    def obtener(self, documento_id: uuid.UUID) -> Documento:
        documento = self._documentos.obtener_por_id(documento_id)
        if documento is None or not documento.esta_activo():
            raise DocumentoNoEncontrado()
        return documento

    def listar(self, laboratorio_id: uuid.UUID, filtros: FiltrosDocumento) -> PaginaDocumentos:
        return self._documentos.listar(laboratorio_id, filtros)

    def listar_recientes(self, laboratorio_id: uuid.UUID, limite: int = 10) -> list[Documento]:
        return self._documentos.listar_recientes(laboratorio_id, limite)

    def listar_papelera(self, laboratorio_id: uuid.UUID) -> list[Documento]:
        return self._documentos.listar_papelera(laboratorio_id)

    def versiones(self, documento_id: uuid.UUID) -> list[VersionDocumento]:
        self.obtener(documento_id)
        return self._versiones.listar_por_documento(documento_id)

    def etiquetas_de(self, documento_id: uuid.UUID) -> list[Etiqueta]:
        return self._etiquetas.listar_por_documento(documento_id)

    def url_descarga(self, documento_id: uuid.UUID, numero_version: int | None = None) -> str:
        """RF-DOC-08."""
        documento = self.obtener(documento_id)
        version = self._version_o_vigente(documento, numero_version)
        return self._almacenamiento.url_descarga(
            version.object_key, version.nombre_archivo, version.tipo_mime
        )

    def url_vista_previa(self, documento_id: uuid.UUID) -> tuple[str | None, VersionDocumento]:
        """RF-DOC-07 — None si el formato no tiene previsualización nativa;
        el frontend muestra metadatos en ese caso en vez de un visor roto."""
        documento = self.obtener(documento_id)
        version = self._version_o_vigente(documento, None)
        if _extension(version.nombre_archivo) not in FORMATOS_CON_PREVISUALIZACION:
            return None, version
        return self._almacenamiento.url_vista_previa(version.object_key, version.tipo_mime), version

    def _version_o_vigente(self, documento: Documento, numero_version: int | None) -> VersionDocumento:
        if numero_version is not None:
            version = self._versiones.obtener(documento.id, numero_version)
            if version is None:
                raise DocumentoNoEncontrado()
            return version
        versiones = self._versiones.listar_por_documento(documento.id)
        if not versiones:
            raise DocumentoNoEncontrado()
        return versiones[0]  # listar_por_documento ordena descendente por número

    # ---- Edición ------------------------------------------------------

    def renombrar(self, documento_id: uuid.UUID, nuevo_nombre: str, actor: ActorContexto) -> Documento:
        documento = self.obtener(documento_id)
        guardado = self._documentos.actualizar(replace(documento, nombre=nuevo_nombre))
        self._auditoria.registrar(
            laboratorio_id=documento.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="renombrar",
            entidad_tipo="documento",
            entidad_id=documento_id,
            valor_anterior={"nombre": documento.nombre},
            valor_nuevo={"nombre": nuevo_nombre},
        )
        return guardado

    def mover(self, documento_id: uuid.UUID, carpeta_id: uuid.UUID | None, actor: ActorContexto) -> Documento:
        documento = self.obtener(documento_id)
        if carpeta_id is not None and self._carpetas.obtener_por_id(carpeta_id) is None:
            raise CarpetaNoEncontrada()
        guardado = self._documentos.actualizar(replace(documento, carpeta_id=carpeta_id))
        self._auditoria.registrar(
            laboratorio_id=documento.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="mover",
            entidad_tipo="documento",
            entidad_id=documento_id,
            valor_anterior={"carpeta_id": str(documento.carpeta_id) if documento.carpeta_id else None},
            valor_nuevo={"carpeta_id": str(carpeta_id) if carpeta_id else None},
        )
        return guardado

    def copiar(self, documento_id: uuid.UUID, actor: ActorContexto) -> Documento:
        """RF-DOC-09 — copia server-side en MinIO (copy_object); el backend
        nunca vuelve a subir bytes que nunca vio."""
        original = self.obtener(documento_id)
        version_original = self._version_o_vigente(original, None)

        nuevo_id = uuid.uuid4()
        nueva_key = f"{original.laboratorio_id}/{nuevo_id}/{version_original.nombre_archivo}"
        self._almacenamiento.copiar_objeto(version_original.object_key, nueva_key)

        ahora = datetime.utcnow()
        copia = self._documentos.crear(
            Documento(
                id=nuevo_id,
                laboratorio_id=original.laboratorio_id,
                carpeta_id=original.carpeta_id,
                nombre=f"{original.nombre} (copia)",
                categoria=original.categoria,
                estado="en_revision",
                fecha_emision=None,
                fecha_vencimiento=None,
                responsable_aprobacion_id=None,
                version_vigente_id=None,
                eliminado_en=None,
                creado_en=ahora,
                actualizado_en=ahora,
            )
        )
        version = self._crear_version(
            copia.id,
            actor,
            nueva_key,
            version_original.nombre_archivo,
            version_original.tamano_bytes,
            version_original.tipo_mime,
        )
        copia = self._documentos.actualizar(replace(copia, version_vigente_id=version.id))

        self._auditoria.registrar(
            laboratorio_id=original.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="copiar",
            entidad_tipo="documento",
            entidad_id=copia.id,
            valor_anterior=None,
            valor_nuevo={"origen_id": str(documento_id)},
        )
        return copia

    # ---- Aprobación (RF-DOC-12 a 14, RN-DOC-02) ------------------------

    def aprobar(self, documento_id: uuid.UUID, actor: ActorContexto) -> Documento:
        """HU-DT-02. Solo se aprueba la versión vigente actual (la última
        subida) — nunca coexisten dos versiones "vigentes" porque solo hay
        un `version_vigente_id` por documento (RN-DOC-02)."""
        documento = self.obtener(documento_id)
        if documento.estado != "en_revision":
            raise DocumentoNoEnRevision()

        version = self._version_o_vigente(documento, None)
        self._versiones.marcar_aprobada(version.id, actor.usuario_id)
        guardado = self._documentos.actualizar(
            replace(documento, estado="vigente", responsable_aprobacion_id=actor.usuario_id)
        )

        self._auditoria.registrar(
            laboratorio_id=documento.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="aprobar",
            entidad_tipo="documento",
            entidad_id=documento_id,
            valor_anterior=None,
            valor_nuevo={"version": version.numero_version},
        )
        return guardado

    def rechazar(self, documento_id: uuid.UUID, actor: ActorContexto, comentario: str) -> Documento:
        """HU-DT-02. Permanece "en_revision" para que Calidad corrija y
        vuelva a subir — el motivo queda en la bitácora de auditoría
        (`ultimo_rechazo`) en vez de sumar un 4° valor de estado no
        contemplado en docs/14-base-de-datos.md."""
        documento = self.obtener(documento_id)
        if documento.estado != "en_revision":
            raise DocumentoNoEnRevision()

        self._auditoria.registrar(
            laboratorio_id=documento.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="rechazar",
            entidad_tipo="documento",
            entidad_id=documento_id,
            valor_anterior=None,
            valor_nuevo={"comentario": comentario},
        )
        return documento

    def ultimo_rechazo(self, documento_id: uuid.UUID) -> LogAuditoria | None:
        """None si el evento más reciente del documento no es un rechazo
        (ya se aprobó, o se subió una versión nueva desde entonces)."""
        entradas = self._auditoria.listar_por_entidad("documento", documento_id)
        if entradas and entradas[0].accion == "rechazar":
            return entradas[0]
        return None

    def actualizar_metadatos(
        self,
        documento_id: uuid.UUID,
        actor: ActorContexto,
        *,
        categoria: str | None,
        fecha_emision: date | None,
        fecha_vencimiento: date | None,
    ) -> Documento:
        """RF-DOC-12."""
        documento = self.obtener(documento_id)
        self._validar_fechas(fecha_emision, fecha_vencimiento)
        guardado = self._documentos.actualizar(
            replace(
                documento,
                categoria=categoria,
                fecha_emision=fecha_emision,
                fecha_vencimiento=fecha_vencimiento,
            )
        )
        self._auditoria.registrar(
            laboratorio_id=documento.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="actualizar_metadatos",
            entidad_tipo="documento",
            entidad_id=documento_id,
            valor_anterior={
                "categoria": documento.categoria,
                "fecha_emision": documento.fecha_emision.isoformat() if documento.fecha_emision else None,
                "fecha_vencimiento": documento.fecha_vencimiento.isoformat()
                if documento.fecha_vencimiento
                else None,
            },
            valor_nuevo={
                "categoria": categoria,
                "fecha_emision": fecha_emision.isoformat() if fecha_emision else None,
                "fecha_vencimiento": fecha_vencimiento.isoformat() if fecha_vencimiento else None,
            },
        )
        return guardado

    # ---- Papelera -----------------------------------------------------

    def enviar_a_papelera(self, documento_id: uuid.UUID, actor: ActorContexto) -> None:
        documento = self.obtener(documento_id)
        self._documentos.eliminar(documento_id)
        self._auditoria.registrar(
            laboratorio_id=documento.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="eliminar",
            entidad_tipo="documento",
            entidad_id=documento_id,
            valor_anterior={"nombre": documento.nombre},
            valor_nuevo=None,
        )

    def restaurar(self, documento_id: uuid.UUID, actor: ActorContexto) -> None:
        documento = self._documentos.obtener_por_id(documento_id)
        if documento is None or documento.esta_activo():
            raise DocumentoNoEncontrado()

        dias_retencion = self._dias_retencion_papelera(documento.laboratorio_id)
        assert documento.eliminado_en is not None  # ya validado por esta_activo() arriba
        # `eliminado_en` viene de una columna TIMESTAMPTZ (tz-aware); restar
        # contra `datetime.utcnow()` (naive) revienta con TypeError — mismo
        # criterio ya establecido en `auth_service.py` para comparaciones
        # contra columnas con huso horario.
        dias_en_papelera = (datetime.now(UTC) - documento.eliminado_en).days
        if dias_en_papelera > dias_retencion:
            raise PapeleraVentanaExpirada(dias_retencion)  # RN-DOC-03

        self._documentos.restaurar(documento_id)
        self._auditoria.registrar(
            laboratorio_id=documento.laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="restaurar",
            entidad_tipo="documento",
            entidad_id=documento_id,
            valor_anterior=None,
            valor_nuevo={"nombre": documento.nombre},
        )

    def _dias_retencion_papelera(self, laboratorio_id: uuid.UUID) -> int:
        config = self._configuraciones.obtener(laboratorio_id)
        return (
            config.dias_retencion_papelera_documentos
            if config
            else DIAS_RETENCION_PAPELERA_DOCUMENTOS_DEFAULT
        )

    def purgar_papelera_vencida(self, laboratorio_id: uuid.UUID) -> int:
        """RN-DOC-03 — barrido periódico (worker): elimina físicamente los
        documentos cuya ventana de restauración ya venció, incluidos sus
        binarios en MinIO. A diferencia de `enviar_a_papelera` (soft delete,
        reversible), esto es irreversible y no pasa por `ActorContexto` — no
        hay un usuario detrás, es una acción programada del sistema, mismo
        criterio que `EvaluadorAlertasService`. Retorna cuántos documentos
        se purgaron, para que el worker lo loguee."""
        expirados = self._documentos.listar_papelera_expirada(
            laboratorio_id, self._dias_retencion_papelera(laboratorio_id)
        )
        for documento in expirados:
            object_keys = self._documentos.purgar(documento.id)
            for object_key in object_keys:
                self._almacenamiento.eliminar_objeto(object_key)
            self._auditoria.registrar(
                laboratorio_id=laboratorio_id,
                usuario_id=None,
                ip_origen=None,
                modulo=_MODULO,
                accion="purgar",
                entidad_tipo="documento",
                entidad_id=documento.id,
                valor_anterior={"nombre": documento.nombre, "eliminado_en": str(documento.eliminado_en)},
                valor_nuevo=None,
            )
        return len(expirados)

    # ---- Favoritos --------------------------------------------------

    def alternar_favorito(self, documento_id: uuid.UUID, usuario_id: uuid.UUID) -> bool:
        self.obtener(documento_id)
        return self._documentos.alternar_favorito(documento_id, usuario_id)

    # ---- Etiquetas ----------------------------------------------------

    def listar_etiquetas(self, laboratorio_id: uuid.UUID) -> list[Etiqueta]:
        return self._etiquetas.listar(laboratorio_id)

    def asignar_etiqueta(
        self, documento_id: uuid.UUID, laboratorio_id: uuid.UUID, nombre_etiqueta: str
    ) -> Etiqueta:
        self.obtener(documento_id)
        etiqueta = self._etiquetas.obtener_o_crear(laboratorio_id, nombre_etiqueta)
        self._etiquetas.asignar(documento_id, etiqueta.id)
        return etiqueta

    def quitar_etiqueta(self, documento_id: uuid.UUID, etiqueta_id: uuid.UUID) -> None:
        self._etiquetas.quitar(documento_id, etiqueta_id)

    # ---- Carpetas -------------------------------------------------------

    def listar_carpetas(self, laboratorio_id: uuid.UUID, carpeta_padre_id: uuid.UUID | None) -> list[Carpeta]:
        return self._carpetas.listar(laboratorio_id, carpeta_padre_id)

    def crear_carpeta(
        self, laboratorio_id: uuid.UUID, nombre: str, carpeta_padre_id: uuid.UUID | None
    ) -> Carpeta:
        if carpeta_padre_id is not None and self._carpetas.obtener_por_id(carpeta_padre_id) is None:
            raise CarpetaNoEncontrada()
        if self._carpetas.existe_nombre(laboratorio_id, carpeta_padre_id, nombre):
            raise NombreDeCarpetaDuplicado(nombre)
        return self._carpetas.crear(
            Carpeta(
                id=uuid.uuid4(),
                laboratorio_id=laboratorio_id,
                nombre=nombre,
                carpeta_padre_id=carpeta_padre_id,
                creado_en=datetime.utcnow(),
            )
        )

    def renombrar_carpeta(self, carpeta_id: uuid.UUID, nuevo_nombre: str) -> Carpeta:
        carpeta = self._carpetas.obtener_por_id(carpeta_id)
        if carpeta is None:
            raise CarpetaNoEncontrada()
        if self._carpetas.existe_nombre(
            carpeta.laboratorio_id, carpeta.carpeta_padre_id, nuevo_nombre, excluir_id=carpeta_id
        ):
            raise NombreDeCarpetaDuplicado(nuevo_nombre)
        return self._carpetas.actualizar(replace(carpeta, nombre=nuevo_nombre))

    def eliminar_carpeta(self, carpeta_id: uuid.UUID) -> None:
        carpeta = self._carpetas.obtener_por_id(carpeta_id)
        if carpeta is None:
            raise CarpetaNoEncontrada()
        if self._carpetas.tiene_contenido(carpeta_id):
            raise CarpetaNoVacia()
        self._carpetas.eliminar(carpeta_id)

    @staticmethod
    def _validar_fechas(fecha_emision: date | None, fecha_vencimiento: date | None) -> None:
        if fecha_emision and fecha_vencimiento and fecha_vencimiento <= fecha_emision:
            raise ErrorDeDominio(
                "fecha_vencimiento_invalida",
                "La fecha de vencimiento debe ser posterior a la fecha de emisión.",
                {"campo": "fecha_vencimiento"},
            )
