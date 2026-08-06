import { apiFetch } from "@/lib/httpClient";

import type { DatosEventoCalendario, EventoCalendario, TipoEvento } from "../types";

export interface FiltrosCalendario {
  desde: string;
  hasta: string;
  tipo?: TipoEvento;
  areaId?: string;
  responsableId?: string;
}

export async function listarEventos(filtros: FiltrosCalendario): Promise<EventoCalendario[]> {
  const params = new URLSearchParams({ desde: filtros.desde, hasta: filtros.hasta });
  if (filtros.tipo) params.set("tipo", filtros.tipo);
  if (filtros.areaId) params.set("area_id", filtros.areaId);
  if (filtros.responsableId) params.set("responsable_id", filtros.responsableId);
  return apiFetch<EventoCalendario[]>(`/calendario/eventos?${params.toString()}`);
}

export async function crearEvento(datos: DatosEventoCalendario): Promise<EventoCalendario> {
  return apiFetch<EventoCalendario>("/calendario/eventos", { method: "POST", body: JSON.stringify(datos) });
}

export async function actualizarEvento(id: string, datos: DatosEventoCalendario): Promise<EventoCalendario> {
  return apiFetch<EventoCalendario>(`/calendario/eventos/${id}`, {
    method: "PATCH",
    body: JSON.stringify(datos),
  });
}

export async function eliminarEvento(id: string): Promise<void> {
  await apiFetch<void>(`/calendario/eventos/${id}`, { method: "DELETE" });
}
