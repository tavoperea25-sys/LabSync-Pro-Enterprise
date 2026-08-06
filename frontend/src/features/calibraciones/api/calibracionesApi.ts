import { apiFetch } from "@/lib/httpClient";

import type { Calibracion, DatosCalibracion, EquipoConSemaforo } from "../types";

export async function solicitarUrlCertificado(
  nombreArchivo: string,
  tipoMime: string,
  tamanoBytes: number,
): Promise<{ url_subida: string; object_key: string }> {
  return apiFetch("/calibraciones/upload-url", {
    method: "POST",
    body: JSON.stringify({ nombre_archivo: nombreArchivo, tipo_mime: tipoMime, tamano_bytes: tamanoBytes }),
  });
}

/** PUT directo a MinIO — mismo patrón que Documentos (docs/13-arquitectura.md). */
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

export async function crearCalibracion(datos: DatosCalibracion): Promise<Calibracion> {
  return apiFetch<Calibracion>("/calibraciones", { method: "POST", body: JSON.stringify(datos) });
}

export async function corregirCalibracion(
  id: string,
  datos: DatosCalibracion & { motivo: string },
): Promise<Calibracion> {
  return apiFetch<Calibracion>(`/calibraciones/${id}/corregir`, {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export async function listarPorEquipo(equipoId: string): Promise<Calibracion[]> {
  return apiFetch<Calibracion[]>(`/calibraciones?equipo_id=${equipoId}`);
}

export async function obtenerCalibracion(id: string): Promise<Calibracion> {
  return apiFetch<Calibracion>(`/calibraciones/${id}`);
}

export async function obtenerUrlCertificado(id: string): Promise<{ url: string }> {
  return apiFetch(`/calibraciones/${id}/certificado-url`);
}

export async function listarCriticos(): Promise<EquipoConSemaforo[]> {
  return apiFetch<EquipoConSemaforo[]>("/calibraciones/criticas");
}
