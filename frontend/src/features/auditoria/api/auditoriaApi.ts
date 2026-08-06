import { apiFetch, apiFetchBlob } from "@/lib/httpClient";

import type { FiltrosAuditoria, FormatoExportacion, PaginaAuditoria, ValoresFiltro } from "../types";

function aParams(filtros: FiltrosAuditoria): string {
  const params = new URLSearchParams();
  if (filtros.usuario_id) params.set("usuario_id", filtros.usuario_id);
  if (filtros.modulo) params.set("modulo", filtros.modulo);
  if (filtros.accion) params.set("accion", filtros.accion);
  if (filtros.desde) params.set("desde", filtros.desde);
  if (filtros.hasta) params.set("hasta", filtros.hasta);
  return params.toString();
}

export async function listarAuditoria(filtros: FiltrosAuditoria): Promise<PaginaAuditoria> {
  const params = aParams(filtros);
  return apiFetch<PaginaAuditoria>(
    `/auditoria?${params ? `${params}&` : ""}pagina=${filtros.pagina ?? 1}`,
  );
}

export async function obtenerValoresFiltro(): Promise<ValoresFiltro> {
  return apiFetch<ValoresFiltro>("/auditoria/valores-filtro");
}

export async function exportarAuditoria(formato: FormatoExportacion, filtros: FiltrosAuditoria): Promise<Blob> {
  const params = aParams(filtros);
  return apiFetchBlob(`/auditoria/export?formato=${formato}${params ? `&${params}` : ""}`);
}
