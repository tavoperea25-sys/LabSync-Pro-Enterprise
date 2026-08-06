from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.almacenamiento_minio import AlmacenamientoMinIO
from app.core.config import get_settings
from app.core.errors import registrar_manejadores_de_error
from app.core.logging import TraceIdMiddleware, configurar_logging
from app.core.rate_limit import limiter
from app.core.ws_gateway import detener_listener, iniciar_listener
from app.modules.alertas.presentation.router import router as alertas_router
from app.modules.alertas.presentation.websocket_router import router as alertas_ws_router
from app.modules.auditoria.presentation.router import router as auditoria_router
from app.modules.auth.presentation.router import router as auth_router
from app.modules.auth.presentation.usuarios_router import router as usuarios_router
from app.modules.busqueda.presentation.router import router as busqueda_router
from app.modules.calendario.presentation.router import router as calendario_router
from app.modules.calibraciones.presentation.router import router as calibraciones_router
from app.modules.configuracion.presentation.router import router as configuracion_router
from app.modules.dashboard.presentation.router import router as dashboard_router
from app.modules.documentos.presentation.router import router as documentos_router
from app.modules.equipos.presentation.router import router as equipos_router
from app.modules.mantenimientos.presentation.router import router as mantenimientos_router
from app.modules.qr.presentation.router import router as qr_router
from app.modules.reportes.presentation.router import router as reportes_router

settings = get_settings()
configurar_logging()

app = FastAPI(title="LabSync Pro Enterprise API", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
# slowapi tipa su handler específicamente para RateLimitExceeded, más
# estrecho que la firma genérica que espera Starlette — no afecta en
# runtime (documentado, fricción conocida entre ambas librerías).
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origenes,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Añadida al final = más externa (Starlette invierte el orden de registro
# al construir la pila) — así el trace_id queda fijado antes de que
# cualquier otro middleware corra, y la cabecera de respuesta sobrevive
# incluso si SlowAPI corta la petición por rate limit.
app.add_middleware(TraceIdMiddleware)

# Más externa todavía que TraceIdMiddleware: debe reescribir `request.client`
# ANTES de que SlowAPI lea la IP (`get_remote_address`, app/core/rate_limit.py)
# para identificar al cliente real detrás de un proxy. Solo confía en
# `X-Forwarded-For` cuando la conexión TCP entrante viene de una IP listada
# en `trusted_proxy_ips` — con la lista vacía (default hoy, sin proxy
# desplegado) equivale a no hacer nada, sigue usando la IP de la conexión.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.trusted_proxy_ips)

registrar_manejadores_de_error(app)

app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(equipos_router)
app.include_router(qr_router)
app.include_router(dashboard_router)
app.include_router(documentos_router)
app.include_router(calibraciones_router)
app.include_router(mantenimientos_router)
app.include_router(alertas_router)
app.include_router(alertas_ws_router)
app.include_router(calendario_router)
app.include_router(busqueda_router)
app.include_router(auditoria_router)
app.include_router(reportes_router)
app.include_router(configuracion_router)


@app.on_event("startup")
def _asegurar_buckets() -> None:
    """MinIO no crea buckets solo — sin esto, la primera subida fallaría
    con "bucket does not exist" en un ambiente recién levantado."""
    AlmacenamientoMinIO(settings.minio_bucket_documentos).asegurar_bucket()
    AlmacenamientoMinIO(settings.minio_bucket_evidencias).asegurar_bucket()
    AlmacenamientoMinIO(settings.minio_bucket_reportes).asegurar_bucket()
    AlmacenamientoMinIO(settings.minio_bucket_logos).asegurar_bucket()
    AlmacenamientoMinIO(settings.minio_bucket_fotos_equipos).asegurar_bucket()
    AlmacenamientoMinIO(settings.minio_bucket_fotos_usuarios).asegurar_bucket()
    AlmacenamientoMinIO(settings.minio_bucket_manuales_equipos).asegurar_bucket()


@app.on_event("startup")
async def _iniciar_listener_ws() -> None:
    await iniciar_listener()


@app.on_event("shutdown")
async def _detener_listener_ws() -> None:
    await detener_listener()


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
