import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch, setAccessToken } from "./httpClient";

/** Revisión de seguridad módulo Auth, hallazgo 1 — varias peticiones que
 * reciben 401 casi a la vez disparaban cada una su propio POST
 * /auth/refresh con la misma cookie, lo que en el backend dispara la
 * detección de reuso de refresh token y revoca todas las sesiones por una
 * carrera benigna. `intentarRefresh` ahora deduplica (single-flight):
 * mientras haya un refresh en curso, cualquier llamada adicional espera esa
 * MISMA promesa en vez de disparar una petición nueva. */
describe("httpClient — refresh concurrente (single-flight)", () => {
  beforeEach(() => {
    setAccessToken(null);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("dos peticiones con 401 simultáneas disparan un solo POST /auth/refresh", async () => {
    let llamadasRefresh = 0;

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url.includes("/auth/refresh")) {
        llamadasRefresh += 1;
        return new Response(JSON.stringify({ access_token: "token-nuevo" }), { status: 200 });
      }

      const headers = new Headers(init?.headers);
      if (headers.get("Authorization") === "Bearer token-nuevo") {
        return new Response(JSON.stringify({ ok: true, ruta: url }), { status: 200 });
      }

      // Sin token válido todavía (o con el viejo) — la API rechaza con 401,
      // como pasaría con un access token vencido.
      return new Response(null, { status: 401 });
    });
    vi.stubGlobal("fetch", fetchMock);

    const [a, b] = await Promise.all([
      apiFetch<{ ok: boolean }>("/algo-protegido-a"),
      apiFetch<{ ok: boolean }>("/algo-protegido-b"),
    ]);

    expect(a.ok).toBe(true);
    expect(b.ok).toBe(true);
    // Antes de este fix, cada una de las dos peticiones hubiera disparado
    // su propio /auth/refresh — exactamente lo que se quiere evitar.
    expect(llamadasRefresh).toBe(1);
  });

  it("un refresh posterior (ya resuelto el anterior) sí dispara una llamada nueva", async () => {
    let llamadasRefresh = 0;

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url.includes("/auth/refresh")) {
        llamadasRefresh += 1;
        return new Response(JSON.stringify({ access_token: `token-${llamadasRefresh}` }), {
          status: 200,
        });
      }

      const headers = new Headers(init?.headers);
      if (headers.get("Authorization") === `Bearer token-${llamadasRefresh}`) {
        return new Response(JSON.stringify({ ok: true }), { status: 200 });
      }

      return new Response(null, { status: 401 });
    });
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/algo-protegido");
    // Simula que el access token en memoria quedó obsoleto (p. ej. venció)
    // antes de la segunda llamada — si no, seguiría siendo válido para el
    // mock y nunca volvería a pedir un 401/refresh, sin que eso diga nada
    // sobre el single-flight en sí.
    setAccessToken(null);
    await apiFetch("/algo-protegido");

    // Dos llamadas secuenciales (no concurrentes) sí deben renovar dos
    // veces — el single-flight solo deduplica mientras hay una EN CURSO,
    // no refrescos futuros ya resueltos.
    expect(llamadasRefresh).toBe(2);
  });
});
