"""Endpoints del módulo QR. Ver docs/15-api-design.md sección "QR (público)"
y docs/16-seguridad.md sección 6 (rate limiting en superficie sin auth).

Nota: a diferencia del resto del proyecto, este módulo NO usa
`from __future__ import annotations`. slowapi envuelve los handlers con un
decorador cuyo `__globals__` no incluye los símbolos de este archivo; con
anotaciones diferidas (strings), FastAPI no logra resolver `datos:
ReportarIncidenciaRequest` a la clase real y lo trata como parámetro de
query en vez de body. Con anotaciones reales (sin el future import) FastAPI
las lee directamente de `__annotations__` sin necesitar resolverlas."""

import io
import uuid

import qrcode
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.database import get_db, set_tenant_context
from app.core.ip import ip_valida
from app.core.rate_limit import limiter
from app.modules.auditoria.infrastructure.repositories import AuditoriaRepositorySQLAlchemy
from app.modules.auth.presentation.dependencies import UsuarioContexto, requiere_permiso
from app.modules.equipos.infrastructure.repositories import EquipoRepositorySQLAlchemy
from app.modules.qr.application.qr_service import ActorContexto, QrService, TokenQrInvalido
from app.modules.qr.infrastructure.repositories import (
    IncidenciaQrRepositorySQLAlchemy,
    QrTokenRepositorySQLAlchemy,
)
from app.modules.qr.presentation.schemas import (
    ActualizarEstadoIncidenciaRequest,
    EquipoPublicoOut,
    IncidenciaCreadaOut,
    IncidenciaQrOut,
    QrInfoOut,
    ReportarIncidenciaRequest,
)

router = APIRouter(prefix="/api/v1", tags=["qr"])

_almacenamiento_fotos = AlmacenamientoMinIO(get_settings().minio_bucket_fotos_equipos)


def _service(db: Session) -> QrService:
    return QrService(
        QrTokenRepositorySQLAlchemy(db),
        IncidenciaQrRepositorySQLAlchemy(db),
        EquipoRepositorySQLAlchemy(db),
        AuditoriaRepositorySQLAlchemy(db),
    )


# ---------------------------------------------------------------------------
# Endpoints públicos — sin autenticación (RF-QR-02, RF-QR-03)
# ---------------------------------------------------------------------------


@router.get("/publico/qr/{token}", response_model=EquipoPublicoOut)
@limiter.limit("30/minute")
def ver_equipo_por_qr(token: str, request: Request, db: Session = Depends(get_db)) -> EquipoPublicoOut:
    servicio = _service(db)
    laboratorio_id, equipo_id = servicio.resolver_equipo_id(token)
    set_tenant_context(db, laboratorio_id)
    equipo = EquipoRepositorySQLAlchemy(db).obtener_por_id(equipo_id)
    if equipo is None:
        raise TokenQrInvalido()
    foto_url = (
        _almacenamiento_fotos.url_vista_previa(equipo.foto_object_key)
        if equipo.foto_object_key
        else None
    )
    publico = servicio.a_vista_publica(equipo, foto_url)
    return EquipoPublicoOut(
        codigo_interno=publico.codigo_interno,
        nombre=publico.nombre,
        estado_operativo=publico.estado_operativo,
        marca=publico.marca,
        modelo=publico.modelo,
        foto_url=publico.foto_url,
        dado_de_baja=publico.dado_de_baja,
    )


@router.post("/publico/qr/{token}/incidencias", response_model=IncidenciaCreadaOut, status_code=201)
@limiter.limit("5/minute")
def reportar_incidencia(
    token: str, datos: ReportarIncidenciaRequest, request: Request, db: Session = Depends(get_db)
) -> IncidenciaCreadaOut:
    servicio = _service(db)
    laboratorio_id, equipo_id = servicio.resolver_equipo_id(token)
    set_tenant_context(db, laboratorio_id)

    incidencia = servicio.reportar_incidencia(
        laboratorio_id, equipo_id, datos.descripcion, datos.contacto_nombre, datos.contacto_medio
    )
    db.commit()
    return IncidenciaCreadaOut(id=str(incidencia.id), estado=incidencia.estado)


# ---------------------------------------------------------------------------
# Endpoints autenticados — consulta del propio QR desde la app
# ---------------------------------------------------------------------------


@router.get("/equipos/{equipo_id}/qr", response_model=QrInfoOut)
def obtener_info_qr(
    equipo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> QrInfoOut:
    qr_token = QrTokenRepositorySQLAlchemy(db).obtener_por_equipo(equipo_id)
    if qr_token is None:
        raise TokenQrInvalido()
    settings = get_settings()
    return QrInfoOut(token=qr_token.token, url_publica=f"{settings.frontend_base_url}/qr/{qr_token.token}")


@router.get("/equipos/{equipo_id}/qr-imagen")
def obtener_imagen_qr(
    equipo_id: uuid.UUID,
    db: Session = Depends(get_db),
    _usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> StreamingResponse:
    qr_token = QrTokenRepositorySQLAlchemy(db).obtener_por_equipo(equipo_id)
    if qr_token is None:
        raise TokenQrInvalido()

    settings = get_settings()
    url = f"{settings.frontend_base_url}/qr/{qr_token.token}"
    imagen = qrcode.make(url)
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="image/png")


@router.get("/qr/incidencias", response_model=list[IncidenciaQrOut])
def listar_incidencias(
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("equipos.leer")),
) -> list[IncidenciaQrOut]:
    """RF-QR-03 'Salidas' — mismo permiso de lectura que el resto del
    listado de Mantenimientos (ver `mantenimientos/presentation/router.py`),
    ya que es ahí donde esta lista se muestra como solicitudes pendientes
    de triage."""
    incidencias = _service(db).listar_incidencias(usuario.laboratorio_id)
    return [
        IncidenciaQrOut(
            id=str(i.id),
            equipo_id=str(i.equipo_id),
            equipo_codigo_interno=i.equipo_codigo_interno,
            equipo_nombre=i.equipo_nombre,
            descripcion=i.descripcion,
            contacto_nombre=i.contacto_nombre,
            contacto_medio=i.contacto_medio,
            estado=i.estado,
            creado_en=i.creado_en,
        )
        for i in incidencias
    ]


@router.patch("/qr/incidencias/{incidencia_id}/estado", response_model=IncidenciaCreadaOut)
def actualizar_estado_incidencia(
    incidencia_id: uuid.UUID,
    datos: ActualizarEstadoIncidenciaRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: UsuarioContexto = Depends(requiere_permiso("mantenimientos.crear")),
) -> IncidenciaCreadaOut:
    """Acción de triage — mismo permiso que registrar el mantenimiento al
    que esta incidencia normalmente da lugar."""
    actor = ActorContexto(
        usuario_id=usuario.id, ip_origen=ip_valida(request.client.host if request.client else None)
    )
    incidencia = _service(db).actualizar_estado_incidencia(incidencia_id, datos.estado, actor)
    db.commit()
    return IncidenciaCreadaOut(id=str(incidencia.id), estado=incidencia.estado)
