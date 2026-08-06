export interface LogAuditoria {
  id: string;
  usuario_id: string | null;
  ip_origen: string | null;
  modulo: string;
  accion: string;
  entidad_tipo: string;
  entidad_id: string | null;
  valor_anterior: Record<string, unknown> | null;
  valor_nuevo: Record<string, unknown> | null;
  creado_en: string;
}

export interface ValoresFiltro {
  modulos: string[];
  acciones: string[];
}

export interface FiltrosAuditoria {
  usuario_id?: string;
  modulo?: string;
  accion?: string;
  desde?: string;
  hasta?: string;
  pagina?: number;
}

export interface PaginaAuditoria {
  items: LogAuditoria[];
  total: number;
  pagina: number;
  tamano_pagina: number;
}

export type FormatoExportacion = "csv" | "xlsx" | "pdf";
