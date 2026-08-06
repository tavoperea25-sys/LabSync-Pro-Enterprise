export interface Rol {
  id: string;
  nombre: string;
  es_sistema: boolean;
}

export const ETIQUETAS_ROL: Record<string, string> = {
  administrador: "Administrador",
  director_tecnico: "Director Técnico",
  calidad: "Calidad",
  metrologia: "Metrología",
  tecnico: "Técnico",
  consulta: "Consulta",
};

export interface Usuario {
  id: string;
  nombre_completo: string;
  correo: string;
  estado: string;
  debe_cambiar_password: boolean;
  roles: string[];
}

export interface PaginaUsuarios {
  items: Usuario[];
  total: number;
  pagina: number;
  tamano_pagina: number;
}

export interface DatosCrearUsuario {
  nombre_completo: string;
  correo: string;
  password: string;
  rol_ids: string[];
}

export interface DatosActualizarUsuario {
  nombre_completo: string;
}

export interface Sesion {
  id: string;
  ip_origen: string | null;
  user_agent: string | null;
  creado_en: string;
  expira_en: string;
}
