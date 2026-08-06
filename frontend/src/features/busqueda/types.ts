export type TipoResultado = "equipo" | "documento" | "calibracion" | "mantenimiento" | "usuario" | "auditoria";

export const ETIQUETAS_TIPO_RESULTADO: Record<TipoResultado, string> = {
  equipo: "Equipos",
  documento: "Documentos",
  calibracion: "Certificados",
  mantenimiento: "Mantenimientos",
  usuario: "Usuarios",
  auditoria: "Auditoría",
};

export interface ResultadoBusqueda {
  tipo: TipoResultado;
  id: string;
  titulo: string;
  subtitulo: string | null;
  ruta: string;
}
