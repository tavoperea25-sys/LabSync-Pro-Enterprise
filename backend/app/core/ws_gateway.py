"""Gateway de WebSocket para notificaciones en tiempo real (RF-ALT-05/06).

Puente PostgreSQL LISTEN/NOTIFY -> WebSocket: el worker (proceso Docker
separado, ver `app/worker/main.py`) escribe en el outbox `notificaciones_pendientes`
y hace `pg_notify`; ESTE proceso (la API) mantiene las conexiones WebSocket
abiertas y reenvía. Ningún módulo de negocio empuja un WebSocket
directamente desde su transacción — todo pasa por el outbox, así el
comportamiento es el mismo si el listener está caído (el frontend hace
fallback a polling de `GET /alertas/contar-activas` cada 30s en ese caso,
ver docs/13-arquitectura.md sección "tiempo real").

`LISTEN` bloquea el socket que lo ejecuta, así que corre en un hilo aparte
con su propia conexión psycopg2 (fuera del pool de SQLAlchemy) — no hay
forma nativa de esperar una notificación de Postgres dentro del loop de
asyncio sin un driver async (asyncpg), que este proyecto no usa."""

from __future__ import annotations

import asyncio
import json
import logging
import select
import threading
import uuid

import psycopg2
from fastapi import WebSocket

from app.core.config import get_settings

CANAL_ALERTAS = "canal_alertas"
_logger = logging.getLogger(__name__)


class ConnectionManager:
    """Registro en memoria de conexiones WebSocket activas por laboratorio.

    Vive solo en este proceso — si hay más de un worker de uvicorn, cada
    uno tiene su propio registro y su propio listener; un cliente conectado
    al worker A no recibe eventos generados vía el worker B. Aceptable para
    v1 (un solo proceso API), documentado como límite conocido."""

    def __init__(self) -> None:
        self._conexiones: dict[uuid.UUID, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def conectar(
        self, laboratorio_id: uuid.UUID, ws: WebSocket, subprotocol: str | None = None
    ) -> None:
        # Fase 2/M5 — si el cliente ofreció subprotocolos (ver
        # `websocket_router.py`), el navegador espera que el servidor elija
        # uno de vuelta en la respuesta del handshake; sin eco, algunos
        # navegadores tratan la conexión como fallida aunque el servidor la
        # haya aceptado (visible en los logs de acceso como "connection
        # open" seguido de un cierre inmediato del lado del cliente).
        await ws.accept(subprotocol=subprotocol)
        async with self._lock:
            self._conexiones.setdefault(laboratorio_id, set()).add(ws)

    async def desconectar(self, laboratorio_id: uuid.UUID, ws: WebSocket) -> None:
        async with self._lock:
            conexiones = self._conexiones.get(laboratorio_id)
            if conexiones is not None:
                conexiones.discard(ws)
                if not conexiones:
                    del self._conexiones[laboratorio_id]

    async def emitir(self, laboratorio_id: uuid.UUID, mensaje: dict) -> None:
        async with self._lock:
            conexiones = list(self._conexiones.get(laboratorio_id, ()))
        texto = json.dumps(mensaje)
        for ws in conexiones:
            try:
                await ws.send_text(texto)
            except Exception:
                _logger.warning("Fallo al enviar por WebSocket, se ignora (el cliente ya reconectará).")


manager = ConnectionManager()

_hilo: threading.Thread | None = None
_detener = threading.Event()


def _dsn_raw() -> str:
    # psycopg2.connect acepta el esquema "postgresql://" pero no el sufijo
    # "+psycopg2" que SQLAlchemy exige en su propia URL de conexión.
    return get_settings().database_url.replace("postgresql+psycopg2://", "postgresql://")


def _loop_listener(bucle_asyncio: asyncio.AbstractEventLoop) -> None:
    conn = psycopg2.connect(_dsn_raw())
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(f"LISTEN {CANAL_ALERTAS};")
    _logger.info("Listener de '%s' iniciado.", CANAL_ALERTAS)

    try:
        while not _detener.is_set():
            if select.select([conn], [], [], 5) == ([], [], []):
                continue
            conn.poll()
            while conn.notifies:
                notificacion = conn.notifies.pop(0)
                try:
                    payload = json.loads(notificacion.payload)
                    laboratorio_id = uuid.UUID(payload.pop("laboratorio_id"))
                except (ValueError, KeyError, TypeError):
                    _logger.warning("Payload de NOTIFY inválido, se descarta: %s", notificacion.payload)
                    continue
                asyncio.run_coroutine_threadsafe(manager.emitir(laboratorio_id, payload), bucle_asyncio)
    finally:
        cur.close()
        conn.close()


async def iniciar_listener() -> None:
    global _hilo
    _detener.clear()
    bucle = asyncio.get_running_loop()
    _hilo = threading.Thread(target=_loop_listener, args=(bucle,), daemon=True, name="pg-listen-alertas")
    _hilo.start()


async def detener_listener() -> None:
    _detener.set()
