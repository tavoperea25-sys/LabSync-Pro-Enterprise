import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { setAccessToken } from "@/lib/httpClient";

import * as authApi from "../api/authApi";
import type { LoginRequest, Usuario } from "../types";

interface AuthContextValue {
  usuario: Usuario | null;
  cargandoSesionInicial: boolean;
  iniciarSesion: (datos: LoginRequest) => Promise<void>;
  cerrarSesion: () => Promise<void>;
  /** RF-CFG-01 — tras editar el perfil propio, refleja el cambio de
   * inmediato en Navbar/Sidebar sin esperar a un refresh de token. */
  actualizarUsuario: (usuario: Usuario) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargandoSesionInicial, setCargandoSesionInicial] = useState(true);

  useEffect(() => {
    // Al montar la app, el access token en memoria se perdió (recarga de
    // página) — se intenta restaurar la sesión vía la cookie httpOnly de
    // refresh (docs/09-user-flows.md no cubre este caso explícitamente,
    // es un detalle de implementación necesario para SPA con tokens en
    // memoria en lugar de localStorage).
    authApi
      .obtenerUsuarioActual()
      .then(setUsuario)
      .catch(() => setUsuario(null))
      .finally(() => setCargandoSesionInicial(false));
  }, []);

  async function iniciarSesion(datos: LoginRequest) {
    const respuesta = await authApi.login(datos);
    setUsuario(respuesta.usuario);
  }

  async function cerrarSesion() {
    await authApi.logout();
    setAccessToken(null);
    setUsuario(null);
  }

  return (
    <AuthContext.Provider
      value={{ usuario, cargandoSesionInicial, iniciarSesion, cerrarSesion, actualizarUsuario: setUsuario }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// Patrón estándar de provider+hook co-ubicados; separarlos en dos archivos
// no aporta claridad aquí, solo indirección.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const contexto = useContext(AuthContext);
  if (!contexto) throw new Error("useAuth debe usarse dentro de <AuthProvider>.");
  return contexto;
}
