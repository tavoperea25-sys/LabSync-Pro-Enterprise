import type { EstadoOperativo } from "@/features/equipos/types";

export interface EquipoPublico {
  codigo_interno: string;
  nombre: string;
  estado_operativo: EstadoOperativo;
  marca: string | null;
  modelo: string | null;
  foto_url: string | null;
  dado_de_baja: boolean;
}

export interface IncidenciaRequest {
  descripcion: string;
  contacto_nombre?: string;
  contacto_medio?: string;
}

export interface IncidenciaCreada {
  id: string;
  estado: string;
}

export type EstadoIncidencia = "pendiente" | "en_revision" | "resuelta";

/** RF-QR-03 "Salidas" — la incidencia enriquecida con los datos del equipo
 * que la vista de triage en Mantenimientos necesita mostrar. */
export interface IncidenciaQr {
  id: string;
  equipo_id: string;
  equipo_codigo_interno: string;
  equipo_nombre: string;
  descripcion: string;
  contacto_nombre: string | null;
  contacto_medio: string | null;
  estado: EstadoIncidencia;
  creado_en: string;
}
