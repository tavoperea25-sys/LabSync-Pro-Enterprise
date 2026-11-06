from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valores de desarrollo de los campos sensibles — usados por el validador de
# abajo para detectar si alguno quedó sin cambiar en producción. Duplicados
# literalmente de los defaults de los campos correspondientes (no se puede
# leer el default de un campo Pydantic de forma genérica y fiable antes de
# que la instancia exista).
_SECRETOS_DEV_POR_DEFECTO = {
    "database_url": "postgresql+psycopg2://labsync_app:labsync_app@localhost:5432/labsync",
    "database_url_migraciones": "postgresql+psycopg2://labsync:labsync@localhost:5432/labsync",
    "minio_access_key": "labsync",
    "minio_secret_key": "labsync123",
}


class Settings(BaseSettings):
    """Configuración de la aplicación. Ver docs/16-seguridad.md."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    entorno: str = "desarrollo"

    # Conexión de RUNTIME de la aplicación — DEBE ser un rol NO superusuario
    # (`labsync_app`, creado por la migración inicial). Postgres ignora Row
    # Level Security por completo para superusuarios, incluso con FORCE
    # ROW LEVEL SECURITY — usar un rol con privilegios elevados aquí anula
    # silenciosamente todo el aislamiento multi-tenant (ver
    # docs/16-seguridad.md sección 3 y el hallazgo documentado en
    # tests/test_tenant_isolation.py).
    database_url: str = "postgresql+psycopg2://labsync_app:labsync_app@localhost:5432/labsync"

    # Conexión SOLO para Alembic (crear tablas, crear el rol `labsync_app`,
    # otorgarle privilegios). Requiere un rol con privilegios elevados
    # (superusuario o dueño del esquema) — nunca se usa para servir tráfico
    # de la aplicación.
    database_url_migraciones: str = "postgresql+psycopg2://labsync:labsync@localhost:5432/labsync"

    # Pool de conexiones del engine de runtime (`app/core/database.py`) —
    # Fase 2/M2 (docs/22-planificacion-fase2.md). Antes sin tuning explícito
    # (los defaults de SQLAlchemy quedaban implícitos, sin que nadie hubiera
    # verificado que encajan con el despliegue real). Los valores por
    # defecto de abajo SÍ son los defaults de SQLAlchemy (pool_size=5,
    # max_overflow=10, pool_timeout=30) — se dejan explícitos, no porque el
    # número deba cambiar, sino para que quede documentado por qué son
    # correctos para hoy: el despliegue actual (docs/13-arquitectura.md,
    # sin balanceador ni escalado horizontal) corre exactamente 2 procesos
    # con su propio pool — la API (`uvicorn` sin `--workers`, un solo
    # proceso) y el worker (contenedor separado que importa el mismo
    # engine). En el peor caso, 2 × (pool_size + max_overflow) = 30
    # conexiones simultáneas, más 1 conexión cruda de `ws_gateway.py` (LISTEN
    # de Postgres, fuera del pool) — bien por debajo del `max_connections`
    # por defecto de Postgres (100), dejando margen para `psql`/Alembic
    # sin necesidad de tocar nada. Si el despliegue cambia (más réplicas de
    # la API, un `max_connections` distinto), estos valores son el primer
    # lugar a ajustar.
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    # Única excepción a "son los defaults de SQLAlchemy": el default real es
    # -1 (nunca reciclar). Con un engine de vida larga (proceso único que
    # puede quedar ocioso tramos largos, uso interno de laboratorio, no
    # tráfico constante 24/7) una conexión puede quedar cerrada
    # silenciosamente por un firewall/timeout de red sin que el pool se
    # entere hasta el próximo checkout. `pool_pre_ping=True` (abajo, no
    # configurable a propósito) ya cubre la mayoría de esos casos con un
    # `SELECT 1` antes de reusar la conexión, pero recicla proactivamente
    # cada 30 min como segunda capa de defensa barata.
    db_pool_recycle_segundos: int = 1800

    jwt_private_key_path: str = ".keys/jwt_private.pem"
    jwt_public_key_path: str = ".keys/jwt_public.pem"
    jwt_algoritmo: str = "RS256"
    access_token_expira_minutos: int = 15
    refresh_token_expira_dias: int = 7
    # "Recordarme" en /login — duración de la cookie/sesión cuando el
    # usuario lo marca (en vez del `refresh_token_expira_dias` de arriba).
    # Antes vivía hardcodeado como `30` en el router y nunca llegaba a
    # `AuthService` ni a la fila de `sesiones` — ver auth_service.py.
    refresh_recordarme_dias: int = 30
    # Revisión de seguridad módulo Auth — hallazgo 1: varias peticiones con
    # 401 pueden disparar refresh concurrente con la misma cookie (de
    # distintas pestañas/dispositivos; una sola pestaña ya se deduplica en
    # httpClient.ts). Sin esta ventana, la segunda petición ve el refresh
    # token ya rotado por la primera y dispara la detección de reuso,
    # cerrando todas las sesiones del usuario por una carrera benigna. Ver
    # AuthService.refresh.
    refresh_ventana_gracia_segundos: int = 10
    # Hallazgo 5 — el bloqueo progresivo por intentos fallidos
    # (AuthService._registrar_intento_fallido) duplica el tiempo de espera
    # en cada intento adicional sin límite; sin techo, unos pocos intentos
    # más lo llevan a cientos de horas. 15 minutos por defecto.
    bloqueo_maximo_segundos: int = 900

    # RNF-SEG — auditoría 2026-07-31, hallazgo crítico C5: `/login` y
    # `/refresh` no tenían rate limiting (a diferencia de QR, ver
    # app/core/rate_limit.py), dejando el bloqueo progresivo por cuenta
    # (auth_service.py) como única defensa — no cubre credential-stuffing
    # distribuido entre muchas cuentas ni protege `/refresh`. Formato de
    # slowapi ("N/period"), igual que los límites ya usados en
    # app/modules/qr/presentation/router.py.
    rate_limit_login: str = "10/minute"
    rate_limit_refresh: str = "30/minute"

    # IPs (o redes CIDR) del/los reverse proxy(s) de confianza — solo si la
    # petición llega directamente desde una de estas IPs se honra
    # `X-Forwarded-For` para identificar al cliente real (ver
    # `uvicorn.middleware.proxy_headers.ProxyHeadersMiddleware`, wireado en
    # app/main.py). Vacío por defecto: hoy no hay proxy delante de la API
    # (docs/13-arquitectura.md documenta uno que aún no existe, ver hallazgo
    # C4 de la misma auditoría) — con la lista vacía, el rate limiting por
    # IP sigue basándose en la IP TCP real de la conexión, igual que hoy.
    trusted_proxy_ips: list[str] = []

    cors_origenes: list[str] = ["http://localhost:5173"]

    # Usado para construir la URL pública codificada en el QR (RF-QR-01) y
    # en el enlace mostrado en la ficha del equipo.
    frontend_base_url: str = "http://localhost:5173"

    # MinIO — dos endpoints deliberadamente distintos (ver
    # docs/13-arquitectura.md sección 5, "URLs prefirmadas"):
    # `_interno` es el nombre de servicio Docker, usado por el backend para
    # hablar con MinIO server-to-server (crear el bucket, copy_object al
    # duplicar un documento). `_publico` es el host que el NAVEGADOR puede
    # resolver, y es el que debe quedar embebido en cualquier URL prefirmada
    # devuelta por la API — si se usara el endpoint interno, el navegador
    # nunca podría resolver `minio` como hostname.
    minio_endpoint_interno: str = "minio:9000"
    minio_endpoint_publico: str = "localhost:9000"
    minio_access_key: str = "labsync"
    minio_secret_key: str = "labsync123"
    minio_secure: bool = False
    minio_bucket_documentos: str = "documentos"
    # Bucket separado para evidencias operativas (certificados de
    # calibración, evidencia fotográfica de mantenimientos) — distinto del
    # bucket "documentos" del Gestor Documental, ver docs/13-arquitectura.md
    # sección 5 ("un bucket lógico por tipo de contenido").
    minio_bucket_evidencias: str = "evidencias"
    # Reportes generados (síncronos pequeños no se suben aquí — se
    # transmiten directo en la respuesta; solo los asíncronos del worker,
    # que sí necesitan sobrevivir más allá de la petición HTTP que los
    # solicitó — ver Sprint 11, RNF-PERF-04).
    minio_bucket_reportes: str = "reportes"
    # Logo institucional del laboratorio (RF-CFG-04) — bucket propio, igual
    # criterio que los anteriores: un tipo de contenido lógico por bucket.
    minio_bucket_logos: str = "logos"
    # Fotografía de ficha técnica de un equipo (RF-EQ-01) — bucket propio,
    # mismo criterio; se resuelve con `url_vista_previa` (igual que el logo)
    # porque se muestra inline, nunca se descarga como adjunto.
    minio_bucket_fotos_equipos: str = "fotos-equipos"
    # Fotografía de perfil de usuario (RF-CFG-01) — mismo criterio.
    minio_bucket_fotos_usuarios: str = "fotos-usuarios"
    # Manual de usuario (PDF) de la ficha técnica de un equipo (RF-EQ-01) —
    # bucket propio, distinto del de fotografías (tipo de contenido distinto).
    minio_bucket_manuales_equipos: str = "manuales-equipos"

    @model_validator(mode="after")
    def _validar_secretos_en_produccion(self) -> "Settings":
        # Revisión de seguridad módulo Auth — hallazgo 3: docker-compose.yml
        # tenía valores de desarrollo como fallback de secretos reales
        # (contraseña de Postgres, de MinIO, clave KMS). Esto no detecta esa
        # situación por sí solo (ocurre a nivel de compose, antes de que
        # Python arranque) — complementa el cambio en docker-compose.yml
        # (`${VAR:?mensaje}`) con una segunda barrera: aunque algo llegue a
        # `Settings` con ENTORNO=produccion, si un campo sensible sigue
        # siendo literalmente el valor de desarrollo, la app se niega a
        # arrancar en vez de correr en producción con credenciales públicas.
        if self.entorno == "produccion":
            conservados = [
                campo
                for campo, valor_dev in _SECRETOS_DEV_POR_DEFECTO.items()
                if getattr(self, campo) == valor_dev
            ]
            if conservados:
                raise ValueError(
                    "ENTORNO=produccion pero los siguientes secretos siguen en su "
                    f"valor de desarrollo por defecto: {', '.join(conservados)}. "
                    "Configuralos vía variables de entorno/.env antes de arrancar "
                    "en producción."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
