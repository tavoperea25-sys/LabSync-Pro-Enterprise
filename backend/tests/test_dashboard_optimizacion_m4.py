"""Fase 2 / M4 (planificación 2026-08-04, docs/22) — evidencia de que
`DashboardService.resumen()` deja de traer full scans a Python.

Este archivo mantiene una réplica literal de la implementación de
`resumen()` ANTERIOR a M4 (`_resumen_version_anterior`, copiada del código
ya revisado antes del cambio) — nunca se usa en producción, solo aquí, para:

1. Probar que el resultado es IDÉNTICO al de la versión optimizada sobre el
   mismo conjunto de datos (equivalencia funcional, no solo "no rompe los
   tests que ya existían").
2. Medir cuántas sentencias SQL emite cada versión sobre el mismo dataset
   (evidencia real, no solo razonamiento sobre el código)."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import date, timedelta

import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.database import engine, set_tenant_context
from app.modules.adjuntos.infrastructure.models import Adjunto  # noqa: F401 — registra la tabla `adjuntos`
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.infrastructure.repositories import UsuarioRepositorySQLAlchemy
from app.modules.calibraciones.domain.ports import CalibracionRepository
from app.modules.calibraciones.infrastructure.models import Calibracion
from app.modules.calibraciones.infrastructure.repositories import CalibracionRepositorySQLAlchemy
from app.modules.dashboard.application.dashboard_service import DashboardService
from app.modules.dashboard.domain.entities import ResumenDashboard
from app.modules.documentos.domain.ports import DocumentoRepository
from app.modules.documentos.infrastructure.models import Documento
from app.modules.documentos.infrastructure.repositories import DocumentoRepositorySQLAlchemy
from app.modules.equipos.domain.ports import EquipoRepository
from app.modules.equipos.infrastructure.models import Equipo
from app.modules.equipos.infrastructure.repositories import (
    AreaRepositorySQLAlchemy,
    EquipoRepositorySQLAlchemy,
)
from app.modules.mantenimientos.domain.ports import FiltrosMantenimiento, MantenimientoRepository
from app.modules.mantenimientos.infrastructure.models import Mantenimiento
from app.modules.mantenimientos.infrastructure.repositories import MantenimientoRepositorySQLAlchemy


def _resumen_version_anterior(
    equipos: EquipoRepository,
    calibraciones: CalibracionRepository,
    documentos: DocumentoRepository,
    mantenimientos: MantenimientoRepository,
    laboratorio_id: uuid.UUID,
) -> ResumenDashboard:
    """Copia literal de `DashboardService.resumen()` tal como estaba antes
    de M4 — NO se usa en producción, solo como referencia de comparación."""
    hoy = date.today()

    conteos_equipos = equipos.contar_por_estado()
    total_equipos = sum(conteos_equipos.values())
    operativos = conteos_equipos.get("operativo", 0)

    criticos = calibraciones.listar_criticos(laboratorio_id)
    proximas = calibraciones.listar_proximas(laboratorio_id, hoy, hoy + timedelta(days=30))
    semaforo_agregado = "normal"
    if any(c.semaforo == "rojo" for c in criticos):
        semaforo_agregado = "critico"
    elif any(c.semaforo in ("amarillo", "gris") for c in criticos):
        semaforo_agregado = "atencion"

    docs_criticos = documentos.listar_vigencia_critica(laboratorio_id, 30)
    documentos_vencidos = sum(1 for d in docs_criticos if d.fecha_vencimiento and d.fecha_vencimiento < hoy)
    documentos_por_vencer = len(docs_criticos) - documentos_vencidos
    todos_documentos = documentos.listar_todos(laboratorio_id)
    documentos_en_revision = sum(1 for d in todos_documentos if d.estado_efectivo(hoy) == "en_revision")

    cumplimiento: float | None = None
    if todos_documentos:
        vigentes = sum(1 for d in todos_documentos if d.estado_efectivo(hoy) == "vigente")
        cumplimiento = round(vigentes / len(todos_documentos) * 100, 1)

    proximos_mant = mantenimientos.listar_proximos(laboratorio_id, 30)
    preventivos_proximos = sum(1 for m in proximos_mant if m.tipo == "preventivo")
    abiertos = mantenimientos.listar_todos(
        laboratorio_id, FiltrosMantenimiento(estado="programado")
    ) + mantenimientos.listar_todos(laboratorio_id, FiltrosMantenimiento(estado="en_ejecucion"))
    correctivos_abiertos = sum(1 for m in abiertos if m.tipo in ("correctivo", "calibracion_correctiva"))

    return ResumenDashboard(
        equipos_total=total_equipos,
        equipos_operativos=operativos,
        equipos_en_mantenimiento=conteos_equipos.get("en_mantenimiento", 0),
        equipos_fuera_de_servicio=conteos_equipos.get("fuera_de_servicio", 0),
        equipos_de_baja=conteos_equipos.get("de_baja", 0),
        equipos_porcentaje_operativo=round(operativos / total_equipos * 100, 1) if total_equipos else 0.0,
        calibraciones_proximas_30_dias=len(proximas),
        calibraciones_semaforo=semaforo_agregado,
        documentos_vencidos=documentos_vencidos,
        documentos_por_vencer=documentos_por_vencer,
        documentos_en_revision=documentos_en_revision,
        mantenimientos_preventivos_proximos=preventivos_proximos,
        mantenimientos_correctivos_abiertos=correctivos_abiertos,
        cumplimiento_documental_pct=cumplimiento,
    )


@contextmanager
def _contar_queries():
    contador = {"n": 0}

    def _evento(*_args: object, **_kwargs: object) -> None:
        contador["n"] += 1

    event.listen(engine, "before_cursor_execute", _evento)
    try:
        yield contador
    finally:
        event.remove(engine, "before_cursor_execute", _evento)


def _crear_equipo(db: Session, laboratorio_id: uuid.UUID, codigo: str, estado: str) -> uuid.UUID:
    equipo_id = uuid.uuid4()
    db.add(
        Equipo(
            id=equipo_id,
            laboratorio_id=laboratorio_id,
            codigo_interno=codigo,
            nombre=f"Equipo {codigo}",
            estado_operativo=estado,
        )
    )
    return equipo_id


def _crear_calibracion(
    db: Session, laboratorio_id: uuid.UUID, equipo_id: uuid.UUID, proxima_fecha: date
) -> None:
    db.add(
        Calibracion(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            equipo_id=equipo_id,
            fecha_calibracion=proxima_fecha - timedelta(days=365),
            frecuencia_meses=12,
            proxima_fecha=proxima_fecha,
            resultado="conforme",
        )
    )


def _crear_documento(
    db: Session, laboratorio_id: uuid.UUID, nombre: str, estado: str, fecha_vencimiento: date | None
) -> None:
    db.add(
        Documento(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            nombre=nombre,
            estado=estado,
            fecha_vencimiento=fecha_vencimiento,
        )
    )


def _crear_mantenimiento(
    db: Session, laboratorio_id: uuid.UUID, equipo_id: uuid.UUID, tipo: str, estado: str
) -> None:
    db.add(
        Mantenimiento(
            id=uuid.uuid4(),
            laboratorio_id=laboratorio_id,
            equipo_id=equipo_id,
            tipo=tipo,
            estado=estado,
            fecha_programada=date.today() + timedelta(days=5),
        )
    )


def _sembrar_dataset_representativo(db: Session, laboratorio_id: uuid.UUID) -> None:
    """12 equipos, 8 calibraciones, 10 documentos, 12 mantenimientos —
    variados en estado/tipo para ejercitar cada rama de los KPIs."""
    set_tenant_context(db, laboratorio_id)
    hoy = date.today()

    estados_equipo = (
        ["operativo"] * 8 + ["fuera_de_servicio"] * 2 + ["en_mantenimiento"] * 1 + ["de_baja"] * 1
    )
    equipos_ids = [
        _crear_equipo(db, laboratorio_id, f"EQ-M4-{i:02d}", estado)
        for i, estado in enumerate(estados_equipo)
    ]
    db.commit()
    set_tenant_context(db, laboratorio_id)

    # Calibraciones: 2 vencidas (rojo), 3 próximas <30 días (amarillo), 3
    # verdes (lejos) — 4 equipos quedan sin ninguna (gris).
    proximas_fechas = (
        [hoy - timedelta(days=10), hoy - timedelta(days=3)]  # rojo
        + [hoy + timedelta(days=5), hoy + timedelta(days=15), hoy + timedelta(days=29)]  # amarillo
        + [hoy + timedelta(days=200), hoy + timedelta(days=300), hoy + timedelta(days=400)]  # verde
    )
    for equipo_id, proxima in zip(equipos_ids, proximas_fechas, strict=False):
        _crear_calibracion(db, laboratorio_id, equipo_id, proxima)
    db.commit()
    set_tenant_context(db, laboratorio_id)

    documentos = [
        ("Vigente A", "vigente", None),
        ("Vigente B", "vigente", hoy + timedelta(days=100)),
        ("Vigente vencido A", "vigente", hoy - timedelta(days=5)),  # estado_efectivo -> vencido
        ("Vigente vencido B", "vigente", hoy - timedelta(days=1)),
        ("En revisión A", "en_revision", None),
        ("En revisión B", "en_revision", hoy + timedelta(days=50)),
        ("En revisión vencido", "en_revision", hoy - timedelta(days=2)),  # estado_efectivo -> vencido
        ("Obsoleto A", "obsoleto", None),
        ("Obsoleto B", "obsoleto", None),
        ("Vigente C", "vigente", hoy + timedelta(days=10)),
    ]
    for nombre, estado, vencimiento in documentos:
        _crear_documento(db, laboratorio_id, nombre, estado, vencimiento)
    db.commit()
    set_tenant_context(db, laboratorio_id)

    mantenimientos = [
        ("correctivo", "programado"),
        ("correctivo", "programado"),
        ("calibracion_correctiva", "en_ejecucion"),
        ("preventivo", "programado"),
        ("preventivo", "programado"),
        ("predictivo", "en_ejecucion"),
        ("predictivo", "programado"),
        ("correctivo", "completado"),  # cerrado -> no cuenta
        ("preventivo", "cancelado"),  # cerrado -> no cuenta
        ("calibracion_correctiva", "programado"),
        ("preventivo", "en_ejecucion"),
        ("correctivo", "en_ejecucion"),
    ]
    for tipo, estado in mantenimientos:
        equipo_id = equipos_ids[hash((tipo, estado)) % len(equipos_ids)]
        _crear_mantenimiento(db, laboratorio_id, equipo_id, tipo, estado)
    db.commit()
    set_tenant_context(db, laboratorio_id)


def _construir_service(db: Session) -> DashboardService:
    return DashboardService(
        equipos=EquipoRepositorySQLAlchemy(db),
        calibraciones=CalibracionRepositorySQLAlchemy(db),
        documentos=DocumentoRepositorySQLAlchemy(db),
        mantenimientos=MantenimientoRepositorySQLAlchemy(db),
        auditoria=AuditoriaRepositorySQLAlchemy(db),
        areas=AreaRepositorySQLAlchemy(db),
        usuarios=UsuarioRepositorySQLAlchemy(db),
    )


def test_resumen_optimizado_produce_el_mismo_resultado_con_menos_consultas(
    db: Session, crear_laboratorio_con_admin
):
    laboratorio_id, _, _, _ = crear_laboratorio_con_admin(
        "Lab Dashboard M4", "lab-dashboard-m4", "admin@dashboard-m4.dev"
    )
    _sembrar_dataset_representativo(db, laboratorio_id)

    equipos = EquipoRepositorySQLAlchemy(db)
    calibraciones = CalibracionRepositorySQLAlchemy(db)
    documentos = DocumentoRepositorySQLAlchemy(db)
    mantenimientos = MantenimientoRepositorySQLAlchemy(db)

    with _contar_queries() as contador_antes:
        resultado_anterior = _resumen_version_anterior(
            equipos, calibraciones, documentos, mantenimientos, laboratorio_id
        )
    consultas_antes = contador_antes["n"]

    with _contar_queries() as contador_despues:
        resultado_nuevo = _construir_service(db).resumen(laboratorio_id)
    consultas_despues = contador_despues["n"]

    # Evidencia para el informe de M4 — ver salida de pytest con -s.
    print(
        f"\n[M4] resumen(): {consultas_antes} consultas SQL antes -> "
        f"{consultas_despues} después (dataset: 12 equipos, 8 calibraciones, "
        f"10 documentos, 12 mantenimientos)"
    )

    assert resultado_nuevo == resultado_anterior
    assert consultas_despues < consultas_antes


def test_resumen_con_laboratorio_vacio_no_falla_y_coincide(db: Session, crear_laboratorio_con_admin):
    laboratorio_id, _, _, _ = crear_laboratorio_con_admin(
        "Lab Dashboard M4 Vacío", "lab-dashboard-m4-vacio", "admin@dashboard-m4-vacio.dev"
    )
    set_tenant_context(db, laboratorio_id)

    equipos = EquipoRepositorySQLAlchemy(db)
    calibraciones = CalibracionRepositorySQLAlchemy(db)
    documentos = DocumentoRepositorySQLAlchemy(db)
    mantenimientos = MantenimientoRepositorySQLAlchemy(db)

    resultado_anterior = _resumen_version_anterior(
        equipos, calibraciones, documentos, mantenimientos, laboratorio_id
    )
    resultado_nuevo = _construir_service(db).resumen(laboratorio_id)

    assert resultado_nuevo == resultado_anterior
    assert resultado_nuevo.equipos_total == 0
    assert resultado_nuevo.cumplimiento_documental_pct is None
    assert resultado_nuevo.calibraciones_semaforo == "normal"
    assert resultado_nuevo.mantenimientos_correctivos_abiertos == 0
    assert resultado_nuevo.documentos_en_revision == 0


def test_resumen_con_multiples_registros_kpis_no_cubiertos_antes(db: Session, crear_laboratorio_con_admin):
    """Fase 2/M4 — `documentos_en_revision`, `mantenimientos_*`,
    `calibraciones_proximas_30_dias` no tenían ningún test que fijara su
    valor antes de esta fase (ver investigación previa a M4); estos son
    precisamente los KPIs que M4 tocó, así que quedan pinneados aquí."""
    laboratorio_id, _, _, _ = crear_laboratorio_con_admin(
        "Lab Dashboard M4 KPIs", "lab-dashboard-m4-kpis", "admin@dashboard-m4-kpis.dev"
    )
    _sembrar_dataset_representativo(db, laboratorio_id)

    resultado = _construir_service(db).resumen(laboratorio_id)

    # 2 documentos "en_revision" con estado_efectivo == "en_revision" (el
    # tercero, "En revisión vencido", pasa a "vencido" por RN-DOC-01).
    assert resultado.documentos_en_revision == 2
    # 3 calibraciones con proxima_fecha entre hoy y hoy+30 (semáforo amarillo).
    assert resultado.calibraciones_proximas_30_dias == 3
    # preventivo+programado: 2 (predictivo no cuenta para este KPI).
    assert resultado.mantenimientos_preventivos_proximos == 2
    # abiertos (programado/en_ejecucion) con tipo correctivo o
    # calibracion_correctiva: 2 programado-correctivo + 1 en_ejecucion-cc +
    # 1 programado-cc + 1 en_ejecucion-correctivo = 5.
    assert resultado.mantenimientos_correctivos_abiertos == 5


@pytest.mark.parametrize("umbral", [1, 5])
def test_mantenimientos_contar_abiertos_por_tipo_excluye_cerrados(
    db: Session, crear_laboratorio_con_admin, umbral: int
):
    """Prueba directa del nuevo método agregado, aislada de `resumen()`."""
    laboratorio_id, _, _, _ = crear_laboratorio_con_admin(
        f"Lab Mant M4 {umbral}", f"lab-mant-m4-{umbral}", f"admin-mant-m4-{umbral}@dashboard-m4.dev"
    )
    set_tenant_context(db, laboratorio_id)
    equipo_id = _crear_equipo(db, laboratorio_id, f"EQ-MANT-M4-{umbral}", "operativo")
    db.commit()
    set_tenant_context(db, laboratorio_id)

    for tipo, estado in [
        ("correctivo", "programado"),
        ("preventivo", "en_ejecucion"),
        ("correctivo", "completado"),  # no debe contar
        ("predictivo", "cancelado"),  # no debe contar
    ]:
        _crear_mantenimiento(db, laboratorio_id, equipo_id, tipo, estado)
    db.commit()
    set_tenant_context(db, laboratorio_id)

    conteos = MantenimientoRepositorySQLAlchemy(db).contar_abiertos_por_tipo()
    assert conteos == {"correctivo": 1, "preventivo": 1}


def test_documentos_contar_por_estado_efectivo_replica_estado_efectivo(
    db: Session, crear_laboratorio_con_admin
):
    """Prueba directa del nuevo método agregado — compara contra
    `Documento.estado_efectivo()` documento por documento (real, no mockeado)."""
    laboratorio_id, _, _, _ = crear_laboratorio_con_admin(
        "Lab Doc M4", "lab-doc-m4", "admin@doc-m4.dev"
    )
    set_tenant_context(db, laboratorio_id)
    hoy = date.today()
    datos = [
        ("A", "vigente", None),
        ("B", "vigente", hoy - timedelta(days=1)),  # vencido
        ("C", "en_revision", None),
        ("D", "obsoleto", None),
    ]
    for nombre, estado, vencimiento in datos:
        _crear_documento(db, laboratorio_id, nombre, estado, vencimiento)
    db.commit()
    set_tenant_context(db, laboratorio_id)

    conteos = DocumentoRepositorySQLAlchemy(db).contar_por_estado_efectivo(hoy)
    assert conteos == {"vigente": 1, "vencido": 1, "en_revision": 1, "obsoleto": 1}
