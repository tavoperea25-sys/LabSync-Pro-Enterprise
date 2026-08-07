import { KeyRound, LogOut } from "lucide-react";
import { useNavigate } from "react-router";

import { AmbientBackground } from "@/shared/components/AmbientBackground";

import { CambiarPasswordForm } from "./CambiarPasswordForm";
import { useAuth } from "../hooks/AuthProvider";

/** RF-USR-04 — pantalla de paso obligatorio para un usuario que todavía
 * tiene la contraseña temporal que le asignó un Administrador.
 * `ProtectedRoute` redirige aquí a cualquier otra ruta mientras
 * `usuario.debe_cambiar_password` sea `true`; el backend hace cumplir lo
 * mismo a nivel de API (`get_usuario_actual`), esta pantalla es la
 * experiencia, no el control de acceso real. */
export function CambiarPasswordObligatorioPage() {
  const { usuario, cerrarSesion } = useAuth();
  const navigate = useNavigate();

  async function salir() {
    await cerrarSesion();
    navigate("/login");
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-surface-alt p-4">
      <AmbientBackground />
      <div className="relative z-10 w-full max-w-md rounded-xl border border-border bg-surface p-8 shadow-ambient">
        <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-full bg-primary-tint">
          <KeyRound className="h-5 w-5 text-primary-900" aria-hidden="true" />
        </div>
        <h1 className="font-display text-xl font-semibold text-ink">Actualiza tu contraseña</h1>
        <p className="mb-6 mt-1.5 text-sm text-ink-soft">
          {usuario ? `Hola, ${usuario.nombre_completo.split(" ")[0]}. ` : ""}
          Tu cuenta todavía tiene la contraseña temporal que te asignó tu Administrador. Debes
          cambiarla antes de poder usar el resto de LabSync Pro.
        </p>

        <CambiarPasswordForm textoBoton="Actualizar y continuar" />

        <button
          type="button"
          onClick={salir}
          className="mt-5 flex items-center gap-1.5 text-xs font-medium text-ink-soft hover:text-ink"
        >
          <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
          Cerrar sesión
        </button>
      </div>
    </div>
  );
}
