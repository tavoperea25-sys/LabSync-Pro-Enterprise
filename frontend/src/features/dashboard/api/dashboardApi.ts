import { apiFetch } from "@/lib/httpClient";

import type { ActividadReciente, EquipoCritico, Kpis } from "../types";

export async function obtenerKpis(): Promise<Kpis> {
  return apiFetch<Kpis>("/dashboard/kpis");
}

export async function obtenerEquiposCriticos(limite = 10): Promise<EquipoCritico[]> {
  return apiFetch<EquipoCritico[]>(`/dashboard/equipos-criticos?limite=${limite}`);
}

export async function obtenerActividadReciente(limite = 8): Promise<ActividadReciente[]> {
  return apiFetch<ActividadReciente[]>(`/dashboard/actividad-reciente?limite=${limite}`);
}
