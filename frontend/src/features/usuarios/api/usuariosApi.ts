import { apiFetch } from "@/lib/httpClient";

import type {
  DatosActualizarUsuario,
  DatosCrearUsuario,
  PaginaUsuarios,
  Rol,
  Sesion,
  Usuario,
} from "../types";

export async function listarRoles(): Promise<Rol[]> {
  return apiFetch<Rol[]>("/roles");
}

export async function listarUsuarios(pagina = 1, tamanoPagina?: number): Promise<PaginaUsuarios> {
  const params = new URLSearchParams({ pagina: String(pagina) });
  if (tamanoPagina) params.set("tamano_pagina", String(tamanoPagina));
  return apiFetch<PaginaUsuarios>(`/usuarios?${params.toString()}`);
}

export async function crearUsuario(datos: DatosCrearUsuario): Promise<Usuario> {
  return apiFetch<Usuario>("/usuarios", { method: "POST", body: JSON.stringify(datos) });
}

export async function actualizarUsuario(id: string, datos: DatosActualizarUsuario): Promise<Usuario> {
  return apiFetch<Usuario>(`/usuarios/${id}`, { method: "PATCH", body: JSON.stringify(datos) });
}

export async function activarUsuario(id: string): Promise<Usuario> {
  return apiFetch<Usuario>(`/usuarios/${id}/activar`, { method: "POST" });
}

export async function desactivarUsuario(id: string): Promise<Usuario> {
  return apiFetch<Usuario>(`/usuarios/${id}/desactivar`, { method: "POST" });
}

export async function asignarRoles(id: string, rolIds: string[]): Promise<Usuario> {
  return apiFetch<Usuario>(`/usuarios/${id}/roles`, {
    method: "PUT",
    body: JSON.stringify({ rol_ids: rolIds }),
  });
}

export async function listarSesiones(usuarioId: string): Promise<Sesion[]> {
  return apiFetch<Sesion[]>(`/usuarios/${usuarioId}/sesiones`);
}

export async function cerrarSesion(usuarioId: string, sesionId: string): Promise<void> {
  await apiFetch<void>(`/usuarios/${usuarioId}/sesiones/${sesionId}`, { method: "DELETE" });
}
