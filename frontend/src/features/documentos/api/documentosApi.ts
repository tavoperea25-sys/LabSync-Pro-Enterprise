import { apiFetch } from "@/lib/httpClient";

import type {
  ArchivoConfirmado,
  Carpeta,
  Documento,
  DocumentoDetalle,
  Etiqueta,
  FiltrosDocumentos,
  PaginaDocumentos,
  Version,
} from "../types";

function construirQuery(filtros: FiltrosDocumentos): string {
  const params = new URLSearchParams();
  if (filtros.carpeta_id) params.set("carpeta_id", filtros.carpeta_id);
  if (filtros.categoria) params.set("categoria", filtros.categoria);
  if (filtros.etiqueta_id) params.set("etiqueta_id", filtros.etiqueta_id);
  if (filtros.q) params.set("q", filtros.q);
  if (filtros.favoritos) params.set("favoritos", "true");
  params.set("pagina", String(filtros.pagina ?? 1));
  return params.toString();
}

export async function listarDocumentos(filtros: FiltrosDocumentos): Promise<PaginaDocumentos> {
  return apiFetch<PaginaDocumentos>(`/documentos?${construirQuery(filtros)}`);
}

export async function listarRecientes(): Promise<Documento[]> {
  return apiFetch<Documento[]>("/documentos/recientes");
}

export async function listarPapelera(): Promise<Documento[]> {
  return apiFetch<Documento[]>("/documentos/papelera");
}

export async function obtenerDocumento(id: string): Promise<DocumentoDetalle> {
  return apiFetch<DocumentoDetalle>(`/documentos/${id}`);
}

export async function solicitarUrlSubida(
  nombreArchivo: string,
  tipoMime: string,
  tamanoBytes: number,
): Promise<{ url_subida: string; object_key: string }> {
  return apiFetch(`/documentos/upload-url`, {
    method: "POST",
    body: JSON.stringify({ nombre_archivo: nombreArchivo, tipo_mime: tipoMime, tamano_bytes: tamanoBytes }),
  });
}

/** PUT directo a la URL prefirmada de MinIO — nunca pasa por nuestro API
 * (docs/13-arquitectura.md sección 5). Se usa XHR en vez de fetch porque
 * fetch no expone eventos de progreso de subida (RF-DOC-01). */
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

export async function crearDocumento(datos: {
  nombre: string;
  carpeta_id?: string | null;
  categoria?: string | null;
  fecha_emision?: string | null;
  fecha_vencimiento?: string | null;
  archivo: ArchivoConfirmado;
}): Promise<Documento> {
  return apiFetch<Documento>("/documentos", { method: "POST", body: JSON.stringify(datos) });
}

export async function subirNuevaVersion(documentoId: string, archivo: ArchivoConfirmado): Promise<Version> {
  return apiFetch<Version>(`/documentos/${documentoId}/versiones`, {
    method: "POST",
    body: JSON.stringify(archivo),
  });
}

export async function renombrarDocumento(id: string, nombre: string): Promise<Documento> {
  return apiFetch<Documento>(`/documentos/${id}`, { method: "PATCH", body: JSON.stringify({ nombre }) });
}

export async function moverDocumento(id: string, carpetaId: string | null): Promise<Documento> {
  return apiFetch<Documento>(`/documentos/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ mover_a_carpeta: true, carpeta_id: carpetaId }),
  });
}

export async function copiarDocumento(id: string): Promise<Documento> {
  return apiFetch<Documento>(`/documentos/${id}/copiar`, { method: "POST" });
}

export async function actualizarMetadatos(
  id: string,
  datos: { categoria: string | null; fecha_emision: string | null; fecha_vencimiento: string | null },
): Promise<Documento> {
  return apiFetch<Documento>(`/documentos/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ actualizar_metadatos: true, ...datos }),
  });
}

export async function aprobarDocumento(id: string): Promise<Documento> {
  return apiFetch<Documento>(`/documentos/${id}/aprobar`, { method: "POST" });
}

export async function rechazarDocumento(id: string, comentario: string): Promise<Documento> {
  return apiFetch<Documento>(`/documentos/${id}/rechazar`, {
    method: "POST",
    body: JSON.stringify({ comentario }),
  });
}

export async function eliminarDocumento(id: string): Promise<void> {
  return apiFetch<void>(`/documentos/${id}`, { method: "DELETE" });
}

export async function restaurarDocumento(id: string): Promise<void> {
  return apiFetch<void>(`/documentos/${id}/restaurar`, { method: "POST" });
}

export async function alternarFavorito(id: string): Promise<{ es_favorito: boolean }> {
  return apiFetch(`/documentos/${id}/favorito`, { method: "POST" });
}

export async function obtenerUrlDescarga(id: string, numeroVersion: number): Promise<{ url: string }> {
  return apiFetch(`/documentos/${id}/versiones/${numeroVersion}/download-url`);
}

export async function obtenerVistaPrevia(
  id: string,
): Promise<{ url: string | null; nombre_archivo: string; tipo_mime: string; tamano_bytes: number }> {
  return apiFetch(`/documentos/${id}/vista-previa`);
}

export async function listarEtiquetasDocumento(id: string): Promise<Etiqueta[]> {
  return apiFetch<Etiqueta[]>(`/documentos/${id}/etiquetas`);
}

export async function asignarEtiqueta(id: string, nombre: string): Promise<Etiqueta> {
  return apiFetch<Etiqueta>(`/documentos/${id}/etiquetas`, { method: "POST", body: JSON.stringify({ nombre }) });
}

export async function quitarEtiqueta(id: string, etiquetaId: string): Promise<void> {
  return apiFetch<void>(`/documentos/${id}/etiquetas/${etiquetaId}`, { method: "DELETE" });
}

export async function listarEtiquetas(): Promise<Etiqueta[]> {
  return apiFetch<Etiqueta[]>("/etiquetas");
}

export async function listarCarpetas(carpetaPadreId?: string | null): Promise<Carpeta[]> {
  const query = carpetaPadreId ? `?carpeta_padre_id=${carpetaPadreId}` : "";
  return apiFetch<Carpeta[]>(`/carpetas${query}`);
}

export async function obtenerCarpeta(id: string): Promise<Carpeta> {
  return apiFetch<Carpeta>(`/carpetas/${id}`);
}

export async function crearCarpeta(nombre: string, carpetaPadreId: string | null): Promise<Carpeta> {
  return apiFetch<Carpeta>("/carpetas", {
    method: "POST",
    body: JSON.stringify({ nombre, carpeta_padre_id: carpetaPadreId }),
  });
}

export async function renombrarCarpeta(id: string, nombre: string): Promise<Carpeta> {
  return apiFetch<Carpeta>(`/carpetas/${id}`, { method: "PATCH", body: JSON.stringify({ nombre }) });
}

export async function eliminarCarpeta(id: string): Promise<void> {
  return apiFetch<void>(`/carpetas/${id}`, { method: "DELETE" });
}
