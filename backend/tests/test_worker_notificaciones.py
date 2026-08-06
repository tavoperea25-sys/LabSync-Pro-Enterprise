"""Regresión de Fase 0 / C1 (auditoría 2026-07-31) — una notificación que
falla al enviarse no debe bloquear el resto del outbox del mismo ciclo ni
quedar reintentándose indefinidamente. Ver docstring del bucle de
notificaciones en app/worker/main.py::_procesar_laboratorio."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.alertas.infrastructure.models import Alerta, NotificacionPendiente
from app.worker.main import _procesar_laboratorio


def _crear_alerta(db: Session, laboratorio_id: uuid.UUID) -> uuid.UUID:
    alerta_id = uuid.uuid4()
    db.add(
        Alerta(
            id=alerta_id,
            laboratorio_id=laboratorio_id,
            tipo="critica",
            origen_tipo="equipo",
            origen_id=uuid.uuid4(),
            mensaje="Prueba worker",
            estado="activa",
        )
    )
    db.flush()
    return alerta_id


def test_una_notificacion_toxica_no_bloquea_las_demas_del_mismo_ciclo(
    db: Session, crear_laboratorio_con_admin
):
    laboratorio_id, _, _, _ = crear_laboratorio_con_admin(
        "Lab Worker Outbox", "lab-worker-outbox", "admin@lab-worker-outbox.dev"
    )
    set_tenant_context(db, laboratorio_id)

    alerta_toxica = _crear_alerta(db, laboratorio_id)
    alerta_normal = _crear_alerta(db, laboratorio_id)

    # Payload que excede el límite real de 8000 bytes de `pg_notify` — provoca
    # un fallo genuino (no simulado) en el `SELECT pg_notify(...)` del worker,
    # el mismo escenario descrito en el hallazgo C1 de la auditoría.
    notif_toxica_id = uuid.uuid4()
    db.add(
        NotificacionPendiente(
            id=notif_toxica_id,
            laboratorio_id=laboratorio_id,
            alerta_id=alerta_toxica,
            canal="websocket",
            payload={"mensaje": "x" * 9000},
            estado="pendiente",
        )
    )

    # Creada después (creado_en posterior, mismo commit) — con el bug
    # original, ni siquiera se intentaba: la excepción de la notificación
    # tóxica escapaba del bucle completo y abortaba el resto del lote.
    notif_normal_id = uuid.uuid4()
    db.add(
        NotificacionPendiente(
            id=notif_normal_id,
            laboratorio_id=laboratorio_id,
            alerta_id=alerta_normal,
            canal="websocket",
            payload={"mensaje": "Notificación normal"},
            estado="pendiente",
        )
    )
    # Un solo commit para las dos — dos commits separados harían morir el
    # `SET LOCAL` de tenant a mitad de camino (mismo motivo documentado en
    # app/worker/main.py) y la segunda inserción violaría RLS.
    db.commit()

    # `_procesar_laboratorio` abre su propia sesión (igual que el proceso
    # `worker` real) — se reutiliza tal cual, sin refactor adicional.
    _procesar_laboratorio(laboratorio_id)

    # La sesión de la fixture no expira sus objetos automáticamente al hacer
    # commit (`expire_on_commit=False`, ver app/core/database.py) — hay que
    # forzar la relectura para no leer los valores en caché de antes de que
    # el worker (en su propia sesión) los actualizara.
    db.expire_all()
    set_tenant_context(db, laboratorio_id)

    toxica = db.get(NotificacionPendiente, notif_toxica_id)
    normal = db.get(NotificacionPendiente, notif_normal_id)

    assert toxica.estado == "fallido"
    assert toxica.intentos == 1
    assert toxica.procesado_en is not None

    assert normal.estado == "enviado"
    assert normal.procesado_en is not None
