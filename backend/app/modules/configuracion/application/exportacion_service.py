"""Caso de uso de exportación/portabilidad de datos del tenant — Sprint 13."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.modules.auditoria.domain.ports import AuditoriaRepository
from app.modules.auth.domain.ports import UsuarioRepository
from app.modules.calibraciones.domain.ports import CalibracionRepository
from app.modules.configuracion.application.configuracion_service import ActorContexto
from app.modules.configuracion.infrastructure.exportador_datos import (
    generar_zip_exportacion,
    proyectar_areas,
    proyectar_calibraciones,
    proyectar_categorias,
    proyectar_documentos,
    proyectar_equipos,
    proyectar_mantenimientos,
    proyectar_usuarios,
)
from app.modules.documentos.domain.ports import DocumentoRepository
from app.modules.equipos.domain.ports import EquipoRepository, FiltrosEquipo
from app.modules.equipos.infrastructure.repositories import (
    AreaRepositorySQLAlchemy,
    CategoriaEquipoRepositorySQLAlchemy,
)
from app.modules.mantenimientos.domain.ports import FiltrosMantenimiento, MantenimientoRepository

_MODULO = "configuracion"


@dataclass
class RepositoriosExportacion:
    equipos: EquipoRepository
    documentos: DocumentoRepository
    calibraciones: CalibracionRepository
    mantenimientos: MantenimientoRepository
    usuarios: UsuarioRepository
    categorias: CategoriaEquipoRepositorySQLAlchemy
    areas: AreaRepositorySQLAlchemy


class ExportacionDatosService:
    def __init__(self, repos: RepositoriosExportacion, auditoria: AuditoriaRepository) -> None:
        self._repos = repos
        self._auditoria = auditoria

    def generar_zip(self, laboratorio_id: uuid.UUID, actor: ActorContexto) -> bytes:
        ahora = datetime.utcnow()
        datos = {
            "equipos": proyectar_equipos(self._repos.equipos.listar_todos(FiltrosEquipo())),
            "documentos": proyectar_documentos(self._repos.documentos.listar_todos(laboratorio_id)),
            "calibraciones": proyectar_calibraciones(self._repos.calibraciones.listar_todas(laboratorio_id)),
            "mantenimientos": proyectar_mantenimientos(
                self._repos.mantenimientos.listar_todos(laboratorio_id, FiltrosMantenimiento())
            ),
            "usuarios": proyectar_usuarios(self._repos.usuarios.listar()),
            "categorias_equipo": proyectar_categorias(self._repos.categorias.listar()),
            "areas": proyectar_areas(self._repos.areas.listar()),
        }
        contenido = generar_zip_exportacion(datos, ahora)

        self._auditoria.registrar(
            laboratorio_id=laboratorio_id,
            usuario_id=actor.usuario_id,
            ip_origen=actor.ip_origen,
            modulo=_MODULO,
            accion="exportar_datos_tenant",
            entidad_tipo="laboratorio",
            entidad_id=laboratorio_id,
            valor_anterior=None,
            valor_nuevo={"tamano_bytes": len(contenido)},
        )
        return contenido
