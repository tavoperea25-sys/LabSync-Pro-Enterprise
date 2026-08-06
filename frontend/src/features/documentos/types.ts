export const FORMATOS_PERMITIDOS: Record<string, string[]> = {
  pdf: ["application/pdf"],
  docx: ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
  xlsx: ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"],
  pptx: ["application/vnd.openxmlformats-officedocument.presentationml.presentation"],
  csv: ["text/csv", "application/vnd.ms-excel"],
  txt: ["text/plain"],
  jpg: ["image/jpeg"],
  jpeg: ["image/jpeg"],
  png: ["image/png"],
  webp: ["image/webp"],
};

export const EXTENSIONES_ACEPTADAS = Object.keys(FORMATOS_PERMITIDOS)
  .map((ext) => `.${ext}`)
  .join(",");

export const TAMANO_MAXIMO_BYTES = 50 * 1024 * 1024;

export interface Carpeta {
  id: string;
  nombre: string;
  carpeta_padre_id: string | null;
  creado_en: string;
}

export interface Version {
  id: string;
  numero_version: number;
  nombre_archivo: string;
  tamano_bytes: number;
  tipo_mime: string;
  subido_por_id: string | null;
  aprobado_por_id: string | null;
  aprobado_en: string | null;
  creado_en: string;
}

export interface Etiqueta {
  id: string;
  nombre: string;
}

export interface Documento {
  id: string;
  carpeta_id: string | null;
  nombre: string;
  categoria: string | null;
  estado: string;
  estado_efectivo: string;
  fecha_emision: string | null;
  fecha_vencimiento: string | null;
  responsable_aprobacion_id: string | null;
  version_vigente_id: string | null;
  creado_en: string;
  actualizado_en: string;
}

export interface Rechazo {
  comentario: string;
  usuario_id: string | null;
  creado_en: string;
}

export interface DocumentoDetalle extends Documento {
  versiones: Version[];
  etiquetas: Etiqueta[];
  es_favorito: boolean;
  ultimo_rechazo: Rechazo | null;
}

export const ETIQUETAS_ESTADO_DOCUMENTO: Record<string, string> = {
  vigente: "Vigente",
  en_revision: "En revisión",
  obsoleto: "Obsoleto",
  vencido: "Vencido",
};

export interface PaginaDocumentos {
  items: Documento[];
  total: number;
  pagina: number;
  tamano_pagina: number;
}

export interface FiltrosDocumentos {
  carpeta_id?: string;
  categoria?: string;
  etiqueta_id?: string;
  q?: string;
  favoritos?: boolean;
  pagina?: number;
  tamano_pagina?: number;
}

export interface ArchivoConfirmado {
  object_key: string;
  nombre_archivo: string;
  tamano_bytes: number;
  tipo_mime: string;
}

export function extensionDe(nombreArchivo: string): string {
  const partes = nombreArchivo.split(".");
  return partes.length > 1 ? (partes.at(-1) ?? "").toLowerCase() : "";
}

export function formatoPermitido(nombreArchivo: string, tipoMime: string): boolean {
  const mimesValidos = FORMATOS_PERMITIDOS[extensionDe(nombreArchivo)];
  return !!mimesValidos && mimesValidos.includes(tipoMime);
}

export function formatearTamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
