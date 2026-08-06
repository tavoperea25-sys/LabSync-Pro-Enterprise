export const RESULTADOS_CALIBRACION = ["conforme", "no_conforme"] as const;
export type ResultadoCalibracion = (typeof RESULTADOS_CALIBRACION)[number];

export const ETIQUETAS_RESULTADO: Record<ResultadoCalibracion, string> = {
  conforme: "Conforme",
  no_conforme: "No conforme",
};

export type Semaforo = "verde" | "amarillo" | "rojo" | "gris";

export const ETIQUETAS_SEMAFORO: Record<Semaforo, string> = {
  verde: "Vigente",
  amarillo: "Próximo a vencer",
  rojo: "Vencido",
  gris: "Sin información",
};

export interface ArchivoCertificado {
  object_key: string;
  nombre_archivo: string;
  tamano_bytes: number;
  tipo_mime: string;
}

export interface Calibracion {
  id: string;
  equipo_id: string;
  fecha_calibracion: string;
  frecuencia_meses: number;
  proxima_fecha: string;
  laboratorio_proveedor: string | null;
  numero_certificado: string | null;
  resultado: ResultadoCalibracion;
  incertidumbre: string | null;
  responsable_id: string | null;
  corrige_a_id: string | null;
  motivo_correccion: string | null;
  observaciones: string | null;
  tiene_certificado: boolean;
  semaforo: Semaforo;
  dias_restantes: number | null;
  creado_en: string;
}

export interface EquipoConSemaforo {
  equipo_id: string;
  equipo_nombre: string;
  equipo_codigo_interno: string;
  ultima_calibracion_id: string | null;
  proxima_fecha: string | null;
  dias_restantes: number | null;
  semaforo: Semaforo;
}

export interface DatosCalibracion {
  equipo_id: string;
  fecha_calibracion: string;
  frecuencia_meses: number;
  laboratorio_proveedor?: string | null;
  numero_certificado?: string | null;
  resultado: ResultadoCalibracion;
  incertidumbre?: string | null;
  observaciones?: string | null;
  certificado?: ArchivoCertificado | null;
}

export const EXTENSIONES_CERTIFICADO = ".pdf";
export const TAMANO_MAXIMO_CERTIFICADO_BYTES = 20 * 1024 * 1024;

export function formatearTamano(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
