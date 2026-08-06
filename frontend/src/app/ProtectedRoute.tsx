import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "@/features/auth/hooks/AuthProvider";

const RUTA_CAMBIO_OBLIGATORIO = "/cambiar-password";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { usuario, cargandoSesionInicial } = useAuth();
  const location = useLocation();

  if (cargandoSesionInicial) {
    return (
      <div className="flex min-h-screen items-center justify-center text-ink-soft" aria-busy="true">
        Cargando…
      </div>
    );
  }

  if (!usuario) {
    return <Navigate to="/login" replace />;
  }

  // RF-USR-04 — mientras el usuario tenga una contraseña temporal
  // pendiente de cambiar, ninguna otra pantalla es alcanzable (el backend
  // ya lo bloquea a nivel de API — ver `get_usuario_actual` — esto solo
  // evita que el usuario navegue a una pantalla que de todos modos le
  // devolvería errores 403 en cada petición).
  if (usuario.debe_cambiar_password && location.pathname !== RUTA_CAMBIO_OBLIGATORIO) {
    return <Navigate to={RUTA_CAMBIO_OBLIGATORIO} replace />;
  }

  return <>{children}</>;
}
