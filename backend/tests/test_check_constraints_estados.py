"""Regresión de Fase 0 / C3 (auditoría 2026-07-31) — columnas de tipo
enumerado deben rechazar valores fuera de dominio a nivel de base de datos,
no solo en la capa de aplicación. Ver alembic/versions/0016_check_constraints_estados.py.

Cada test intenta insertar una fila válida en todo salvo la columna bajo
prueba, que recibe un valor fuera del dominio declarado — debe fallar con
`IntegrityError` (violación de CHECK), no con éxito silencioso ni con el
`ProgrammingError` de RLS (que es un mecanismo de rechazo distinto, ver
tests/test_tenant_isolation.py)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import set_tenant_context
from app.modules.adjuntos.infrastructure.models import Adjunto
from app.modules.alertas.infrastructure.models import Alerta, NotificacionPendiente
from app.modules.auth.infrastructure.models import Usuario
from app.modules.calibraciones.infrastructure.models import Calibracion
from app.modules.documentos.infrastructure.models import Documento
from app.modules.equipos.infrastructure.models import Equipo
from app.modules.mantenimientos.infrastructure.models import Mantenimiento
from app.modules.qr.infrastructure.models import IncidenciaQr

# La columna más angosta bajo prueba es VARCHAR(20) (p. ej. alertas.tipo,
# calibraciones.resultado) — el valor inválido debe caber en todas para que
# el fallo sea siempre por CHECK y no por truncamiento de longitud.
_VALOR_INVALIDO = "invalido"


def _crear_equipo(db: Session, laboratorio_id: uuid.UUID, codigo: str = "EQ-CK-001") -> uuid.UUID:
    equipo_id = uuid.uuid4()
    db.add(
        Equipo(
            id=equipo_id,
            laboratorio_id=laboratorio_id,
            codigo_interno=codigo,
            nombre=f"Equipo {codigo}",
            estado_operativo="operativo",
        )
    )
    db.commit()
    return equipo_id


def _crear_alerta(db: Session, laboratorio_id: uuid.UUID) -> uuid.UUID:
    alerta_id = uuid.uuid4()
    db.add(
        Alerta(
            id=alerta_id,
            laboratorio_id=laboratorio_id,
            tipo="critica",
            origen_tipo="equipo",
            origen_id=uuid.uuid4(),
            mensaje="Prueba CHECK constraint",
            estado="activa",
        )
    )
    db.commit()
    return alerta_id


def test_usuarios_estado_rechaza_valor_fuera_de_dominio(db: Session, crear_laboratorio_con_admin):
    lab, _, _, _ = crear_laboratorio_con_admin(
        "Lab CK Usuarios", "lab-ck-usuarios", "admin@lab-ck-usuarios.dev"
    )
    set_tenant_context(db, lab)
    db.add(
        Usuario(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            correo="invalido@lab-ck-usuarios.dev",
            password_hash="x",
            nombre_completo="Usuario inválido",
            estado=_VALOR_INVALIDO,
        )
    )
    with pytest.raises(IntegrityError, match="ck_usuarios_estado"):
        db.flush()


def test_equipos_estado_operativo_rechaza_valor_fuera_de_dominio(db: Session, crear_laboratorio_con_admin):
    lab, _, _, _ = crear_laboratorio_con_admin("Lab CK Equipos", "lab-ck-equipos", "admin@lab-ck-equipos.dev")
    set_tenant_context(db, lab)
    db.add(
        Equipo(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            codigo_interno="EQ-CK-INV",
            nombre="Equipo inválido",
            estado_operativo=_VALOR_INVALIDO,
        )
    )
    with pytest.raises(IntegrityError, match="ck_equipos_estado_operativo"):
        db.flush()


def test_documentos_estado_rechaza_valor_fuera_de_dominio(db: Session, crear_laboratorio_con_admin):
    lab, _, _, _ = crear_laboratorio_con_admin("Lab CK Docs", "lab-ck-docs", "admin@lab-ck-docs.dev")
    set_tenant_context(db, lab)
    db.add(
        Documento(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            nombre="Documento inválido",
            estado=_VALOR_INVALIDO,
        )
    )
    with pytest.raises(IntegrityError, match="ck_documentos_estado"):
        db.flush()


def test_calibraciones_resultado_rechaza_valor_fuera_de_dominio(db: Session, crear_laboratorio_con_admin):
    lab, _, _, _ = crear_laboratorio_con_admin("Lab CK Calib", "lab-ck-calib", "admin@lab-ck-calib.dev")
    set_tenant_context(db, lab)
    equipo_id = _crear_equipo(db, lab)
    # `_crear_equipo` comitea internamente — el `SET LOCAL` de tenant muere
    # con ese commit (mismo motivo documentado en app/worker/main.py).
    set_tenant_context(db, lab)
    db.add(
        Calibracion(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            equipo_id=equipo_id,
            fecha_calibracion="2026-01-01",
            frecuencia_meses=12,
            proxima_fecha="2027-01-01",
            resultado=_VALOR_INVALIDO,
        )
    )
    with pytest.raises(IntegrityError, match="ck_calibraciones_resultado"):
        db.flush()


def test_mantenimientos_tipo_rechaza_valor_fuera_de_dominio(db: Session, crear_laboratorio_con_admin):
    lab, _, _, _ = crear_laboratorio_con_admin(
        "Lab CK Mant Tipo", "lab-ck-mant-tipo", "admin@lab-ck-mant-tipo.dev"
    )
    set_tenant_context(db, lab)
    equipo_id = _crear_equipo(db, lab)
    set_tenant_context(db, lab)  # ver comentario en test_calibraciones_resultado_...
    db.add(
        Mantenimiento(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            equipo_id=equipo_id,
            tipo=_VALOR_INVALIDO,
            estado="programado",
        )
    )
    with pytest.raises(IntegrityError, match="ck_mantenimientos_tipo"):
        db.flush()


def test_mantenimientos_estado_rechaza_valor_fuera_de_dominio(db: Session, crear_laboratorio_con_admin):
    lab, _, _, _ = crear_laboratorio_con_admin(
        "Lab CK Mant Estado", "lab-ck-mant-estado", "admin@lab-ck-mant-estado.dev"
    )
    set_tenant_context(db, lab)
    equipo_id = _crear_equipo(db, lab)
    set_tenant_context(db, lab)  # ver comentario en test_calibraciones_resultado_...
    db.add(
        Mantenimiento(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            equipo_id=equipo_id,
            tipo="preventivo",
            estado=_VALOR_INVALIDO,
        )
    )
    with pytest.raises(IntegrityError, match="ck_mantenimientos_estado"):
        db.flush()


def test_alertas_tipo_rechaza_valor_fuera_de_dominio(db: Session, crear_laboratorio_con_admin):
    lab, _, _, _ = crear_laboratorio_con_admin(
        "Lab CK Alt Tipo", "lab-ck-alt-tipo", "admin@lab-ck-alt-tipo.dev"
    )
    set_tenant_context(db, lab)
    db.add(
        Alerta(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            tipo=_VALOR_INVALIDO,
            origen_tipo="equipo",
            origen_id=uuid.uuid4(),
            mensaje="Prueba",
            estado="activa",
        )
    )
    with pytest.raises(IntegrityError, match="ck_alertas_tipo"):
        db.flush()


def test_alertas_estado_rechaza_valor_fuera_de_dominio(db: Session, crear_laboratorio_con_admin):
    lab, _, _, _ = crear_laboratorio_con_admin(
        "Lab CK Alt Estado", "lab-ck-alt-estado", "admin@lab-ck-alt-estado.dev"
    )
    set_tenant_context(db, lab)
    db.add(
        Alerta(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            tipo="critica",
            origen_tipo="equipo",
            origen_id=uuid.uuid4(),
            mensaje="Prueba",
            estado=_VALOR_INVALIDO,
        )
    )
    with pytest.raises(IntegrityError, match="ck_alertas_estado"):
        db.flush()


def test_alertas_origen_tipo_rechaza_valor_fuera_de_dominio(db: Session, crear_laboratorio_con_admin):
    lab, _, _, _ = crear_laboratorio_con_admin(
        "Lab CK Alt Origen", "lab-ck-alt-origen", "admin@lab-ck-alt-origen.dev"
    )
    set_tenant_context(db, lab)
    db.add(
        Alerta(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            tipo="critica",
            origen_tipo=_VALOR_INVALIDO,
            origen_id=uuid.uuid4(),
            mensaje="Prueba",
            estado="activa",
        )
    )
    with pytest.raises(IntegrityError, match="ck_alertas_origen_tipo"):
        db.flush()


def test_notificaciones_pendientes_estado_rechaza_valor_fuera_de_dominio(
    db: Session, crear_laboratorio_con_admin
):
    lab, _, _, _ = crear_laboratorio_con_admin(
        "Lab CK Notif Estado", "lab-ck-notif-estado", "a@lab-ck-notif-e.dev"
    )
    set_tenant_context(db, lab)
    alerta_id = _crear_alerta(db, lab)
    set_tenant_context(db, lab)  # ver comentario en test_calibraciones_resultado_...
    db.add(
        NotificacionPendiente(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            alerta_id=alerta_id,
            canal="websocket",
            payload={"mensaje": "prueba"},
            estado=_VALOR_INVALIDO,
        )
    )
    with pytest.raises(IntegrityError, match="ck_notificaciones_pendientes_estado"):
        db.flush()


def test_notificaciones_pendientes_canal_rechaza_valor_fuera_de_dominio(
    db: Session, crear_laboratorio_con_admin
):
    lab, _, _, _ = crear_laboratorio_con_admin(
        "Lab CK Notif Canal", "lab-ck-notif-canal", "a@lab-ck-notif-c.dev"
    )
    set_tenant_context(db, lab)
    alerta_id = _crear_alerta(db, lab)
    set_tenant_context(db, lab)  # ver comentario en test_calibraciones_resultado_...
    db.add(
        NotificacionPendiente(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            alerta_id=alerta_id,
            canal=_VALOR_INVALIDO,
            payload={"mensaje": "prueba"},
            estado="pendiente",
        )
    )
    with pytest.raises(IntegrityError, match="ck_notificaciones_pendientes_canal"):
        db.flush()


def test_incidencias_qr_estado_rechaza_valor_fuera_de_dominio(db: Session, crear_laboratorio_con_admin):
    lab, _, _, _ = crear_laboratorio_con_admin("Lab CK QR", "lab-ck-qr", "admin@lab-ck-qr.dev")
    set_tenant_context(db, lab)
    equipo_id = _crear_equipo(db, lab)
    set_tenant_context(db, lab)  # ver comentario en test_calibraciones_resultado_...
    db.add(
        IncidenciaQr(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            equipo_id=equipo_id,
            descripcion="Prueba",
            estado=_VALOR_INVALIDO,
        )
    )
    with pytest.raises(IntegrityError, match="ck_incidencias_qr_estado"):
        db.flush()


def test_adjuntos_entidad_tipo_rechaza_valor_fuera_de_dominio(db: Session, crear_laboratorio_con_admin):
    lab, _, _, _ = crear_laboratorio_con_admin("Lab CK Adj", "lab-ck-adj", "admin@lab-ck-adj.dev")
    set_tenant_context(db, lab)
    db.add(
        Adjunto(
            id=uuid.uuid4(),
            laboratorio_id=lab,
            entidad_tipo=_VALOR_INVALIDO,
            entidad_id=uuid.uuid4(),
            object_key="prueba/adjunto.pdf",
            nombre_archivo="adjunto.pdf",
            tamano_bytes=1024,
            tipo_mime="application/pdf",
        )
    )
    with pytest.raises(IntegrityError, match="ck_adjuntos_entidad_tipo"):
        db.flush()
