"""Endpoint de Búsqueda Global — RF-SEARCH-01 a 05.

Sin capa domain/application propia a propósito: es una composición de
lectura pura sobre repositorios que ya existen en otros módulos (mismo
criterio que `dashboard/presentation/router.py`, el único otro endpoint del
backend que agrega datos de varios módulos sin dueño propio). Cada
categoría de resultado se consulta solo si el usuario tiene el permiso de
lectura correspondiente (RF-SEARCH-05) — nunca se filtra después de traer
los datos, se evita la consulta por completo."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.infrastructure.repositories import UsuarioRepositorySQLAlchemy
from app.modules.auth.presentation.dependencies import UsuarioContexto, get_usuario_actual, tiene_permiso
from app.modules.busqueda.presentation.schemas import ResultadoBusqueda
from app.modules.calibraciones.infrastructure.repositories import CalibracionRepositorySQLAlchemy
from app.modules.documentos.infrastructure.repositories import DocumentoRepositorySQLAlchemy
from app.modules.equipos.infrastructure.repositories import EquipoRepositorySQLAlchemy
from app.modules.mantenimientos.infrastructure.repositories import MantenimientoRepositorySQLAlchemy

router = APIRouter(prefix="/api/v1", tags=["busqueda"])

_LIMITE_POR_CATEGORIA = 8
_LONGITUD_MINIMA = 2


@router.get("/busqueda", response_model=list[ResultadoBusqueda])
def buscar(
    q: str = Query(default="", max_length=200),
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(get_usuario_actual),
) -> list[ResultadoBusqueda]:
    consulta = q.strip()
    if len(consulta) < _LONGITUD_MINIMA:
        return []

    resultados: list[ResultadoBusqueda] = []

    if tiene_permiso(db, usuario.roles, "equipos.leer"):
        for e in EquipoRepositorySQLAlchemy(db).buscar_texto(consulta, _LIMITE_POR_CATEGORIA):
            resultados.append(
                ResultadoBusqueda(
                    tipo="equipo",
                    id=e.id,
                    titulo=e.nombre,
                    subtitulo=e.codigo_interno,
                    ruta=f"/equipos/{e.id}",
                )
            )

        for c in CalibracionRepositorySQLAlchemy(db).buscar_texto(consulta, _LIMITE_POR_CATEGORIA):
            resultados.append(
                ResultadoBusqueda(
                    tipo="calibracion",
                    id=c.id,
                    titulo=f"Certificado {c.numero_certificado}" if c.numero_certificado else "Calibración",
                    subtitulo=c.laboratorio_proveedor,
                    ruta=f"/equipos/{c.equipo_id}",
                )
            )

        for m in MantenimientoRepositorySQLAlchemy(db).buscar_texto(consulta, _LIMITE_POR_CATEGORIA):
            resultados.append(
                ResultadoBusqueda(
                    tipo="mantenimiento",
                    id=m.id,
                    titulo=m.descripcion or f"Mantenimiento {m.tipo}",
                    subtitulo=m.estado,
                    ruta=f"/equipos/{m.equipo_id}",
                )
            )

    if tiene_permiso(db, usuario.roles, "documentos.leer"):
        for d in DocumentoRepositorySQLAlchemy(db).buscar_texto(consulta, _LIMITE_POR_CATEGORIA):
            resultados.append(
                ResultadoBusqueda(
                    tipo="documento",
                    id=d.id,
                    titulo=d.nombre,
                    subtitulo=d.categoria,
                    ruta=f"/documentos/{d.id}",
                )
            )

    if tiene_permiso(db, usuario.roles, "usuarios.administrar"):
        for u in UsuarioRepositorySQLAlchemy(db).buscar_texto(consulta, _LIMITE_POR_CATEGORIA):
            resultados.append(
                ResultadoBusqueda(
                    tipo="usuario", id=u.id, titulo=u.nombre_completo, subtitulo=u.correo, ruta="/usuarios"
                )
            )

    if tiene_permiso(db, usuario.roles, "auditoria.ver"):
        for log in AuditoriaRepositorySQLAlchemy(db).buscar_texto(consulta, _LIMITE_POR_CATEGORIA):
            resultados.append(
                ResultadoBusqueda(
                    tipo="auditoria",
                    id=log.id,
                    titulo=f"{log.accion} · {log.modulo}",
                    subtitulo=log.entidad_tipo,
                    ruta="/auditoria",
                )
            )

    return resultados
