"""Exportación de Equipos a Excel — RF-EQ-08.

La exportación a PDF corporativo llega con el módulo Reportes (Sprint 11,
docs/17-roadmap.md), que reutiliza esta misma consulta con una plantilla de
marca — no se construye aquí una versión a medias."""

from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet

from app.modules.equipos.domain.entities import Equipo

_ENCABEZADOS = [
    "Código interno",
    "Nombre",
    "Estado operativo",
    "Marca",
    "Modelo",
    "N° de serie",
    "Fabricante",
    "Proveedor",
    "Fecha de adquisición",
]


def generar_excel(equipos: list[Equipo]) -> bytes:
    libro = Workbook()
    hoja: Worksheet = libro.active
    hoja.title = "Equipos"

    hoja.append(_ENCABEZADOS)
    for celda in hoja[1]:
        celda.font = Font(bold=True)

    for equipo in equipos:
        hoja.append(
            [
                equipo.codigo_interno,
                equipo.nombre,
                equipo.estado_operativo,
                equipo.marca,
                equipo.modelo,
                equipo.numero_serie,
                equipo.fabricante,
                equipo.proveedor,
                equipo.fecha_adquisicion.isoformat() if equipo.fecha_adquisicion else None,
            ]
        )

    for columna in hoja.columns:
        ancho = max((len(str(c.value)) for c in columna if c.value), default=10)
        hoja.column_dimensions[columna[0].column_letter].width = min(ancho + 2, 40)

    buffer = io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
