"""Exportación de la bitácora de auditoría filtrada — RF-AUD-03.

A diferencia de la exportación de Equipos (Sprint 4), aquí SÍ se construye
PDF ahora: HU-ADMIN-03 lo pide explícitamente para este sprint ("cuando
exporto a PDF, conserva los mismos filtros y una marca de fecha de
generación"), a diferencia de RF-EQ-08 que solo pedía Excel. Es un PDF
tabular funcional, no la plantilla corporativa con marca del laboratorio
que sí queda para el módulo Reportes (Sprint 11, docs/17-roadmap.md)."""

from __future__ import annotations

import csv
import io
from datetime import datetime

from fpdf import FPDF
from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet

from app.modules.auditoria.domain.entities import LogAuditoria

_ENCABEZADOS = ["Fecha", "Usuario", "IP", "Módulo", "Acción", "Entidad", "ID de entidad"]


def _fila(log: LogAuditoria) -> list[str]:
    return [
        log.creado_en.strftime("%Y-%m-%d %H:%M:%S"),
        str(log.usuario_id) if log.usuario_id else "sistema",
        log.ip_origen or "",
        log.modulo,
        log.accion,
        log.entidad_tipo,
        str(log.entidad_id) if log.entidad_id else "",
    ]


def generar_csv(logs: list[LogAuditoria]) -> bytes:
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(_ENCABEZADOS)
    for log in logs:
        escritor.writerow(_fila(log))
    return buffer.getvalue().encode("utf-8-sig")  # BOM — Excel abre UTF-8 correctamente con acentos


def generar_excel(logs: list[LogAuditoria]) -> bytes:
    libro = Workbook()
    hoja: Worksheet = libro.active
    hoja.title = "Auditoría"

    hoja.append(_ENCABEZADOS)
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    for log in logs:
        hoja.append(_fila(log))

    for columna in hoja.columns:
        ancho = max((len(str(c.value)) for c in columna if c.value), default=10)
        hoja.column_dimensions[columna[0].column_letter].width = min(ancho + 2, 40)

    buffer = io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def generar_pdf(logs: list[LogAuditoria], generado_en: datetime) -> bytes:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, "Bitácora de auditoría", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(
        0, 6, f"Generado el {generado_en.strftime('%Y-%m-%d %H:%M:%S UTC')}", new_x="LMARGIN", new_y="NEXT"
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)

    anchos = [32, 55, 30, 30, 30, 35, 55]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(230, 230, 230)
    for encabezado, ancho in zip(_ENCABEZADOS, anchos, strict=True):
        pdf.cell(ancho, 7, encabezado, border=1, fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 7.5)
    for log in logs:
        for valor, ancho in zip(_fila(log), anchos, strict=True):
            pdf.cell(ancho, 6, valor[:60], border=1)
        pdf.ln()

    salida = pdf.output()
    return bytes(salida)
