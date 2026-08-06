import { apiFetch } from "@/lib/httpClient";

import type { Alerta, EstadoAlerta, PaginaAlertas } from "../types";

/** RNF-PERF-03 — pagina de verdad; `tamanoPagina` permite que
 * `NotificacionesBell` pida una página chica (8) directamente al servidor
 * en vez de traer todo y recortar del lado del cliente. */
export async function listarAlertas(
  estado?: EstadoAlerta,
  pagina?: number,
  tamanoPagina?: number,
): Promise<PaginaAlertas> {
  const params = new URLSearchParams();
  if (estado) params.set("estado", estado);
  if (pagina) params.set("pagina", String(pagina));
  if (tamanoPagina) params.set("tamano_pagina", String(tamanoPagina));
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<PaginaAlertas>(`/alertas${query}`);
}

export async function contarActivas(): Promise<{ activas: number }> {
  return apiFetch("/alertas/contar-activas");
}

export async function marcarLeida(id: string): Promise<Alerta> {
  return apiFetch<Alerta>(`/alertas/${id}/leer`, { method: "POST" });
}

export async function resolverManual(id: string): Promise<Alerta> {
  return apiFetch<Alerta>(`/alertas/${id}/resolver`, { method: "POST" });
}
