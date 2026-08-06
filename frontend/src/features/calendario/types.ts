export const TIPOS_EVENTO_MANUAL = ["auditoria", "capacitacion", "institucional"] as const;
export type TipoEventoManual = (typeof TIPOS_EVENTO_MANUAL)[number];

export type TipoEvento = TipoEventoManual | "calibracion" | "mantenimiento" | "vencimiento_documental";

export const ETIQUETAS_TIPO_EVENTO: Record<TipoEvento, string> = {
  auditoria: "Auditoría",
  capacitacion: "Capacitación",
  institucional: "Institucional",
  calibracion: "Calibración",
  mantenimiento: "Mantenimiento",
  vencimiento_documental: "Vencimiento de documento",
};

export const COLOR_POR_TIPO: Record<TipoEvento, string> = {
  auditoria: "#7C3AED",
  capacitacion: "#0891B2",
  institucional: "#4338CA",
  calibracion: "#0F5132",
  mantenimiento: "#B45309",
  vencimiento_documental: "#991B1B",
};

export interface EventoCalendario {
  id: string;
  tipo: TipoEvento;
  titulo: string;
  descripcion: string | null;
  fecha: string;
  origen_tipo: string | null;
  origen_id: string | null;
  editable: boolean;
}

export interface DatosEventoCalendario {
  tipo: TipoEventoManual;
  titulo: string;
  fecha: string;
  descripcion?: string | null;
}

export type VistaCalendario = "dia" | "semana" | "mes" | "agenda";
