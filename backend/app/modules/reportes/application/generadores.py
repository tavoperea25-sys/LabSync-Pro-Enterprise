"""Generadores de datos de cada tipo de reporte — RF-REP-01 a 07.

Cada función devuelve filas ya listas para exportar (`infrastructure/
exportadores.py` las serializa a PDF/Excel/CSV/ZIP) — esta capa solo sabe
consultar y proyectar datos de negocio, nunca de formato de archivo."""

from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.core.errors import ErrorDeDominio, RecursoNoEncontrado
from app.modules.calibraciones.domain.entities import Calibracion, EquipoConSemaforo, calcular_proxima_fecha
from app.modules.calibraciones.domain.ports import CalibracionRepository
from app.modules.documentos.domain.entities import Documento
from app.modules.documentos.domain.ports import DocumentoRepository
from app.modules.equipos.domain.entities import Equipo
from app.modules.equipos.domain.ports import EquipoRepository, FiltrosEquipo
from app.modules.mantenimientos.domain.entities import Mantenimiento
from app.modules.mantenimientos.domain.ports import FiltrosMantenimiento, MantenimientoRepository

MESES_HISTORICO_CUMPLIMIENTO = 12


# ---- RF-REP-01 — Inventario de equipos --------------------------------------


@dataclass
class FilaInventario:
    codigo_interno: str
    nombre: str
    categoria: str | None
    area: str | None
    estado_operativo: str
    marca: str | None
    modelo: str | None
    numero_serie: str | None
    fecha_adquisicion: date | None


def generar_inventario(
    equipos: EquipoRepository,
    categorias_por_id: dict[uuid.UUID, str],
    areas_por_id: dict[uuid.UUID, str],
    categoria_id: uuid.UUID | None = None,
    area_id: uuid.UUID | None = None,
    estado_operativo: str | None = None,
) -> list[FilaInventario]:
    filas = equipos.listar_todos(
        FiltrosEquipo(categoria_id=categoria_id, area_id=area_id, estado_operativo=estado_operativo)
    )
    return [
        FilaInventario(
            codigo_interno=e.codigo_interno,
            nombre=e.nombre,
            categoria=categorias_por_id.get(e.categoria_id) if e.categoria_id else None,
            area=areas_por_id.get(e.area_id) if e.area_id else None,
            estado_operativo=e.estado_operativo,
            marca=e.marca,
            modelo=e.modelo,
            numero_serie=e.numero_serie,
            fecha_adquisicion=e.fecha_adquisicion,
        )
        for e in filas
    ]


# ---- RF-REP-02 — Estado de calibraciones ------------------------------------


def generar_calibraciones(
    calibraciones: CalibracionRepository, laboratorio_id: uuid.UUID
) -> list[EquipoConSemaforo]:
    filas = calibraciones.listar_estado_todos(laboratorio_id)
    orden = {"rojo": 0, "amarillo": 1, "gris": 2, "verde": 3}
    return sorted(filas, key=lambda f: (orden[f.semaforo], f.proxima_fecha or date.max))


# ---- RF-REP-03 — Equipos vencidos (calibración o mantenimiento) ------------


@dataclass
class FilaVencido:
    equipo_codigo: str
    equipo_nombre: str
    motivo: str  # "calibracion" | "mantenimiento"
    detalle: str
    vencido_desde: date


def generar_vencidos(
    calibraciones: CalibracionRepository,
    mantenimientos: MantenimientoRepository,
    equipos: EquipoRepository,
    laboratorio_id: uuid.UUID,
) -> list[FilaVencido]:
    filas: list[FilaVencido] = []

    for f in calibraciones.listar_estado_todos(laboratorio_id):
        if f.semaforo == "rojo" and f.proxima_fecha is not None:
            filas.append(
                FilaVencido(
                    equipo_codigo=f.equipo_codigo_interno,
                    equipo_nombre=f.equipo_nombre,
                    motivo="calibracion",
                    detalle=f"Calibración vencida ({abs(f.dias_restantes or 0)} días)",
                    vencido_desde=f.proxima_fecha,
                )
            )

    hoy = date.today()
    equipos_por_id: dict[uuid.UUID, Equipo] = {}
    for m in mantenimientos.listar_proximos(laboratorio_id, dias_umbral=0):
        if m.fecha_programada is None or m.fecha_programada >= hoy:
            continue
        if m.equipo_id not in equipos_por_id:
            encontrado = equipos.obtener_por_id(m.equipo_id)
            if encontrado is not None:
                equipos_por_id[m.equipo_id] = encontrado
        equipo = equipos_por_id.get(m.equipo_id)
        if equipo is None:
            continue
        filas.append(
            FilaVencido(
                equipo_codigo=equipo.codigo_interno,
                equipo_nombre=equipo.nombre,
                motivo="mantenimiento",
                detalle=f"Mantenimiento {m.tipo} programado sin ejecutar",
                vencido_desde=m.fecha_programada,
            )
        )

    return sorted(filas, key=lambda f: f.vencido_desde)


