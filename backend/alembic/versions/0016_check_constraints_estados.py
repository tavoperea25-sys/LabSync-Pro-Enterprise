"""CHECK constraints para columnas de tipo enumerado — auditoría 2026-07-31,
hallazgo crítico C1 ("casi ninguna columna 'tipo enum' tiene CHECK constraint
a nivel de base de datos — la aplicación es la única barrera").

Antes de esta migración, `eventos_calendario.tipo` (0008) y
`reportes_generados.tipo/formato/estado` (0009) eran las únicas excepciones
que sí tenían CHECK constraint desde su creación; el resto de columnas de
estado quedaban como `VARCHAR` libre, validadas solo en la capa de
aplicación (ver p. ej. `ESTADOS_OPERATIVOS` en
`app/modules/equipos/domain/entities.py`). Un bug de aplicación, una
migración de datos manual o un acceso directo a la BD podía escribir un
valor fuera de dominio sin que Postgres lo impidiera.

Los valores de cada CHECK se copiaron literalmente de la tupla de dominio
vigente en cada módulo al momento de escribir esta migración (mismo criterio
ya usado en 0008/0009: la migración queda como una fotografía fija e
independiente del código de aplicación, que puede seguir evolucionando).
`adjuntos.entidad_tipo` no tenía una tupla de dominio propia — se agregó
`ENTIDADES_ADJUNTO` en `app/modules/adjuntos/domain/entities.py` como parte
de este mismo cambio, con el conjunto cerrado de valores que de hecho
escribe el código (`mantenimiento_evidencia`, `mantenimiento_informe`,
`calibracion_certificado` — únicos dos módulos que usan `AdjuntoRepository`).

`logs_auditoria.entidad_tipo` queda deliberadamente FUERA de este cambio: es
una bitácora genérica de auditoría que registra el nombre de entidad de
CUALQUIER módulo (`documento`, `usuario`, `equipo`, `laboratorio`,
`configuracion_laboratorio`, `evento_calendario`, `referencia_equipo`,
`incidencia_qr`, `mantenimiento`, `calibracion`, `reporte`, y lo que se
agregue en el futuro) — restringirla a un dominio cerrado rompería su
propósito de ser abierta a cualquier módulo nuevo sin requerir una migración
de esquema cada vez.

Se validaron los datos existentes de la base de desarrollo (`labsync`) antes
de escribir esta migración — un `SELECT DISTINCT` por columna confirmó que
todos los valores actuales ya caen dentro del dominio declarado en cada
`CheckConstraint` (ver informe de la corrección en docs/18-sprints.md). No se
esperan filas fuera de dominio en ningún despliegue existente, así que el
`ALTER TABLE ... ADD CONSTRAINT` no debería fallar por datos preexistentes;
si un despliegue tuviera datos corruptos fuera de este conjunto, esta
migración fallaría de forma explícita en vez de permitir que la corrupción
pase desapercibida — comportamiento deseado.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-04
"""

from __future__ import annotations

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None

# Mismo criterio ya usado en 0008/0009 (_TIPOS_EVENTO, _TIPOS_REPORTE, etc.):
# tuplas locales a la migración, no importadas desde app.modules.*.domain —
# una migración vieja no debe cambiar de comportamiento si el dominio
# evoluciona después.
_ESTADOS_USUARIO = ("activo", "inactivo", "pendiente_activacion")
_ESTADOS_OPERATIVOS_EQUIPO = ("operativo", "fuera_de_servicio", "en_mantenimiento", "de_baja")
_ESTADOS_DOCUMENTO = ("vigente", "obsoleto", "en_revision")
_RESULTADOS_CALIBRACION = ("conforme", "no_conforme")
_TIPOS_MANTENIMIENTO = ("preventivo", "correctivo", "predictivo", "calibracion_correctiva")
_ESTADOS_MANTENIMIENTO = ("programado", "en_ejecucion", "completado", "cancelado")
_TIPOS_ALERTA = ("critica", "preventiva")
_ESTADOS_ALERTA = ("activa", "resuelta")
_ORIGENES_ALERTA = ("calibracion", "documento", "mantenimiento", "equipo")
_ESTADOS_NOTIFICACION = ("pendiente", "enviado", "fallido")
_CANALES_NOTIFICACION = ("websocket", "email", "push")
_ESTADOS_INCIDENCIA_QR = ("pendiente", "en_revision", "resuelta")
_ENTIDADES_ADJUNTO = ("mantenimiento_evidencia", "mantenimiento_informe", "calibracion_certificado")


def _lista_sql(valores: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


# (nombre_constraint, tabla, columna, valores) — un solo lugar para
# upgrade/downgrade, evita que la lista se desincronice entre ambos.
_CONSTRAINTS: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("ck_usuarios_estado", "usuarios", "estado", _ESTADOS_USUARIO),
    ("ck_equipos_estado_operativo", "equipos", "estado_operativo", _ESTADOS_OPERATIVOS_EQUIPO),
    ("ck_documentos_estado", "documentos", "estado", _ESTADOS_DOCUMENTO),
    ("ck_calibraciones_resultado", "calibraciones", "resultado", _RESULTADOS_CALIBRACION),
    ("ck_mantenimientos_tipo", "mantenimientos", "tipo", _TIPOS_MANTENIMIENTO),
    ("ck_mantenimientos_estado", "mantenimientos", "estado", _ESTADOS_MANTENIMIENTO),
    ("ck_alertas_tipo", "alertas", "tipo", _TIPOS_ALERTA),
    ("ck_alertas_estado", "alertas", "estado", _ESTADOS_ALERTA),
    ("ck_alertas_origen_tipo", "alertas", "origen_tipo", _ORIGENES_ALERTA),
    ("ck_notificaciones_pendientes_estado", "notificaciones_pendientes", "estado", _ESTADOS_NOTIFICACION),
    ("ck_notificaciones_pendientes_canal", "notificaciones_pendientes", "canal", _CANALES_NOTIFICACION),
    ("ck_incidencias_qr_estado", "incidencias_qr", "estado", _ESTADOS_INCIDENCIA_QR),
    ("ck_adjuntos_entidad_tipo", "adjuntos", "entidad_tipo", _ENTIDADES_ADJUNTO),
)


def upgrade() -> None:
    for nombre, tabla, columna, valores in _CONSTRAINTS:
        op.create_check_constraint(nombre, tabla, f"{columna} IN ({_lista_sql(valores)})")


def downgrade() -> None:
    for nombre, tabla, _columna, _valores in _CONSTRAINTS:
        op.drop_constraint(nombre, tabla, type_="check")
