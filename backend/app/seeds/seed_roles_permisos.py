"""Siembra los 6 roles de sistema y un set inicial de permisos.

Idempotente: se puede ejecutar múltiples veces sin duplicar filas.
Ver docs/03-requerimientos-funcionales.md (roles) y docs/15-api-design.md
(claves de permiso usadas como ejemplo en el diseño de la API).

Uso: `python -m app.seeds.seed_roles_permisos` (ver README del backend).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.auth.infrastructure.models import Permiso, Rol, RolPermiso

ROLES_SISTEMA = [
    "administrador",
    "director_tecnico",
    "calidad",
    "metrologia",
    "tecnico",
    "consulta",
]

PERMISOS_BASE = [
    ("equipos.crear", "Crear y editar equipos"),
    ("equipos.leer", "Ver equipos"),
    ("documentos.crear", "Subir, versionar y organizar documentos"),
    ("documentos.aprobar", "Aprobar versiones de documentos"),
    ("documentos.leer", "Ver documentos"),
    ("calibraciones.crear", "Registrar calibraciones"),
    ("mantenimientos.crear", "Registrar mantenimientos"),
    ("alertas.gestionar", "Resolver alertas manualmente y forzar la evaluación de vencimientos"),
    ("calendario.gestionar", "Crear, editar y eliminar eventos manuales del calendario"),
    ("auditoria.ver", "Ver la bitácora de auditoría"),
    ("usuarios.administrar", "Crear, editar y desactivar usuarios"),
    ("reportes.generar", "Generar y exportar reportes"),
    (
        "configuracion.gestionar",
        "Configurar umbrales de alerta, datos institucionales, política de contraseña y categorías/áreas",
    ),
]

# Matriz mínima rol -> permisos (se amplía en Sprint 3+ junto a los módulos
# de negocio).
MATRIZ_ROL_PERMISOS: dict[str, list[str]] = {
    # RF-CFG-03/04/05: "solo A gestiona configuración institucional"
    # (docs/03-requerimientos-funcionales.md Módulo 14) — ningún otro rol
    # recibe `configuracion.gestionar`, ni siquiera Director Técnico/Calidad
    # que sí tienen `reportes.generar` y `auditoria.ver`.
    "administrador": [clave for clave, _ in PERMISOS_BASE],
    "director_tecnico": [
        "equipos.leer",
        "documentos.aprobar",
        "documentos.leer",
        "alertas.gestionar",
        "calendario.gestionar",
        "auditoria.ver",
        "reportes.generar",
    ],
    "calidad": [
        "documentos.crear",
        "documentos.aprobar",
        "documentos.leer",
        "alertas.gestionar",
        "calendario.gestionar",
        "auditoria.ver",
        "reportes.generar",
    ],
    "metrologia": [
        "equipos.leer",
        "calibraciones.crear",
        "mantenimientos.crear",
        "alertas.gestionar",
        "calendario.gestionar",
        "reportes.generar",
    ],
    "tecnico": ["equipos.leer", "mantenimientos.crear"],
    "consulta": ["equipos.leer", "documentos.leer"],
}


def _obtener_o_crear_permiso(db: Session, clave: str, descripcion: str) -> Permiso:
    permiso = db.execute(select(Permiso).where(Permiso.clave == clave)).scalar_one_or_none()
    if permiso is None:
        permiso = Permiso(clave=clave, descripcion=descripcion)
        db.add(permiso)
        db.flush()
    return permiso


def _obtener_o_crear_rol_sistema(db: Session, nombre: str) -> Rol:
    rol = db.execute(
        select(Rol).where(Rol.nombre == nombre, Rol.laboratorio_id.is_(None))
    ).scalar_one_or_none()
    if rol is None:
        rol = Rol(nombre=nombre, laboratorio_id=None, es_sistema=True)
        db.add(rol)
        db.flush()
    return rol


def ejecutar() -> None:
    db = SessionLocal()
    try:
        permisos_por_clave = {
            clave: _obtener_o_crear_permiso(db, clave, descripcion) for clave, descripcion in PERMISOS_BASE
        }
        for nombre_rol in ROLES_SISTEMA:
            rol = _obtener_o_crear_rol_sistema(db, nombre_rol)
            claves_asignadas = MATRIZ_ROL_PERMISOS.get(nombre_rol, [])
            existentes = {rp.permiso_id for rp in db.query(RolPermiso).filter_by(rol_id=rol.id).all()}
            for clave in claves_asignadas:
                permiso = permisos_por_clave[clave]
                if permiso.id not in existentes:
                    db.add(RolPermiso(rol_id=rol.id, permiso_id=permiso.id))
        db.commit()
        print(f"Sembrados {len(ROLES_SISTEMA)} roles de sistema y {len(PERMISOS_BASE)} permisos.")
    finally:
        db.close()


if __name__ == "__main__":
    ejecutar()
