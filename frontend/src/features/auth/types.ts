export interface Usuario {
  id: string;
  nombre_completo: string;
  correo: string;
  roles: string[];
  debe_cambiar_password: boolean;
  foto_url: string | null;
  foto_object_key: string | null;
}

export interface LoginResponse {
  access_token: string;
  expira_en: number;
  usuario: Usuario;
}

export interface LoginRequest {
  laboratorio_slug: string;
  correo: string;
  password: string;
  recordarme: boolean;
}
