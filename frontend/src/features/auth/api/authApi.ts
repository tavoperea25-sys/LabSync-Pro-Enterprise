import { apiFetch, setAccessToken } from "@/lib/httpClient";

import type { LoginRequest, LoginResponse, Usuario } from "../types";

export async function login(datos: LoginRequest): Promise<LoginResponse> {
  const respuesta = await apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(datos),
    reintentarConRefresh: false,
  });
  setAccessToken(respuesta.access_token);
  return respuesta;
}

export async function logout(): Promise<void> {
  await apiFetch<void>("/auth/logout", { method: "POST", reintentarConRefresh: false });
  setAccessToken(null);
}

export async function obtenerUsuarioActual(): Promise<Usuario> {
  return apiFetch<Usuario>("/auth/me");
}
