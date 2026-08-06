"""Casos de uso del Dashboard. Ver docs/03-requerimientos-funcionales.md
Módulo 2.

Agrega datos de Equipos, Calibraciones, Documentos, Mantenimientos y
Auditoría reutilizando los repositorios de cada módulo — nunca duplica su
lógica de negocio (ej. RN-CAL-01 sigue viviendo solo en
`calibraciones/domain/entities.py::semaforo`, aquí solo se lee su resultado
vía `listar_estado_todos`/`listar_criticos`; RN-DOC-01 solo en
`documentos/domain/entities.py::Documento.estado_efectivo`, replicada en SQL
por `DocumentoRepository.contar_por_estado_efectivo` — Fase 2/M4,
docs/22-planificacion-fase2.md)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from app.modules.auditoria.domain.ports import AuditoriaRepository, FiltrosAuditoria
from app.modules.auth.domain.ports import UsuarioRepository
from app.modules.calibraciones.domain.entities import EquipoConSemaforo
from app.modules.calibraciones.domain.ports import CalibracionRepository
from app.modules.dashboard.domain.entities import ActividadReciente, EquipoCritico, ResumenDashboard
from app.modules.documentos.domain.ports import DocumentoRepository
from app.modules.equipos.domain.entities import Equipo
from app.modules.equipos.domain.ports import EquipoRepository, FiltrosEquipo
from app.modules.equipos.infrastructure.repositories import AreaRepositorySQLAlchemy
from app.modules.mantenimientos.domain.ports import MantenimientoRepository

_DIAS_HORIZONTE_CALIBRACIONES = 30
_DIAS_HORIZONTE_DOCUMENTOS = 30
_DIAS_HORIZONTE_MANTENIMIENTOS = 30
_LIMITE_EQUIPOS_CRITICOS_DEFECTO = 10
_LIMITE_ACTIVIDAD_DEFECTO = 8

# Orden de urgencia para la tabla "equipos que requieren atención" — un
# equipo fuera de servicio siempre se muestra antes que uno con calibración
# solo "próxima a vencer".
_PRIORIDAD_ESTADO = {"fuera_de_servicio": 0, "en_mantenimiento": 1, "operativo": 2, "de_baja": 3}
_PRIORIDAD_SEMAFORO = {"rojo": 0, "gris": 1, "amarillo": 2, None: 3, "verde": 4}


class DashboardService:
    def __init__(
        self,
        equipos: EquipoRepository,
        calibraciones: CalibracionRepository,
        documentos: DocumentoRepository,
        mantenimientos: MantenimientoRepository,
        auditoria: AuditoriaRepository,
        areas: AreaRepositorySQLAlchemy,
        usuarios: UsuarioRepository,
    ) -> None:
        self._equipos = equipos
        self._calibraciones = calibraciones
        self._documentos = documentos
        self._mantenimientos = mantenimientos
        self._auditoria = auditoria
        self._areas = areas
        self._usuarios = usuarios

    def resumen(self, laboratorio_id: uuid.UUID) -> ResumenDashboard:
        hoy = date.today()

        conteos_equipos = self._equipos.contar_por_estado()
        total_equipos = sum(conteos_equipos.values())
        operativos = conteos_equipos.get("operativo", 0)

        # Fase 2/M4 (docs/22-planificacion-fase2.md) — `listar_criticos` y
        # `listar_proximas` llamaban por separado a la misma consulta interna
        # (`_ultima_por_equipo`, un DISTINCT ON + semáforo por cada equipo);
        # una sola llamada a `listar_estado_todos` basta para derivar ambos
        # hechos, sin duplicar esa consulta dentro de la misma petición.
        estados_calibracion = self._calibraciones.listar_estado_todos(laboratorio_id)
        semaforo_agregado = "normal"
        if any(e.semaforo == "rojo" for e in estados_calibracion):
            semaforo_agregado = "critico"
        elif any(e.semaforo in ("amarillo", "gris") for e in estados_calibracion):
            semaforo_agregado = "atencion"
        limite_calibraciones = hoy + timedelta(days=_DIAS_HORIZONTE_CALIBRACIONES)
        calibraciones_proximas = sum(
            1
            for e in estados_calibracion
            if e.proxima_fecha is not None and hoy <= e.proxima_fecha <= limite_calibraciones
        )

        docs_criticos = self._documentos.listar_vigencia_critica(laboratorio_id, _DIAS_HORIZONTE_DOCUMENTOS)
        documentos_vencidos = sum(
            1 for d in docs_criticos if d.fecha_vencimiento and d.fecha_vencimiento < hoy
        )
        documentos_por_vencer = len(docs_criticos) - documentos_vencidos
        # Fase 2/M4 — antes traía hasta 5000 documentos completos a Python
        # (`listar_todos`) solo para contar dos categorías de
        # `estado_efectivo`; ahora es un único GROUP BY.
        conteos_documentos = self._documentos.contar_por_estado_efectivo(hoy)
        documentos_en_revision = conteos_documentos.get("en_revision", 0)
        total_documentos = sum(conteos_documentos.values())

        cumplimiento: float | None = None
        if total_documentos:
            vigentes = conteos_documentos.get("vigente", 0)
            cumplimiento = round(vigentes / total_documentos * 100, 1)

        proximos_mant = self._mantenimientos.listar_proximos(laboratorio_id, _DIAS_HORIZONTE_MANTENIMIENTOS)
        preventivos_proximos = sum(1 for m in proximos_mant if m.tipo == "preventivo")
        # Fase 2/M4 — antes eran dos `listar_todos()` SIN límite (uno por
        # estado abierto), concatenados y sumados por tipo en Python; ahora
        # es un único GROUP BY por tipo.
        conteos_abiertos = self._mantenimientos.contar_abiertos_por_tipo()
        correctivos_abiertos = conteos_abiertos.get("correctivo", 0) + conteos_abiertos.get(
            "calibracion_correctiva", 0
        )

        return ResumenDashboard(
            equipos_total=total_equipos,
            equipos_operativos=operativos,
            equipos_en_mantenimiento=conteos_equipos.get("en_mantenimiento", 0),
            equipos_fuera_de_servicio=conteos_equipos.get("fuera_de_servicio", 0),
            equipos_de_baja=conteos_equipos.get("de_baja", 0),
            equipos_porcentaje_operativo=round(operativos / total_equipos * 100, 1) if total_equipos else 0.0,
            calibraciones_proximas_30_dias=calibraciones_proximas,
            calibraciones_semaforo=semaforo_agregado,
            documentos_vencidos=documentos_vencidos,
            documentos_por_vencer=documentos_por_vencer,
            documentos_en_revision=documentos_en_revision,
            mantenimientos_preventivos_proximos=preventivos_proximos,
            mantenimientos_correctivos_abiertos=correctivos_abiertos,
            cumplimiento_documental_pct=cumplimiento,
        )

    def equipos_criticos(
        self, laboratorio_id: uuid.UUID, limite: int = _LIMITE_EQUIPOS_CRITICOS_DEFECTO
    ) -> list[EquipoCritico]:
        semaforos = {c.equipo_id: c for c in self._calibraciones.listar_criticos(laboratorio_id)}
        areas_por_id = {a.id: a.nombre for a in self._areas.listar()}
        usuarios_por_id: dict[uuid.UUID, str] = {}

        def _nombre_usuario(usuario_id: uuid.UUID | None) -> str | None:
            if usuario_id is None:
                return None
            if usuario_id not in usuarios_por_id:
                usuario = self._usuarios.obtener_por_id(usuario_id)
                usuarios_por_id[usuario_id] = usuario.nombre_completo if usuario else "Usuario eliminado"
            return usuarios_por_id[usuario_id]

        candidatos: list[tuple[Equipo, EquipoConSemaforo | None, str | None]] = []
        for equipo in self._equipos.listar_todos(FiltrosEquipo()):
            info = semaforos.get(equipo.id)
            semaforo = info.semaforo if info else None
            necesita_atencion = equipo.estado_operativo != "operativo" or semaforo in ("rojo", "amarillo")
            if not necesita_atencion:
                continue
            candidatos.append((equipo, info, semaforo))

        candidatos.sort(
            key=lambda fila: (
                _PRIORIDAD_ESTADO.get(fila[0].estado_operativo, 9),
                _PRIORIDAD_SEMAFORO.get(fila[2], 9),
            )
        )

        filas: list[EquipoCritico] = []
        for equipo, info, semaforo in candidatos[:limite]:
            ultima_fecha = None
            if info and info.ultima_calibracion_id:
                calibracion = self._calibraciones.obtener_por_id(info.ultima_calibracion_id)
                ultima_fecha = calibracion.fecha_calibracion if calibracion else None
            filas.append(
                EquipoCritico(
                    equipo_id=equipo.id,
                    equipo_nombre=equipo.nombre,
                    equipo_codigo_interno=equipo.codigo_interno,
                    area_nombre=areas_por_id.get(equipo.area_id) if equipo.area_id else None,
                    estado_operativo=equipo.estado_operativo,
                    ultima_calibracion_fecha=ultima_fecha,
                    proxima_calibracion_fecha=info.proxima_fecha if info else None,
                    semaforo_calibracion=semaforo,
                    responsable_nombre=_nombre_usuario(equipo.responsable_id),
                )
            )
        return filas

    def actividad_reciente(
        self, laboratorio_id: uuid.UUID, limite: int = _LIMITE_ACTIVIDAD_DEFECTO
    ) -> list[ActividadReciente]:
        registros = self._auditoria.listar_filtrado(FiltrosAuditoria(), limite)
        usuarios_por_id: dict[uuid.UUID, str] = {}

        def _nombre_usuario(usuario_id: uuid.UUID | None) -> str | None:
            if usuario_id is None:
                return None
            if usuario_id not in usuarios_por_id:
                usuario = self._usuarios.obtener_por_id(usuario_id)
                usuarios_por_id[usuario_id] = usuario.nombre_completo if usuario else "Usuario eliminado"
            return usuarios_por_id[usuario_id]

        return [
            ActividadReciente(
                usuario_nombre=_nombre_usuario(registro.usuario_id),
                accion=registro.accion,
                modulo=registro.modulo,
                entidad_tipo=registro.entidad_tipo,
                creado_en=registro.creado_en,
            )
            for registro in registros
        ]
