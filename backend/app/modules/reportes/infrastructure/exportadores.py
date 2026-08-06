"""Exportación de reportes a PDF/Excel/CSV — RF-REP-08.

Mismo criterio que `auditoria/infrastructure/exportador.py` (Sprint 10):
PDF tabular funcional con marca de fecha de generación. El logo
institucional en el encabezado (RF-CFG-04) se embebe cuando el llamador
pasa `logo_bytes` — la resolución de "¿este laboratorio tiene logo?" vive
en `reporte_service.py`/el worker, no aquí (este módulo no sabe de
`configuraciones_laboratorio` ni de MinIO, solo recibe bytes ya
resueltos). Un único renderizador genérico por formato, alimentado por
"proyecciones" (encabezados + filas de texto) que cada tipo de reporte
arma a partir de sus propios dataclasses — evita 21 funciones de
exportación casi idénticas para 7 tipos × 3 formatos."""

from __future__ import annotations

import csv
import io
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet

from app.modules.calibraciones.domain.entities import EquipoConSemaforo
from app.modules.documentos.domain.entities import Documento
from app.modules.mantenimientos.domain.entities import Mantenimiento
from app.modules.reportes.application.generadores import (
    FilaCumplimientoMensual,
    FilaInventario,
    FilaVencido,
    PaqueteAuditoria,
)

Proyeccion = tuple[list[str], list[list[str]]]

_logger = logging.getLogger(__name__)


def _texto(valor: object) -> str:
    if valor is None:
        return ""
    return str(valor)


# La fuente core "Helvetica" de fpdf2 solo soporta Latin-1 — cualquier dato
# de USUARIO (nombre de equipo, descripción de mantenimiento, etc.) que
# contenga una raya "—", comillas tipográficas u otro carácter fuera de ese
# rango revienta `pdf.cell()` con FPDFUnicodeEncodingException (encontrado
# en pruebas, Sprint 11) — no es hipotético, ya pasó con datos reales de
# sprints anteriores. Este saneo se aplica SOLO en el camino de PDF; Excel y
# CSV manejan Unicode completo y no deben perder esos caracteres.
_REEMPLAZOS_PDF = {
    "—": "-",  # —
    "–": "-",  # –
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
}


def _texto_pdf(valor: str) -> str:
    for buscado, reemplazo in _REEMPLAZOS_PDF.items():
        valor = valor.replace(buscado, reemplazo)
    # Red de seguridad final para cualquier otro carácter no previsto — se
    # sustituye en vez de reventar la generación completa del PDF.
    return valor.encode("latin-1", errors="replace").decode("latin-1")


# ---- Proyecciones: dataclass tipado -> (encabezados, filas de texto) -------


def proyectar_inventario(filas: list[FilaInventario]) -> Proyeccion:
    encabezados = ["Código", "Nombre", "Categoría", "Área", "Estado", "Marca", "Modelo", "N° de serie"]
    return encabezados, [
        [
            f.codigo_interno,
            f.nombre,
            _texto(f.categoria),
            _texto(f.area),
            f.estado_operativo,
            _texto(f.marca),
            _texto(f.modelo),
            _texto(f.numero_serie),
        ]
        for f in filas
    ]


def proyectar_calibraciones(filas: list[EquipoConSemaforo]) -> Proyeccion:
    encabezados = ["Código", "Equipo", "Próxima calibración", "Días restantes", "Estado"]
    return encabezados, [
        [
            f.equipo_codigo_interno,
            f.equipo_nombre,
            _texto(f.proxima_fecha),
            _texto(f.dias_restantes),
            f.semaforo,
        ]
        for f in filas
    ]


def proyectar_vencidos(filas: list[FilaVencido]) -> Proyeccion:
    encabezados = ["Código", "Equipo", "Motivo", "Detalle", "Vencido desde"]
    return encabezados, [
        [f.equipo_codigo, f.equipo_nombre, f.motivo, f.detalle, _texto(f.vencido_desde)] for f in filas
    ]


