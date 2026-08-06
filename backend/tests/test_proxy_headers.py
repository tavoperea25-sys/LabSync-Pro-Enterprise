"""Regresión de Fase 0 / C5 — compatibilidad con despliegues detrás de un
reverse proxy de confianza. Ver app/main.py (`ProxyHeadersMiddleware`,
`settings.trusted_proxy_ips`) y app/core/rate_limit.py (`get_remote_address`,
la función que usa slowapi para identificar al cliente).

`settings.trusted_proxy_ips` se lee una sola vez al construir `app` (igual
que `cors_origenes` de CORSMiddleware) — no es reconfigurable en caliente
por request, así que no se puede probar contra `app.main.app` ya construida
con monkeypatch. Se arma acá una app mínima equivalente, con el mismo
middleware y la misma configuración que usaría en producción, para probar
el comportamiento de forma aislada."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


def _app_con_proxy_de_confianza(trusted_hosts: list[str]) -> FastAPI:
    app = FastAPI()

    @app.get("/ip")
    def ver_ip(request: Request) -> dict[str, str | None]:
        return {"ip": request.client.host if request.client else None}

    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=trusted_hosts)
    return app


def test_ip_del_cliente_real_se_usa_cuando_no_hay_proxy_configurado():
    """Configuración por defecto del proyecto (`trusted_proxy_ips=[]`) — sin
    proxy de confianza declarado, `X-Forwarded-For` se ignora por completo y
    se usa la IP de la conexión TCP entrante, exactamente el comportamiento
    de hoy (sin este middleware)."""
    client = TestClient(_app_con_proxy_de_confianza(trusted_hosts=[]))

    respuesta = client.get("/ip", headers={"X-Forwarded-For": "203.0.113.7"})

    assert respuesta.json()["ip"] != "203.0.113.7"


def test_x_forwarded_for_se_honra_solo_desde_un_proxy_de_confianza():
    """Con la IP del proxy explícitamente en `trusted_proxy_ips`, la IP
    reportada pasa a ser la del cliente real detrás de ese proxy — esto es
    lo que hace que el rate limiting por IP (get_remote_address) siga
    identificando correctamente a cada cliente cuando la API está detrás de
    un reverse proxy, en vez de tratar a todos los clientes como una sola
    IP (la del proxy)."""
    client = TestClient(_app_con_proxy_de_confianza(trusted_hosts=["testclient"]))

    respuesta = client.get("/ip", headers={"X-Forwarded-For": "203.0.113.7"})

    assert respuesta.json()["ip"] == "203.0.113.7"


def test_x_forwarded_for_no_se_confia_desde_un_peer_no_autorizado():
    """Un cliente que no es un proxy de confianza no puede spoofear su IP
    inyectando `X-Forwarded-For` — si se confiara ciegamente en el header
    (lo que hace `slowapi.util.get_ipaddr`, deliberadamente NO usado en este
    proyecto), cualquiera podría burlar el rate limiting por IP mandando un
    valor distinto en cada petición."""
    # "testclient" (la IP simulada del TestClient) NO está en la lista de
    # confianza — la petición debe tratarse como si viniera directo, sin
    # honrar el header que el propio "atacante" mandó.
    client = TestClient(_app_con_proxy_de_confianza(trusted_hosts=["10.0.0.5"]))

    respuesta = client.get("/ip", headers={"X-Forwarded-For": "203.0.113.7"})

    assert respuesta.json()["ip"] != "203.0.113.7"
