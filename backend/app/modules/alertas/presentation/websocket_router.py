"""Gateway WebSocket de notificaciones — RF-ALT-05/06.

Fase 2/M5 (docs/22-planificacion-fase2.md): el navegador no permite fijar
la cabecera Authorization en el handshake de WebSocket, pero sí permite
ofrecer valores arbitrarios en `Sec-WebSocket-Protocol` (segundo argumento
del constructor `WebSocket` del navegador) — a diferencia de un query param,
ese valor no queda en la URL de la conexión, así que no aparece en logs de
acceso estándar ni en los de un futuro reverse proxy que sí registre líneas
de petición completas (docs/13-arquitectura.md sección 11). El cliente
ofrece dos "subprotocolos": un marcador fijo (`access_token`) seguido del
token real — mismo patrón ya usado por otros gateways de WebSocket con
autenticación (p. ej. AWS AppSync). Sigue siendo el mismo access token de
corta duración (15 min, ver `app/core/security.py`) que ya se usa en las
peticiones REST — no se introduce un mecanismo de autenticación nuevo, solo
un transporte distinto para el mismo token.

Alternativas consideradas y descartadas (ver informe de cierre de M5):
- Ticket de un solo uso emitido por HTTP antes de abrir el WebSocket: sigue
  necesitando un valor en el query string (más corto/efímero, pero no
  elimina el problema), y exige un almacén de tickets con expiración que
  hoy no tiene dónde vivir (no hay Redis en este stack) y que además
  quedaría atado a un solo proceso — la misma limitación ya documentada de
  `ConnectionManager` (un backend sin réplicas). Complejidad nueva por un
  beneficio marginal frente a la opción elegida.
- Reusar la cookie httpOnly del refresh token (`app/modules/auth/presentation/router.py`):
  técnicamente el navegador la enviaría sola en el handshake, pero mezclaría
  un credential de larga duración (7 días, pensado para tocar la red solo en
  `/auth/refresh`) con un uso de alta frecuencia (cada reconexión de
  WebSocket) — debilita la separación access/refresh a propósito.
- Migrar todo el esquema de autenticación a cookies httpOnly: resolvería
  esto de raíz, pero es un rediseño de todo el flujo REST (no solo
  WebSocket) y abre superficie de CSRF que hoy no existe (el Bearer token en
  header no es vulnerable a CSRF) — desproporcionado para este hallazgo."""

from __future__ import annotations

import uuid

import jwt as pyjwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import decodificar_access_token
from app.core.ws_gateway import manager

router = APIRouter(tags=["alertas"])

_MARCADOR_SUBPROTOCOLO = "access_token"


def _extraer_token(websocket: WebSocket) -> str:
    """El navegador envía los subprotocolos que el cliente ofreció como una
    lista separada por comas en la cabecera `Sec-WebSocket-Protocol`. Se
    espera exactamente `["access_token", <token>]` — cualquier otra forma
    (cabecera ausente, sin el marcador, con partes de más o de menos) se
    trata como token vacío, que `decodificar_access_token` ya rechaza."""
    crudo = websocket.headers.get("sec-websocket-protocol", "")
    partes = [p.strip() for p in crudo.split(",")] if crudo else []
    if len(partes) == 2 and partes[0] == _MARCADOR_SUBPROTOCOLO:
        return partes[1]
    return ""


@router.websocket("/ws/v1/notificaciones")
async def notificaciones_ws(websocket: WebSocket) -> None:
    try:
        claims = decodificar_access_token(_extraer_token(websocket))
        laboratorio_id = uuid.UUID(claims["laboratorio_id"])
    except (pyjwt.PyJWTError, KeyError, ValueError):
        await websocket.close(code=4401)
        return

    await manager.conectar(laboratorio_id, websocket, subprotocol=_MARCADOR_SUBPROTOCOLO)
    try:
        while True:
            # No se espera contenido del cliente — solo se mantiene la
            # conexión viva y se detecta la desconexión. Un mensaje
            # entrante (p. ej. un "ping" del cliente) simplemente se ignora.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.desconectar(laboratorio_id, websocket)
