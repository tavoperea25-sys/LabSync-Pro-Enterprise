import { useState } from "react";

import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Input } from "@/shared/components/ui/input";

import { useRoles } from "../hooks/useUsuarios";
import { ETIQUETAS_ROL, type DatosCrearUsuario } from "../types";

interface Props {
  guardando: boolean;
  onGuardar: (datos: DatosCrearUsuario) => Promise<void>;
  onCancelar: () => void;
}

export function UsuarioFormulario({ guardando, onGuardar, onCancelar }: Props) {
  const { data: roles } = useRoles();
  const [nombreCompleto, setNombreCompleto] = useState("");
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");
  const [rolIds, setRolIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  function alternarRol(id: string) {
    setRolIds((actuales) => (actuales.includes(id) ? actuales.filter((r) => r !== id) : [...actuales, id]));
  }

  async function confirmar() {
    if (!nombreCompleto.trim() || !correo.trim() || !password) {
      setError("Nombre, correo y contraseña son obligatorios.");
      return;
    }
    if (rolIds.length === 0) {
      setError("Selecciona al menos un rol.");
      return;
    }
    setError(null);
    try {
      await onGuardar({ nombre_completo: nombreCompleto.trim(), correo: correo.trim(), password, rol_ids: rolIds });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el usuario.");
    }
  }

  return (
    <div className="rounded-md border border-border bg-surface-alt p-4">
      <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
        <Input label="Nombre completo" value={nombreCompleto} onChange={(e) => setNombreCompleto(e.target.value)} />
        <Input label="Correo" type="email" value={correo} onChange={(e) => setCorreo(e.target.value)} />
      </div>
      <Input
        label="Contraseña temporal"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <p className="-mt-2 mb-4 text-xs text-ink-soft">
        Mínimo 10 caracteres, con mayúscula, minúscula, dígito y símbolo. El usuario deberá cambiarla en su
        primer inicio de sesión.
      </p>

      <div className="mb-4">
        <p className="mb-1.5 block text-sm font-semibold text-ink-soft">Roles</p>
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          {roles?.map((rol) => (
            <Checkbox
              key={rol.id}
              name={rol.id}
              label={ETIQUETAS_ROL[rol.nombre] ?? rol.nombre}
              checked={rolIds.includes(rol.id)}
              onChange={() => alternarRol(rol.id)}
            />
          ))}
        </div>
      </div>

      {error && (
        <p role="alert" aria-live="polite" className="mb-3 text-sm font-medium text-danger">
          {error}
        </p>
      )}

      <div className="flex gap-2">
        <Button size="sm" cargando={guardando} onClick={confirmar}>
          Crear usuario
        </Button>
        <Button variant="secondary" size="sm" onClick={onCancelar}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}
