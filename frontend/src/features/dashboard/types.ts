export type SemaforoCalibracionAgregado = "normal" | "atencion" | "critico";

export interface Kpis {
  equipos_total: number;
  equipos_operativos: number;
  equipos_fuera_de_servicio: number;
  equipos_en_mantenimiento: number;
  equipos_de_baja: number;
  equipos_porcentaje_operativo: number;

  calibraciones_proximas_30_dias: number;
  calibraciones_semaforo: SemaforoCalibracionAgregado;

  documentos_vencidos: number;
  documentos_por_vencer: number;
  documentos_en_revision: number;

  mantenimientos_preventivos_proximos: number;
  mantenimientos_correctivos_abiertos: number;

  cumplimiento_documental_pct: number | null;
}

export interface EquipoCritico {
  equipo_id: string;
  equipo_nombre: string;
  equipo_codigo_interno: string;
  area_nombre: string | null;
  estado_operativo: string;
  ultima_calibracion_fecha: string | null;
  proxima_calibracion_fecha: string | null;
  semaforo_calibracion: string | null;
  responsable_nombre: string | null;
}

export interface ActividadReciente {
  usuario_nombre: string | null;
  accion: string;
  modulo: string;
  entidad_tipo: string;
  creado_en: string;
}
