export const TIPOS_REPORTE = [
  "inventario",
  "calibraciones",
  "vencidos",
  "cumplimiento",
  "mantenimiento",
  "trazabilidad_documental",
  "paquete_auditoria",
] as const;

export type TipoReporte = (typeof TIPOS_REPORTE)[number];

export type FormatoReporte = "pdf" | "xlsx" | "csv";

export const ETIQUETAS_FORMATO: Record<FormatoReporte, string> = {
  pdf: "PDF",
  xlsx: "Excel",
  csv: "CSV",
};

export const ESTADOS_REPORTE = ["pendiente", "procesando", "listo", "fallido"] as const;
export type EstadoReporte = (typeof ESTADOS_REPORTE)[number];

export const ETIQUETAS_ESTADO_REPORTE: Record<EstadoReporte, string> = {
  pendiente: "En cola",
  procesando: "Procesando",
  listo: "Listo",
  fallido: "Falló",
};

export interface TipoReporteInfo {
  tipo: TipoReporte;
  etiqueta: string;
  formatos_disponibles: FormatoReporte[];
}

export interface FiltrosReporte {
  categoria_id?: string;
  area_id?: string;
  estado_operativo?: string;
  equipo_id?: string;
  desde?: string;
  hasta?: string;
  meses?: number;
}

export interface ReporteGenerado {
  id: string;
  tipo: TipoReporte;
  formato: FormatoReporte;
  filtros: Record<string, unknown> | null;
  estado: EstadoReporte;
  nombre_archivo: string | null;
  error: string | null;
  creado_en: string;
  completado_en: string | null;
}

export interface UrlDescarga {
  url: string;
}
