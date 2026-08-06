"""Adaptador de almacenamiento sobre MinIO. Ver docs/13-arquitectura.md
sección 5 — subida y descarga siempre vía URLs prefirmadas; el backend
nunca transporta el binario del archivo.

Compartido entre módulos (Documentos, Calibraciones y, más adelante,
Mantenimientos) — cada uno instancia con su propio bucket lógico
("documentos" vs "evidencias"), ver core/config.py."""

from __future__ import annotations

import io
from datetime import timedelta

from minio import Minio
from minio.commonconfig import CopySource
from minio.sseconfig import Rule, SSEConfig

from app.core.config import get_settings

_DURACION_SUBIDA = timedelta(minutes=15)
_DURACION_DESCARGA = timedelta(minutes=10)


def _cliente(endpoint: str) -> Minio:
    settings = get_settings()
    return Minio(
        endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        # Sin esto, minio-py resuelve la región con una llamada de red real
        # (GetBucketLocation) la primera vez que firma una URL — no es la
        # operación "solo criptografía local" que parece. Para el cliente
        # `_publico` esa llamada es imposible por diseño (su host es el que
        # el NAVEGADOR debe resolver, no necesariamente el backend), así que
        # se fija la región por adelantado. "us-east-1" es la región por
        # defecto de MinIO cuando no se configura MINIO_REGION explícitamente
        # (no es el caso aquí, ver docker-compose.yml).
        region="us-east-1",
    )


class AlmacenamientoMinIO:
    def __init__(self, bucket: str) -> None:
        settings = get_settings()
        self._bucket = bucket
        # Cliente interno: tráfico servidor-a-servidor real (crear el
        # bucket, copy_object). Cliente público: solo firma URLs de forma
        # local (no hace peticiones de red) — el host firmado debe ser el
        # que el navegador puede resolver, ver core/config.py.
        self._interno = _cliente(settings.minio_endpoint_interno)
        self._publico = _cliente(settings.minio_endpoint_publico)

    def asegurar_bucket(self) -> None:
        if not self._interno.bucket_exists(self._bucket):
            self._interno.make_bucket(self._bucket)
        # docs/16-seguridad.md sección 5 — "Documentos en MinIO cifrados en
        # reposo (SSE)": cifrado por defecto a nivel de bucket (SSE-S3, clave
        # gestionada por el KMS del propio servidor MinIO, ver
        # MINIO_KMS_SECRET_KEY en docker-compose.yml). Al vivir a nivel de
        # bucket y no de request, cifra por igual las subidas server-to-server
        # (`subir_bytes`) y las subidas del navegador vía URL prefirmada
        # (`url_subida`) sin tocar ninguno de los dos flujos — MinIO aplica el
        # cifrado del lado del servidor sin que el emisor de la subida haga
        # nada distinto. Se reconfigura en cada arranque (idempotente:
        # sobrescribe con el mismo valor si ya estaba activo).
        self._interno.set_bucket_encryption(self._bucket, SSEConfig(Rule.new_sse_s3_rule()))

    def url_subida(self, object_key: str, tipo_mime: str) -> str:
        return self._publico.presigned_put_object(self._bucket, object_key, expires=_DURACION_SUBIDA)

    def url_descarga(self, object_key: str, nombre_descarga: str, tipo_mime: str | None = None) -> str:
        # `tipo_mime` opcional — IMP-03 (RC1): si se provee, fuerza el
        # Content-Type de la respuesta al valor validado por la aplicación en
        # vez del que MinIO tenga almacenado para el objeto (que puede no
        # coincidir con lo declarado en la subida, ver
        # docs/24-auditoria-independiente-2026-08-05.md CRIT-3). Sin este
        # argumento el comportamiento es idéntico al anterior — hoy solo lo
        # usa el módulo Documentos, que es el único que persiste un
        # `tipo_mime` validado por versión.
        headers: dict[str, str | list[str] | tuple[str]] = {
            "response-content-disposition": f'attachment; filename="{nombre_descarga}"'
        }
        if tipo_mime is not None:
            headers["response-content-type"] = tipo_mime
        return self._publico.presigned_get_object(
            self._bucket,
            object_key,
            expires=_DURACION_DESCARGA,
            response_headers=headers,
        )

    def url_vista_previa(self, object_key: str, tipo_mime: str | None = None) -> str:
        # Ver nota de `url_descarga` — mismo criterio.
        headers: dict[str, str | list[str] | tuple[str]] = {"response-content-disposition": "inline"}
        if tipo_mime is not None:
            headers["response-content-type"] = tipo_mime
        return self._publico.presigned_get_object(
            self._bucket,
            object_key,
            expires=_DURACION_DESCARGA,
            response_headers=headers,
        )

    def copiar_objeto(self, origen_key: str, destino_key: str) -> None:
        self._interno.copy_object(self._bucket, destino_key, CopySource(self._bucket, origen_key))

    def subir_bytes(self, object_key: str, contenido: bytes, tipo_mime: str) -> None:
        """Único caso server-to-server real (el resto del proyecto sube
        siempre vía URL prefirmada desde el navegador, ver docs/13
        sección 5) — el worker genera el archivo del reporte async en
        memoria y lo sube él mismo, no hay cliente al que devolverle una
        URL de subida (Sprint 11, RNF-PERF-04)."""
        self._interno.put_object(
            self._bucket, object_key, io.BytesIO(contenido), length=len(contenido), content_type=tipo_mime
        )

    def eliminar_objeto(self, object_key: str) -> None:
        """RN-DOC-03 — purga de la papelera de documentos vencida: a
        diferencia del resto del ciclo de vida (siempre soft delete, ver
        `documentos/application/documento_service.py`), esta es la única
        eliminación física del binario en todo el proyecto."""
        self._interno.remove_object(self._bucket, object_key)

    def descargar_bytes(self, object_key: str) -> bytes:
        """Segundo caso server-to-server real: el generador de PDF de
        Reportes necesita los bytes del logo institucional para embeberlo
        en el encabezado — no hay navegador de por medio al que devolverle
        una URL (Sprint 14, RF-CFG-04)."""
        respuesta = self._interno.get_object(self._bucket, object_key)
        try:
            return respuesta.read()
        finally:
            respuesta.close()
            respuesta.release_conn()
