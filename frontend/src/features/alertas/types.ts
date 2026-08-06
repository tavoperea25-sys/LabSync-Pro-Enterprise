export const TIPOS_ALERTA = ["critica", "preventiva"] as const;
export type TipoAlerta = (typeof TIPOS_ALERTA)[number];

export const ETIQUETAS_TIPO_ALERTA: Record<TipoAlerta, string> = {
  critica: "Crítica",
  preventiva: "Preventiva",
};

export type OrigenAlerta = "calibracion" | "documento" | "mantenimiento" | "equipo";

export const ETIQUETAS_ORIGEN: Record<OrigenAlerta, string> = {
  calibracion: "Calibración",
  documento: "Documento",
  mantenimiento: "Mantenimiento",
  equipo: "Equipo",
};

export const ESTADOS_ALERTA = ["activa", "resuelta"] as const;
export type EstadoAlerta = (typeof ESTADOS_ALERTA)[number];

export interface Alerta {
  id: string;
  tipo: TipoAlerta;
  origen_tipo: OrigenAlerta;
  origen_id: string;
  mensaje: string;
  estado: EstadoAlerta;
  leida_en: string | null;
  resuelta_por_id: string | null;
  resuelta_en: string | null;
  creado_en: string;
}

export interface PaginaAlertas {
  items: Alerta[];
  total: number;
  pagina: number;
  tamano_pagina: number;
}

/** Payload del canal WS `/ws/v1/notificaciones` — compartido entre eventos
 * de Alertas ("alerta.nueva") y de Reportes asíncronos ("reporte.listo",
 * Sprint 11, RNF-PERF-04), de ahí que los campos específicos de cada uno
 * sean opcionales. */
export interface EventoNotificacion {
  evento: string;
  mensaje: string;
  alerta_id?: string;
  tipo?: TipoAlerta | string;
  origen_tipo?: OrigenAlerta;
  reporte_id?: string;
}
