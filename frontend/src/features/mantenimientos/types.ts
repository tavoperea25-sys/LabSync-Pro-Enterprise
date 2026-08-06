export const TIPOS_MANTENIMIENTO = ["preventivo", "correctivo", "predictivo", "calibracion_correctiva"] as const;
export type TipoMantenimiento = (typeof TIPOS_MANTENIMIENTO)[number];

export const ETIQUETAS_TIPO: Record<TipoMantenimiento, string> = {
  preventivo: "Preventivo",
  correctivo: "Correctivo",
  predictivo: "Predictivo",
  calibracion_correctiva: "Calibración correctiva",
};

export const ESTADOS_MANTENIMIENTO = ["programado", "en_ejecucion", "completado", "cancelado"] as const;
export type EstadoMantenimiento = (typeof ESTADOS_MANTENIMIENTO)[number];

export const ETIQUETAS_ESTADO_MANTENIMIENTO: Record<EstadoMantenimiento, string> = {
  programado: "Programado",
  en_ejecucion: "En ejecución",
  completado: "Completado",
  cancelado: "Cancelado",
};

export interface Mantenimiento {
  id: string;
  equipo_id: string;
  tipo: TipoMantenimiento;
  estado: EstadoMantenimiento;
  fecha_programada: string | null;
  fecha_ejecutada: string | null;
  tecnico_responsable_id: string | null;
  descripcion: string | null;
  repuestos_utilizados: string | null;
  tiempo_inactividad_horas: string | null;
  costo: string | null;
  tiene_informe: boolean;
  frecuencia_meses: number | null;
  generado_de_id: string | null;
  creado_en: string;
  actualizado_en: string;
}

export interface PaginaMantenimientos {
  items: Mantenimiento[];
  total: number;
  pagina: number;
  tamano_pagina: number;
}

export interface DatosMantenimiento {
  equipo_id: string;
  tipo: TipoMantenimiento;
  fecha_programada: string | null;
  tecnico_responsable_id?: string | null;
  descripcion?: string | null;
  frecuencia_meses?: number | null;
}

export interface DatosCierre {
  fecha_ejecutada: string;
  repuestos_utilizados?: string | null;
  tiempo_inactividad_horas?: string | null;
  costo?: string | null;
  descripcion?: string | null;
}

export interface Evidencia {
  id: string;
  nombre_archivo: string;
  tamano_bytes: number;
  tipo_mime: string;
  creado_en: string;
}

export interface ArchivoConfirmado {
  object_key: string;
  nombre_archivo: string;
  tamano_bytes: number;
  tipo_mime: string;
}

export const EXTENSIONES_EVIDENCIA = ".jpg,.jpeg,.png,.webp";
export const TAMANO_MAXIMO_EVIDENCIA_BYTES = 10 * 1024 * 1024;
export const EXTENSIONES_INFORME = ".pdf";
export const TAMANO_MAXIMO_INFORME_BYTES = 20 * 1024 * 1024;

export function formatearTamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
