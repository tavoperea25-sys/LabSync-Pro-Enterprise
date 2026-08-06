"""Entidades del módulo Calibraciones. Ver docs/14-base-de-datos.md y
docs/03-requerimientos-funcionales.md (RF-CAL-01 a RF-CAL-07 — Sprint 7)."""

from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

RESULTADOS_CALIBRACION = ("conforme", "no_conforme")

SEMAFOROS = ("verde", "amarillo", "rojo", "gris")

# RN-CAL-01 — umbral preventivo por defecto, usado cuando el laboratorio no
# configuró uno propio (`configuraciones_laboratorio.umbral_alerta_calibracion_dias`,
# módulo Configuración, Sprint 12). `semaforo()` sigue siendo una función
# pura — quien la llama es responsable de resolver el umbral configurado y
# pasarlo explícitamente, nunca esta función va a la base de datos.
UMBRAL_ALERTA_CALIBRACION_DIAS = 30

# RF-CAL-06 — solo PDF, a diferencia del Gestor Documental (RF-DOC-02) que
# acepta formatos variados; un certificado de calibración es siempre PDF.
FORMATOS_PERMITIDOS_CERTIFICADO: dict[str, tuple[str, ...]] = {"pdf": ("application/pdf",)}
TAMANO_MAXIMO_CERTIFICADO_BYTES = 20 * 1024 * 1024  # 20 MB


def calcular_proxima_fecha(fecha_calibracion: date, frecuencia_meses: int) -> date:
    """RN-CAL-03 — fecha_calibracion + frecuencia_meses, con día clamp al
    último día del mes destino si este tiene menos días (ej. 31 ene + 1 mes
    -> 28/29 feb, nunca "marzo 3" por desborde silencioso)."""
    mes_total = fecha_calibracion.month - 1 + frecuencia_meses
    anio = fecha_calibracion.year + mes_total // 12
    mes = mes_total % 12 + 1
    ultimo_dia_mes = calendar.monthrange(anio, mes)[1]
    dia = min(fecha_calibracion.day, ultimo_dia_mes)
    return date(anio, mes, dia)


def semaforo(proxima_fecha: date | None, hoy: date, umbral_dias: int = UMBRAL_ALERTA_CALIBRACION_DIAS) -> str:
    """RN-CAL-01. "gris" es responsabilidad del llamador cuando el equipo
    no tiene ninguna calibración — aquí basta con `proxima_fecha is None`
    para cubrir ese caso sin duplicar la regla en cada consumidor."""
    if proxima_fecha is None:
        return "gris"
    dias_restantes = (proxima_fecha - hoy).days
    if dias_restantes < 0:
        return "rojo"
    if dias_restantes <= umbral_dias:
        return "amarillo"
    return "verde"


@dataclass
class Calibracion:
    id: uuid.UUID
    laboratorio_id: uuid.UUID
    equipo_id: uuid.UUID
    fecha_calibracion: date
    frecuencia_meses: int
    proxima_fecha: date
    laboratorio_proveedor: str | None
    numero_certificado: str | None
    resultado: str
    incertidumbre: Decimal | None
    responsable_id: uuid.UUID | None
    certificado_adjunto_id: uuid.UUID | None
    corrige_a_id: uuid.UUID | None
    motivo_correccion: str | None
    observaciones: str | None
    creado_en: datetime


@dataclass
class EquipoConSemaforo:
    """RF-CAL-05 — una fila del listado de críticos."""

    equipo_id: uuid.UUID
    equipo_nombre: str
    equipo_codigo_interno: str
    ultima_calibracion_id: uuid.UUID | None
    proxima_fecha: date | None
    dias_restantes: int | None
    semaforo: str
