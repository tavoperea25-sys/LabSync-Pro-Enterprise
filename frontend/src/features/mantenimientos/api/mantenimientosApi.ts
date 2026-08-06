import { apiFetch } from "@/lib/httpClient";

import type {
  ArchivoConfirmado,
  DatosCierre,
  DatosMantenimiento,
  Evidencia,
  Mantenimiento,
  PaginaMantenimientos,
} from "../types";

export async function crearMantenimiento(datos: DatosMantenimiento): Promise<Mantenimiento> {
  return apiFetch<Mantenimiento>("/mantenimientos", { method: "POST", body: JSON.stringify(datos) });
}

/** RNF-PERF-03 — el listado general pagina de verdad (20 por página); el
 * historial de un equipo (`equipoId` presente) sigue trayendo todo en una
 * sola página, ver el default de `tamano_pagina` en el backend. */
export async function listarMantenimientos(
  equipoId?: string,
  pagina?: number,
): Promise<PaginaMantenimientos> {
  const params = new URLSearchParams();
  if (equipoId) params.set("equipo_id", equipoId);
  if (pagina) params.set("pagina", String(pagina));
  const query = params.toString() ? `?${params.toString()}` : "";
  return apiFetch<PaginaMantenimientos>(`/mantenimientos${query}`);
}

export async function obtenerMantenimiento(id: string): Promise<Mantenimiento> {
  return apiFetch<Mantenimiento>(`/mantenimientos/${id}`);
}

export async function iniciarMantenimiento(id: string): Promise<Mantenimiento> {
  return apiFetch<Mantenimiento>(`/mantenimientos/${id}/iniciar`, { method: "POST" });
}

export async function cerrarMantenimiento(id: string, datos: DatosCierre): Promise<Mantenimiento> {
  return apiFetch<Mantenimiento>(`/mantenimientos/${id}/cerrar`, {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export async function cancelarMantenimiento(id: string, motivo: string): Promise<Mantenimiento> {
  return apiFetch<Mantenimiento>(`/mantenimientos/${id}/cancelar`, {
    method: "POST",
    body: JSON.stringify({ motivo }),
  });
}

export async function misMantenimientosDeHoy(): Promise<Mantenimiento[]> {
  return apiFetch<Mantenimiento[]>("/mantenimientos/hoy");
}

export async function solicitarUrlEvidencia(
  nombreArchivo: string,
  tipoMime: string,
  tamanoBytes: number,
): Promise<{ url_subida: string; object_key: string }> {
  return apiFetch("/mantenimientos/upload-url/evidencia", {
    method: "POST",
    body: JSON.stringify({ nombre_archivo: nombreArchivo, tipo_mime: tipoMime, tamano_bytes: tamanoBytes }),
  });
}

export async function solicitarUrlInforme(
  nombreArchivo: string,
  tipoMime: string,
  tamanoBytes: number,
): Promise<{ url_subida: string; object_key: string }> {
  return apiFetch("/mantenimientos/upload-url/informe", {
    method: "POST",
    body: JSON.stringify({ nombre_archivo: nombreArchivo, tipo_mime: tipoMime, tamano_bytes: tamanoBytes }),
  });
}

/** PUT directo a MinIO — mismo patrón que Calibraciones/Documentos (docs/13-arquitectura.md). */
export function subirArchivoConProgreso(
  url: string,
  archivo: File,
  onProgreso: (porcentaje: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", archivo.type);
    xhr.upload.onprogress = (evento) => {
      if (evento.lengthComputable) onProgreso(Math.round((evento.loaded / evento.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`La subida falló (HTTP ${xhr.status}).`));
    };
    xhr.onerror = () => reject(new Error("La subida falló por un error de red."));
    xhr.send(archivo);
  });
}

export async function agregarEvidencia(id: string, archivo: ArchivoConfirmado): Promise<Evidencia> {
  return apiFetch<Evidencia>(`/mantenimientos/${id}/evidencias`, {
    method: "POST",
    body: JSON.stringify(archivo),
  });
}

export async function listarEvidencias(id: string): Promise<Evidencia[]> {
  return apiFetch<Evidencia[]>(`/mantenimientos/${id}/evidencias`);
}

export async function obtenerUrlEvidencia(adjuntoId: string): Promise<{ url: string }> {
  return apiFetch(`/mantenimientos/evidencias/${adjuntoId}/url`);
}

export async function asignarInforme(id: string, archivo: ArchivoConfirmado): Promise<Mantenimiento> {
  return apiFetch<Mantenimiento>(`/mantenimientos/${id}/informe`, {
    method: "POST",
    body: JSON.stringify(archivo),
  });
}

export async function obtenerUrlInforme(id: string): Promise<{ url: string }> {
  return apiFetch(`/mantenimientos/${id}/informe-url`);
}
