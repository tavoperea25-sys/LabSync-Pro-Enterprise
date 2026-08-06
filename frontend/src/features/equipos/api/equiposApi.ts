import { apiFetch, apiFetchBlob } from "@/lib/httpClient";

import type {
  Area,
  CategoriaEquipo,
  Equipo,
  EquipoRequest,
  FiltrosEquipos,
  HistorialEntrada,
  PaginaEquipos,
  QrInfo,
  UrlFoto,
} from "../types";

function construirQuery(filtros: FiltrosEquipos): string {
  const params = new URLSearchParams();
  if (filtros.q) params.set("q", filtros.q);
  if (filtros.categoria_id) params.set("categoria_id", filtros.categoria_id);
  if (filtros.area_id) params.set("area_id", filtros.area_id);
  if (filtros.estado_operativo) params.set("estado_operativo", filtros.estado_operativo);
  params.set("pagina", String(filtros.pagina ?? 1));
  return params.toString();
}

export async function listarEquipos(filtros: FiltrosEquipos): Promise<PaginaEquipos> {
  return apiFetch<PaginaEquipos>(`/equipos?${construirQuery(filtros)}`);
}

export async function obtenerEquipo(id: string): Promise<Equipo> {
  return apiFetch<Equipo>(`/equipos/${id}`);
}

export async function crearEquipo(datos: EquipoRequest): Promise<Equipo> {
  return apiFetch<Equipo>("/equipos", { method: "POST", body: JSON.stringify(datos) });
}

export async function actualizarEquipo(id: string, datos: EquipoRequest): Promise<Equipo> {
  return apiFetch<Equipo>(`/equipos/${id}`, { method: "PATCH", body: JSON.stringify(datos) });
}

export async function eliminarEquipo(id: string): Promise<void> {
  return apiFetch<void>(`/equipos/${id}`, { method: "DELETE" });
}

export async function listarCategorias(): Promise<CategoriaEquipo[]> {
  return apiFetch<CategoriaEquipo[]>("/categorias-equipo");
}

export async function listarAreas(): Promise<Area[]> {
  return apiFetch<Area[]>("/areas");
}

export async function duplicarEquipo(id: string): Promise<Equipo> {
  return apiFetch<Equipo>(`/equipos/${id}/duplicar`, { method: "POST" });
}

export async function obtenerHistorial(id: string): Promise<HistorialEntrada[]> {
  return apiFetch<HistorialEntrada[]>(`/equipos/${id}/historial`);
}

export async function obtenerQrInfo(id: string): Promise<QrInfo> {
  return apiFetch<QrInfo>(`/equipos/${id}/qr`);
}

export async function obtenerImagenQrBlob(id: string): Promise<Blob> {
  return apiFetchBlob(`/equipos/${id}/qr-imagen`);
}

export async function exportarEquiposBlob(filtros: FiltrosEquipos): Promise<Blob> {
  return apiFetchBlob(`/equipos/export?${construirQuery(filtros)}`);
}

export async function solicitarUrlFoto(
  nombreArchivo: string,
  tipoMime: string,
  tamanoBytes: number,
): Promise<UrlFoto> {
  return apiFetch<UrlFoto>("/equipos/upload-url/foto", {
    method: "POST",
    body: JSON.stringify({ nombre_archivo: nombreArchivo, tipo_mime: tipoMime, tamano_bytes: tamanoBytes }),
  });
}

export async function solicitarUrlManual(
  nombreArchivo: string,
  tipoMime: string,
  tamanoBytes: number,
): Promise<UrlFoto> {
  return apiFetch<UrlFoto>("/equipos/upload-url/manual", {
    method: "POST",
    body: JSON.stringify({ nombre_archivo: nombreArchivo, tipo_mime: tipoMime, tamano_bytes: tamanoBytes }),
  });
}
