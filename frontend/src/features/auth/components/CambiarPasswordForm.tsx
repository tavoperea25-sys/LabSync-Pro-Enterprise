import { useState } from "react";
import { useNavigate } from "react-router";

import { useCambiarPasswordPropio } from "@/features/configuracion/hooks/useConfiguracion";
import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";

import { useAuth } from "../hooks/AuthProvider";

/** Formulario de "cambiar mi contraseña", compartido entre
 * `PerfilSection` (Configuración → Mi perfil, cambio voluntario) y
 * `CambiarPasswordObligatorioPage` (RF-USR-04, cambio forzado en el primer
 * inicio de sesión) — misma llamada, misma validación, mismo efecto
 * (revoca todas las sesiones y redirige a login), solo cambia el texto
 * alrededor según el contexto en el que se use. */
export function CambiarPasswordForm({ textoBoton = "Cambiar contraseña" }: { textoBoton?: string }) {
  const { cerrarSesion } = useAuth();
  const navigate = useNavigate();
  const cambiarPassword = useCambiarPasswordPropio();

  const [passwordActual, setPasswordActual] = useState("");
  const [passwordNueva, setPasswordNueva] = useState("");
  const [erroresPassword, setErroresPassword] = useState<string[]>([]);

  async function guardarPassword() {
    if (!passwordActual || !passwordNueva) {
      setErroresPassword(["Completa ambos campos de contraseña."]);
      return;
    }
    setErroresPassword([]);
    try {
      await cambiarPassword.mutateAsync({ password_actual: passwordActual, password_nueva: passwordNueva });
      // El cambio revoca todas las sesiones, incluida esta (mismo criterio
      // que RN-USR-01 al desactivar un usuario) — se navega a login primero
      // (con el mensaje) y solo después se limpia la sesión local: si
      // `cerrarSesion()` fuera primero, pondría `usuario` en null mientras
      // este formulario sigue montado bajo `ProtectedRoute`, y su propio
      // redirect a "/login" (sin mensaje) competiría con este navigate.
      navigate("/login", { state: { mensaje: "Contraseña actualizada. Inicia sesión de nuevo." } });
      await cerrarSesion();
    } catch (err) {
      if (err instanceof ApiError) {
        const motivos = (err.detalles?.motivos as string[] | undefined) ?? [err.message];
        setErroresPassword(motivos);
      } else {
        setErroresPassword(["No se pudo cambiar la contraseña."]);
      }
    }
  }

  return (
    <div>
      <Input
        label="Contraseña actual"
        type="password"
        value={passwordActual}
        onChange={(e) => setPasswordActual(e.target.value)}
        autoComplete="current-password"
      />
      <Input
        label="Contraseña nueva"
        type="password"
        value={passwordNueva}
        onChange={(e) => setPasswordNueva(e.target.value)}
        autoComplete="new-password"
      />
      {erroresPassword.length > 0 && (
        <ul role="alert" aria-live="polite" className="mb-3 list-disc space-y-0.5 pl-5 text-sm font-medium text-danger">
          {erroresPassword.map((motivo) => (
            <li key={motivo}>{motivo}</li>
          ))}
        </ul>
      )}
      <Button size="sm" variant="secondary" cargando={cambiarPassword.isPending} onClick={guardarPassword}>
        {textoBoton}
      </Button>
    </div>
  );
}