# ---- RF-REP-04 — Indicadores de cumplimiento (histórico mensual) -----------


@dataclass
class FilaCumplimientoMensual:
    mes: date  # primer día del mes, representa el período
    total_equipos: int
    vigentes: int
    proximos_a_vencer: int
    vencidos: int
    sin_informacion: int
    porcentaje_cumplimiento: Decimal


def _ultimo_dia_del_mes(fecha: date) -> date:
    return date(fecha.year, fecha.month, calendar.monthrange(fecha.year, fecha.month)[1])


def generar_cumplimiento(
    calibraciones: CalibracionRepository, laboratorio_id: uuid.UUID, meses: int = MESES_HISTORICO_CUMPLIMIENTO
) -> list[FilaCumplimientoMensual]:
    hoy = date.today()
    filas: list[FilaCumplimientoMensual] = []
    for i in range(meses - 1, -1, -1):
        # `calcular_proxima_fecha` con meses negativos retrocede — se
        # reutiliza en vez de añadir una dependencia solo para aritmética
        # de meses (Python maneja división/módulo negativos correctamente
        # ahí, ver docstring de la función original en Calibraciones).
        mes_de_referencia = calcular_proxima_fecha(hoy, -i)
        fin_de_mes = hoy if i == 0 else _ultimo_dia_del_mes(mes_de_referencia)
        estado = calibraciones.listar_estado_a_fecha(laboratorio_id, fin_de_mes)
        total = len(estado)
        vigentes = sum(1 for e in estado if e.semaforo == "verde")
        proximos = sum(1 for e in estado if e.semaforo == "amarillo")
        vencidos = sum(1 for e in estado if e.semaforo == "rojo")
        sin_info = sum(1 for e in estado if e.semaforo == "gris")
        cumplimiento = Decimal(vigentes + proximos) / Decimal(total) * 100 if total else Decimal(0)
        filas.append(
            FilaCumplimientoMensual(
                mes=fin_de_mes.replace(day=1),
                total_equipos=total,
                vigentes=vigentes,
                proximos_a_vencer=proximos,
                vencidos=vencidos,
                sin_informacion=sin_info,
                porcentaje_cumplimiento=cumplimiento.quantize(Decimal("0.1")),
            )
        )
    return filas


# ---- RF-REP-05 — Historial de mantenimiento ---------------------------------


