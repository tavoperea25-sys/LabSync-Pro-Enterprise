export const ESTADOS_OPERATIVOS = [
  "operativo",
  "fuera_de_servicio",
  "en_mantenimiento",
  "de_baja",
] as const;

export type EstadoOperativo = (typeof ESTADOS_OPERATIVOS)[number];

export const ETIQUETAS_ESTADO: Record<EstadoOperativo, string> = {
  operativo: "Operativo",
  fuera_de_servicio: "Fuera de servicio",
  en_mantenimiento: "En mantenimiento",
  de_baja: "De baja",
};

export interface Equipo {
  id: string;
  codigo_interno: string;
  nombre: string;
  estado_operativo: EstadoOperativo;
  categoria_id: string | null;
  area_id: string | null;
  responsable_id: string | null;
  marca: string | null;
  modelo: string | null;
  numero_serie: string | null;
  fabricante: string | null;
  proveedor: string | null;
  fecha_adquisicion: string | null;
  observaciones: string | null;
  /** URL prefirmada ya resuelta, lista para usar en un <img>. */
  foto_url: string | null;
  /** object_key estable (no expira) — se reenvía tal cual en un PATCH que
   * no toca la foto, para no borrarla accidentalmente (ver EquipoFormPage). */
  foto_object_key: string | null;
  /** URL prefirmada de descarga (expira), o null si no hay manual cargado. */
  manual_url: string | null;
  manual_object_key: string | null;
  creado_en: string;
  actualizado_en: string;
}

export interface EquipoRequest {
  codigo_interno: string;
  nombre: string;
  estado_operativo: EstadoOperativo;
  categoria_id?: string | null;
  area_id?: string | null;
  responsable_id?: string | null;
  marca?: string | null;
  modelo?: string | null;
  numero_serie?: string | null;
  fabricante?: string | null;
  proveedor?: string | null;
  fecha_adquisicion?: string | null;
  observaciones?: string | null;
  foto_object_key?: string | null;
  manual_object_key?: string | null;
}

export interface UrlFoto {
  url_subida: string;
  object_key: string;
}

export interface PaginaEquipos {
  items: Equipo[];
  total: number;
  pagina: number;
  tamano_pagina: number;
}

export interface CategoriaEquipo {
  id: string;
  nombre: string;
}

export interface Area {
  id: string;
  nombre: string;
}

export interface FiltrosEquipos {
  q?: string;
  categoria_id?: string;
  area_id?: string;
  estado_operativo?: string;
  pagina?: number;
}

export interface HistorialEntrada {
  id: string;
  usuario_id: string | null;
  accion: string;
  valor_anterior: Record<string, unknown> | null;
  valor_nuevo: Record<string, unknown> | null;
  creado_en: string;
}

export const ETIQUETAS_ACCION: Record<string, string> = {
  crear: "Creado",
  actualizar: "Actualizado",
  eliminar: "Archivado",
};

export interface QrInfo {
  token: string;
  url_publica: string;
}
