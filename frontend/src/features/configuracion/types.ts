export interface PoliticaPassword {
  longitud_minima?: number;
  requiere_mayuscula?: boolean;
  requiere_minuscula?: boolean;
  requiere_digito?: boolean;
  requiere_simbolo?: boolean;
}

export type EstadoOperativoResultante = "fuera_de_servicio" | "en_mantenimiento";

/** RN-MANT-01 — tipo de mantenimiento -> estado operativo que toma el
 * equipo al iniciarlo. `null`/tipo ausente usa la asignación por defecto
 * (ver mantenimientos/domain/entities.py). */
export type MapeoEstadosMantenimiento = Record<string, EstadoOperativoResultante>;

export interface Configuracion {
  umbral_alerta_calibracion_dias: number;
  umbral_alerta_mantenimiento_dias: number;
  umbral_alerta_documento_dias: number;
  dias_retencion_papelera_documentos: number;
  politica_password: PoliticaPassword | null;
  mapeo_estados_mantenimiento: MapeoEstadosMantenimiento | null;
}

export interface ActualizarUmbrales {
  umbral_alerta_calibracion_dias: number;
  umbral_alerta_mantenimiento_dias: number;
  umbral_alerta_documento_dias: number;
  dias_retencion_papelera_documentos: number;
}

export interface Institucion {
  id: string;
  nombre: string;
  slug: string;
  logo_url: string | null;
  logo_object_key: string | null;
}

export interface UrlSubidaLogo {
  url_subida: string;
  object_key: string;
}

export interface CategoriaEquipo {
  id: string;
  nombre: string;
  frecuencia_calibracion_default_meses: number | null;
  bloquea_activacion_si_calibracion_vencida: boolean;
}

export interface Area {
  id: string;
  nombre: string;
}

export interface DatosPerfilPropio {
  nombre_completo: string;
  correo: string;
  foto_object_key?: string | null;
}

export interface PerfilActualizado {
  id: string;
  nombre_completo: string;
  correo: string;
  roles: string[];
  debe_cambiar_password: boolean;
  foto_url: string | null;
  foto_object_key: string | null;
}

export interface DatosCambiarPassword {
  password_actual: string;
  password_nueva: string;
}