def proyectar_cumplimiento(filas: list[FilaCumplimientoMensual]) -> Proyeccion:
    encabezados = [
        "Mes",
        "Total equipos",
        "Vigentes",
        "Próximos a vencer",
        "Vencidos",
        "Sin información",
        "% Cumplimiento",
    ]
    return encabezados, [
        [
            f.mes.strftime("%Y-%m"),
            str(f.total_equipos),
            str(f.vigentes),
            str(f.proximos_a_vencer),
            str(f.vencidos),
            str(f.sin_informacion),
            f"{f.porcentaje_cumplimiento}%",
        ]
        for f in filas
    ]


def proyectar_mantenimiento(filas: list[Mantenimiento]) -> Proyeccion:
    encabezados = ["Tipo", "Estado", "Programado", "Ejecutado", "Descripción", "Costo"]
    return encabezados, [
        [
            m.tipo,
            m.estado,
            _texto(m.fecha_programada),
            _texto(m.fecha_ejecutada),
            _texto(m.descripcion),
            _texto(m.costo),
        ]
        for m in filas
    ]


def proyectar_trazabilidad_documental(filas: list[Documento]) -> Proyeccion:
    encabezados = ["Nombre", "Categoría", "Estado", "Emisión", "Vencimiento"]
    return encabezados, [
        [d.nombre, _texto(d.categoria), d.estado, _texto(d.fecha_emision), _texto(d.fecha_vencimiento)]
        for d in filas
    ]


_TITULOS: dict[str, str] = {
    "inventario": "Inventario de equipos",
    "calibraciones": "Estado de calibraciones",
    "vencidos": "Equipos vencidos",
    "cumplimiento": "Indicadores de cumplimiento (histórico mensual)",
    "mantenimiento": "Historial de mantenimiento",
    "trazabilidad_documental": "Trazabilidad documental",
}


# ---- Renderizadores genéricos por formato -----------------------------------


def _agregar_logo_encabezado(pdf: FPDF, logo_bytes: bytes | None) -> None:
    """Esquina superior derecha, en posición absoluta — no interfiere con
    el flujo normal de texto (título/fecha), que sigue ligado al margen
    izquierdo vía `new_x="LMARGIN"`. Un logo que no se puede decodificar
    (formato inesperado, bytes corruptos) no debe tumbar la generación
    completa del reporte — se omite y se registra."""
    if not logo_bytes:
        return
    try:
        alto = 14.0
        pdf.image(io.BytesIO(logo_bytes), x=pdf.w - pdf.r_margin - 30, y=8, h=alto)
    except Exception:
        _logger.warning("No se pudo embeber el logo institucional en el PDF.", exc_info=True)


def _pdf_tabular(
    titulo: str,
    encabezados: list[str],
    filas: list[list[str]],
    generado_en: datetime,
    logo_bytes: bytes | None = None,
) -> bytes:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    _agregar_logo_encabezado(pdf, logo_bytes)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, _texto_pdf(titulo), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    texto_fecha = f"Generado el {generado_en.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    pdf.cell(0, 6, _texto_pdf(texto_fecha), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    ancho_disponible = 277
    ancho_columna = ancho_disponible / max(len(encabezados), 1)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    for encabezado in encabezados:
        pdf.cell(ancho_columna, 7, _texto_pdf(encabezado), border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 7.5)
    for fila in filas:
        for valor in fila:
            pdf.cell(ancho_columna, 6, _texto_pdf(valor[:50]), border=1)
        pdf.ln()

    return bytes(pdf.output())


def _excel_tabular(titulo: str, encabezados: list[str], filas: list[list[str]]) -> bytes:
    libro = Workbook()
    hoja: Worksheet = libro.active
    hoja.title = titulo[:31]  # límite de Excel para nombres de hoja

    hoja.append(encabezados)
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    for fila in filas:
        hoja.append(fila)

    for columna in hoja.columns:
        ancho = max((len(str(c.value)) for c in columna if c.value), default=10)
        hoja.column_dimensions[columna[0].column_letter].width = min(ancho + 2, 40)

    buffer = io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def _csv_tabular(encabezados: list[str], filas: list[list[str]]) -> bytes:
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(encabezados)
    escritor.writerows(filas)
    return buffer.getvalue().encode("utf-8-sig")


_PROYECTORES: dict[str, Callable[[list[Any]], Proyeccion]] = {
    "inventario": proyectar_inventario,
    "calibraciones": proyectar_calibraciones,
    "vencidos": proyectar_vencidos,
    "cumplimiento": proyectar_cumplimiento,
    "mantenimiento": proyectar_mantenimiento,
    "trazabilidad_documental": proyectar_trazabilidad_documental,
}


