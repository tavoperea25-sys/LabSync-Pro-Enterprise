import { apiFetch } from "@/lib/httpClient";

import type { FiltrosReporte, FormatoReporte, ReporteGenerado, TipoReporte, TipoReporteInfo, UrlDescarga } from "../types";

export async function listarTiposReporte(): Promise<TipoReporteInfo[]> {
  return apiFetch<TipoReporteInfo[]>("/reportes/tipos");
}

export async function listarHistorialReportes(): Promise<ReporteGenerado[]> {
  return apiFetch<ReporteGenerado[]>("/reportes/historial");
}

export async function generarReporte(
  tipo: TipoReporte,
  formato: FormatoReporte,
  filtros: FiltrosReporte,
): Promise<ReporteGenerado> {
  return apiFetch<ReporteGenerado>("/reportes/generar", {
    method: "POST",
    body: JSON.stringify({ tipo, formato, filtros }),
  });
}

export async function obtenerReporte(id: string): Promise<ReporteGenerado> {
  return apiFetch<ReporteGenerado>(`/reportes/${id}`);
}

export async function obtenerUrlDescarga(id: string): Promise<UrlDescarga> {
  return apiFetch<UrlDescarga>(`/reportes/${id}/descargar`);
}
