import { apiFetch } from "@/lib/httpClient";

import type {
  EquipoPublico,
  EstadoIncidencia,
  IncidenciaCreada,
  IncidenciaQr,
  IncidenciaRequest,
} from "../types";

export async function obtenerEquipoPorQr(token: string): Promise<EquipoPublico> {
  return apiFetch<EquipoPublico>(`/publico/qr/${token}`);
}

export async function reportarIncidencia(token: string, datos: IncidenciaRequest): Promise<IncidenciaCreada> {
  return apiFetch<IncidenciaCreada>(`/publico/qr/${token}/incidencias`, {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export async function listarIncidencias(): Promise<IncidenciaQr[]> {
  return apiFetch<IncidenciaQr[]>("/qr/incidencias");
}

export async function actualizarEstadoIncidencia(
  incidenciaId: string,
  estado: EstadoIncidencia,
): Promise<IncidenciaCreada> {
  return apiFetch<IncidenciaCreada>(`/qr/incidencias/${incidenciaId}/estado`, {
    method: "PATCH",
    body: JSON.stringify({ estado }),
  });
}
