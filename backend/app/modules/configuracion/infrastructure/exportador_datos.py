"""Exportación/portabilidad de datos del tenant — Sprint 13,
docs/17-roadmap.md Fase 5 ("Exportación de datos del tenant").

Un CSV por entidad dentro de un único ZIP — mismo criterio de simplicidad
que `reportes/infrastructure/exportadores.py` (Sprint 11): proyecciones
explícitas (encabezados + filas de texto) en vez de volcar los dataclasses
por reflexión, precisamente para poder EXCLUIR a propósito los campos
sensibles (`Usuario.password_hash`, contadores de intentos de login) que
nunca deben salir en un archivo descargable, ni siquiera para el propio
Administrador del laboratorio.

Síncrono, no vía el patrón async de Reportes (RNF-PERF-04): esta operación
es infrecuente (no es un reporte operativo del día a día) y el volumen de
datos de UN tenant es acotado — se documenta como decisión de alcance
deliberada, no un descuido; si en el futuro un tenant muy grande lo
requiere, se puede migrar al mismo patrón de job asíncrono."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime
from typing import Any

Proyeccion = tuple[list[str], list[list[str]]]


def _texto(valor: object) -> str:
    return "" if valor is None else str(valor)


def _csv_bytes(proyeccion: Proyeccion) -> bytes:
    encabezados, filas = proyeccion
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(encabezados)
    escritor.writerows(filas)
    return buffer.getvalue().encode("utf-8-sig")


def proyectar_equipos(equipos: list[Any]) -> Proyeccion:
    encabezados = [
        "id",
        "codigo_interno",
        "nombre",
        "estado_operativo",
        "categoria_id",
        "area_id",
        "marca",
        "modelo",
        "numero_serie",
        "fabricante",
        "proveedor",
        "fecha_adquisicion",
        "creado_en",
    ]
    filas = [
        [
            _texto(e.id),
            e.codigo_interno,
            e.nombre,
            e.estado_operativo,
            _texto(e.categoria_id),
            _texto(e.area_id),
            _texto(e.marca),
            _texto(e.modelo),
            _texto(e.numero_serie),
            _texto(e.fabricante),
            _texto(e.proveedor),
            _texto(e.fecha_adquisicion),
            _texto(e.creado_en),
        ]
        for e in equipos
    ]
    return encabezados, filas


def proyectar_documentos(documentos: list[Any]) -> Proyeccion:
    encabezados = ["id", "nombre", "categoria", "estado", "fecha_emision", "fecha_vencimiento", "creado_en"]
    filas = [
        [
            _texto(d.id),
            d.nombre,
            _texto(d.categoria),
            d.estado,
            _texto(d.fecha_emision),
            _texto(d.fecha_vencimiento),
            _texto(d.creado_en),
        ]
        for d in documentos
    ]
    return encabezados, filas


def proyectar_calibraciones(calibraciones: list[Any]) -> Proyeccion:
    encabezados = [
        "id",
        "equipo_id",
        "fecha_calibracion",
        "frecuencia_meses",
        "proxima_fecha",
        "laboratorio_proveedor",
        "numero_certificado",
        "resultado",
        "creado_en",
    ]
    filas = [
        [
            _texto(c.id),
            _texto(c.equipo_id),
            _texto(c.fecha_calibracion),
            _texto(c.frecuencia_meses),
            _texto(c.proxima_fecha),
            _texto(c.laboratorio_proveedor),
            _texto(c.numero_certificado),
            c.resultado,
            _texto(c.creado_en),
        ]
        for c in calibraciones
    ]
    return encabezados, filas


def proyectar_mantenimientos(mantenimientos: list[Any]) -> Proyeccion:
    encabezados = [
        "id",
        "equipo_id",
        "tipo",
        "estado",
        "fecha_programada",
        "fecha_ejecutada",
        "descripcion",
        "creado_en",
    ]
    filas = [
        [
            _texto(m.id),
            _texto(m.equipo_id),
            m.tipo,
            m.estado,
            _texto(m.fecha_programada),
            _texto(m.fecha_ejecutada),
            _texto(m.descripcion),
            _texto(m.creado_en),
        ]
        for m in mantenimientos
    ]
    return encabezados, filas


def proyectar_usuarios(usuarios: list[Any]) -> Proyeccion:
    # A propósito NO incluye password_hash, intentos_fallidos ni
    # bloqueado_hasta — son datos operativos de seguridad, no datos del
    # tenant que le pertenezcan para portabilidad.
    encabezados = ["id", "nombre_completo", "correo", "estado", "roles"]
    filas = [[_texto(u.id), u.nombre_completo, u.correo, u.estado, ";".join(u.roles)] for u in usuarios]
    return encabezados, filas


def proyectar_categorias(categorias: list[Any]) -> Proyeccion:
    encabezados = ["id", "nombre", "frecuencia_calibracion_default_meses"]
    filas = [[_texto(c.id), c.nombre, _texto(c.frecuencia_calibracion_default_meses)] for c in categorias]
    return encabezados, filas


def proyectar_areas(areas: list[Any]) -> Proyeccion:
    encabezados = ["id", "nombre"]
    filas = [[_texto(a.id), a.nombre] for a in areas]
    return encabezados, filas


def generar_zip_exportacion(datos_por_entidad: dict[str, Proyeccion], generado_en: datetime) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for nombre_entidad, proyeccion in datos_por_entidad.items():
            zf.writestr(f"{nombre_entidad}.csv", _csv_bytes(proyeccion))
        zf.writestr(
            "README.txt",
            "Exportación de datos de LabSync Pro Enterprise.\n"
            f"Generado el {generado_en.strftime('%Y-%m-%d %H:%M:%S UTC')}.\n\n"
            "No incluye archivos binarios (documentos, certificados, evidencias) ni "
            "credenciales de usuario — solo metadatos en formato CSV (UTF-8).\n",
        )
    return buffer.getvalue()