def generar_mantenimiento(
    mantenimientos: MantenimientoRepository,
    laboratorio_id: uuid.UUID,
    equipo_id: uuid.UUID | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[Mantenimiento]:
    filtros = FiltrosMantenimiento(equipo_id=equipo_id, fecha_desde=desde, fecha_hasta=hasta)
    return mantenimientos.listar_todos(laboratorio_id, filtros)


# ---- RF-REP-06 — Trazabilidad documental ------------------------------------


def generar_trazabilidad_documental(
    documentos: DocumentoRepository, laboratorio_id: uuid.UUID
) -> list[Documento]:
    return documentos.listar_vigentes(laboratorio_id)


# ---- RF-REP-07 — Paquete de auditoría por equipo ----------------------------


@dataclass
class PaqueteAuditoria:
    equipo: Equipo
    calibraciones: list[Calibracion]
    mantenimientos: list[Mantenimiento]
    documentos_vigentes: list[Documento]
    generado_en: datetime


def generar_paquete_auditoria(
    equipos: EquipoRepository,
    calibraciones: CalibracionRepository,
    mantenimientos: MantenimientoRepository,
    documentos: DocumentoRepository,
    laboratorio_id: uuid.UUID,
    equipo_id: uuid.UUID,
) -> PaqueteAuditoria | None:
    equipo = equipos.obtener_por_id(equipo_id)
    if equipo is None:
        return None
    return PaqueteAuditoria(
        equipo=equipo,
        calibraciones=calibraciones.listar_por_equipo(equipo_id),
        mantenimientos=generar_mantenimiento(mantenimientos, laboratorio_id, equipo_id=equipo_id),
        documentos_vigentes=documentos.listar_vigentes(laboratorio_id),
        generado_en=datetime.utcnow(),
    )


# ---- Despachador único (RF-REP dispatcher) ----------------------------------
#
# Punto de entrada único que tanto el flujo síncrono (router) como el worker
# (flujo asíncrono, RNF-PERF-04) usan para obtener los datos de un reporte a
# partir de (tipo, filtros en dict) — así ambos caminos quedan garantizados
# de producir exactamente los mismos datos para los mismos parámetros, sin
# duplicar la lógica de "qué significa cada filtro" en dos lugares.


@dataclass
class RepositoriosReporte:
    equipos: EquipoRepository
    categorias_por_id: dict[uuid.UUID, str]
    areas_por_id: dict[uuid.UUID, str]
    calibraciones: CalibracionRepository
    mantenimientos: MantenimientoRepository
    documentos: DocumentoRepository


class TipoDeReporteDesconocido(ValueError):
    pass


class EquipoIdRequeridoParaPaquete(ErrorDeDominio):
    def __init__(self) -> None:
        super().__init__(
            "equipo_id_requerido", "El paquete de auditoría requiere el filtro 'equipo_id'."
        )


def generar_datos_por_tipo(
    tipo: str, laboratorio_id: uuid.UUID, filtros: dict, repos: RepositoriosReporte
) -> list | PaqueteAuditoria:
    if tipo == "inventario":
        return generar_inventario(
            repos.equipos,
            repos.categorias_por_id,
            repos.areas_por_id,
            categoria_id=_uuid_o_none(filtros.get("categoria_id")),
            area_id=_uuid_o_none(filtros.get("area_id")),
            estado_operativo=filtros.get("estado_operativo"),
        )
    if tipo == "calibraciones":
        return generar_calibraciones(repos.calibraciones, laboratorio_id)
    if tipo == "vencidos":
        return generar_vencidos(repos.calibraciones, repos.mantenimientos, repos.equipos, laboratorio_id)
    if tipo == "cumplimiento":
        meses = int(filtros.get("meses") or MESES_HISTORICO_CUMPLIMIENTO)
        return generar_cumplimiento(repos.calibraciones, laboratorio_id, meses=meses)
    if tipo == "mantenimiento":
        return generar_mantenimiento(
            repos.mantenimientos,
            laboratorio_id,
            equipo_id=_uuid_o_none(filtros.get("equipo_id")),
            desde=_fecha_o_none(filtros.get("desde")),
            hasta=_fecha_o_none(filtros.get("hasta")),
        )
    if tipo == "trazabilidad_documental":
        return generar_trazabilidad_documental(repos.documentos, laboratorio_id)
    if tipo == "paquete_auditoria":
        equipo_id = _uuid_o_none(filtros.get("equipo_id"))
        if equipo_id is None:
            raise EquipoIdRequeridoParaPaquete()
        paquete = generar_paquete_auditoria(
            repos.equipos,
            repos.calibraciones,
            repos.mantenimientos,
            repos.documentos,
            laboratorio_id,
            equipo_id,
        )
        if paquete is None:
            raise RecursoNoEncontrado("equipo_no_encontrado", "El equipo indicado no existe.")
        return paquete
    raise TipoDeReporteDesconocido(tipo)


def _uuid_o_none(valor: object) -> uuid.UUID | None:
    if not valor:
        return None
    return valor if isinstance(valor, uuid.UUID) else uuid.UUID(str(valor))


def _fecha_o_none(valor: object) -> date | None:
    if not valor:
        return None
    return valor if isinstance(valor, date) else date.fromisoformat(str(valor))
