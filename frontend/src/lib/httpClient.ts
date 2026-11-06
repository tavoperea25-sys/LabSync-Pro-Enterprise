/**
 * Cliente HTTP mínimo para la API de LabSync Pro.
 *
 * El access token se guarda SOLO en memoria (nunca en localStorage) — ver
 * docs/16-seguridad.md: el refresh token vive en una cookie httpOnly que
 * el navegador envía automáticamente (`credentials: "include"`), fuera del
 * alcance de JavaScript y por tanto de un eventual XSS.
 */

let accessTokenEnMemoria: string | null = null;

export function setAccessToken(token: string | null): void {
  accessTokenEnMemoria = token;
}

export function getAccessToken(): string | null {
  return accessTokenEnMemoria;
}

export class ApiError extends Error {
  constructor(
    public codigo: string,
    message: string,
    public status: number,
    public detalles?: Record<string, unknown>,
  ) {
    super(message);
  }
}

async function parseErrorEnvelope(response: Response): Promise<ApiError> {
  try {
    const cuerpo = await response.json();
    const error = cuerpo?.error ?? {};
    return new ApiError(
      error.codigo ?? "error_desconocido",
      error.mensaje ?? "Ocurrió un error inesperado.",
      response.status,
      error.detalles,
    );
  } catch {
    return new ApiError("error_desconocido", "Ocurrió un error inesperado.", response.status);
  }
}

interface RequestOptions extends RequestInit {
  reintentarConRefresh?: boolean;
}

export async function apiFetch<T>(ruta: string, options: RequestOptions = {}): Promise<T> {
  const { reintentarConRefresh = true, headers, ...resto } = options;

  const response = await fetch(`/api/v1${ruta}`, {
    ...resto,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(accessTokenEnMemoria ? { Authorization: `Bearer ${accessTokenEnMemoria}` } : {}),
      ...headers,
    },
  });

  if (response.status === 401 && reintentarConRefresh && ruta !== "/auth/refresh") {
    const renovado = await intentarRefresh();
    if (renovado) {
      return apiFetch<T>(ruta, { ...options, reintentarConRefresh: false });
    }
  }

  if (!response.ok) {
    throw await parseErrorEnvelope(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/** Para respuestas binarias (export .xlsx, imagen QR) — mismo manejo de
 * auth/refresh que `apiFetch`, pero sin forzar `Content-Type`/parseo JSON. */
export async function apiFetchBlob(ruta: string, options: RequestOptions = {}): Promise<Blob> {
  const { reintentarConRefresh = true, headers, ...resto } = options;

  const response = await fetch(`/api/v1${ruta}`, {
    ...resto,
    credentials: "include",
    headers: {
      ...(accessTokenEnMemoria ? { Authorization: `Bearer ${accessTokenEnMemoria}` } : {}),
      ...headers,
    },
  });

  if (response.status === 401 && reintentarConRefresh) {
    const renovado = await intentarRefresh();
    if (renovado) {
      return apiFetchBlob(ruta, { ...options, reintentarConRefresh: false });
    }
  }

  if (!response.ok) {
    throw await parseErrorEnvelope(response);
  }

  return response.blob();
}

// Revisión de seguridad módulo Auth, hallazgo 1 — varias peticiones que
// reciben 401 casi a la vez disparaban cada una su propio POST
// /auth/refresh con la misma cookie. El backend rota el refresh token en
// cada llamada, así que la segunda veía el token ya usado por la primera y
// lo trataba como un posible robo, cerrando todas las sesiones del
// usuario por una carrera benigna (ver AuthService.refresh). Single-flight:
// mientras haya un refresh en curso, cualquier llamada adicional espera esa
// MISMA promesa en vez de disparar una petición nueva.
let refrescoEnCurso: Promise<boolean> | null = null;

async function intentarRefresh(): Promise<boolean> {
  if (refrescoEnCurso) {
    return refrescoEnCurso;
  }
  refrescoEnCurso = ejecutarRefresh().finally(() => {
    refrescoEnCurso = null;
  });
  return refrescoEnCurso;
}

async function ejecutarRefresh(): Promise<boolean> {
  try {
    const respuesta = await fetch("/api/v1/auth/refresh", { method: "POST", credentials: "include" });
    if (!respuesta.ok) return false;
    const datos = await respuesta.json();
    setAccessToken(datos.access_token);
    return true;
  } catch {
    return false;
  }
}