def exportar_reporte_tabular(
    tipo: str, formato: str, datos: list[Any], generado_en: datetime, logo_bytes: bytes | None = None
) -> bytes:
    """Despachador usado tanto por el flujo síncrono (router) como por el
    worker (flujo asíncrono, RNF-PERF-04) — la misma función produce el
    mismo archivo sin importar quién la invoque. `logo_bytes` se ignora en
    Excel/CSV (RF-CFG-04 es solo para el encabezado del PDF)."""
    encabezados, filas = _PROYECTORES[tipo](datos)
    if formato == "pdf":
        return _pdf_tabular(_TITULOS[tipo], encabezados, filas, generado_en, logo_bytes)
    if formato == "xlsx":
        return _excel_tabular(_TITULOS[tipo], encabezados, filas)
    if formato == "csv":
        return _csv_tabular(encabezados, filas)
    raise ValueError(f"Formato no soportado: {formato}")


# ---- RF-REP-07 — Paquete de auditoría (multi-sección, solo PDF) -----------


def _seccion(pdf: FPDF, titulo: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(15, 81, 50)  # verde institucional
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, _texto_pdf(titulo), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def _tabla_seccion(pdf: FPDF, encabezados: list[str], filas: list[list[str]]) -> None:
    if not filas:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "Sin registros.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        return
    ancho = 190 / len(encabezados)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    for encabezado in encabezados:
        pdf.cell(ancho, 6, _texto_pdf(encabezado), border=1, fill=True)
    pdf.ln()
    pdf.set_font("Helvetica", "", 7.5)
    for fila in filas:
        for valor in fila:
            pdf.cell(ancho, 6, _texto_pdf(valor[:40]), border=1)
        pdf.ln()
    pdf.ln(3)


def generar_paquete_auditoria_pdf(paquete: PaqueteAuditoria, logo_bytes: bytes | None = None) -> bytes:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _agregar_logo_encabezado(pdf, logo_bytes)

    pdf.set_font("Helvetica", "B", 16)
    # Guion normal, no raya "—": la fuente Helvetica core de fpdf2 no
    # soporta ese carácter fuera de Latin-1 y revienta con
    # FPDFUnicodeEncodingException (ver Sprint 11, encontrado en pruebas).
    pdf.cell(0, 10, _texto_pdf("Paquete de auditoría - ISO 15189"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    texto_fecha = f"Generado el {paquete.generado_en.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    pdf.cell(0, 6, _texto_pdf(texto_fecha), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    _seccion(pdf, "Ficha del equipo")
    equipo = paquete.equipo
    pdf.set_font("Helvetica", "", 9)
    for etiqueta, valor in [
        ("Código interno", equipo.codigo_interno),
        ("Nombre", equipo.nombre),
        ("Estado operativo", equipo.estado_operativo),
        ("Marca", equipo.marca),
        ("Modelo", equipo.modelo),
        ("N° de serie", equipo.numero_serie),
    ]:
        pdf.cell(0, 6, _texto_pdf(f"{etiqueta}: {_texto(valor)}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    _seccion(pdf, "Calibraciones")
    _tabla_seccion(
        pdf,
        ["Fecha", "Próxima", "Resultado", "N° certificado"],
        [
            [_texto(c.fecha_calibracion), _texto(c.proxima_fecha), c.resultado, _texto(c.numero_certificado)]
            for c in paquete.calibraciones
        ],
    )

    _seccion(pdf, "Mantenimientos")
    _tabla_seccion(
        pdf,
        ["Tipo", "Estado", "Programado", "Ejecutado"],
        [
            [m.tipo, m.estado, _texto(m.fecha_programada), _texto(m.fecha_ejecutada)]
            for m in paquete.mantenimientos
        ],
    )

    _seccion(pdf, "Documentos vigentes del laboratorio")
    _tabla_seccion(
        pdf,
        ["Nombre", "Categoría", "Vencimiento"],
        [[d.nombre, _texto(d.categoria), _texto(d.fecha_vencimiento)] for d in paquete.documentos_vigentes],
    )

    return bytes(pdf.output())
