import { Monitor, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/httpClient";
import { Button } from "@/shared/components/ui/button";
import { Checkbox } from "@/shared/components/ui/checkbox";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";

import {
  useActivarUsuario,
  useActualizarUsuario,
  useAsignarRoles,
  useCerrarSesion,
  useDesactivarUsuario,
  useRoles,
  useSesiones,
} from "../hooks/useUsuarios";
import { ETIQUETAS_ROL, type Usuario } from "../types";

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
}

export function PanelUsuario({ usuario }: { usuario: Usuario }) {
  const { data: roles } = useRoles();
  const { data: sesiones, isLoading: cargandoSesiones } = useSesiones(usuario.id);
  const actualizar = useActualizarUsuario();
  const asignarRoles = useAsignarRoles();
  const activar = useActivarUsuario();
  const desactivar = useDesactivarUsuario();
  const cerrarSesion = useCerrarSesion(usuario.id);

  const [nombreCompleto, setNombreCompleto] = useState(usuario.nombre_completo);
  const [error, setError] = useState<string | null>(null);
  const [confirmandoDesactivar, setConfirmandoDesactivar] = useState(false);
  const botonDesactivarRef = useRef<HTMLButtonElement>(null);
  const dialogoDesactivarRef = useRef<HTMLDivElement>(null);
  const idDialogoDesactivar = `confirmar-desactivar-${usuario.id}`;

  // Mismo patrón de foco/teclado ya validado en el Omnibox (RF-SEARCH):
  // foco entra al diálogo al abrir, Escape lo cierra, y la limpieza de esta
  // instancia del efecto (que solo corre mientras `confirmandoDesactivar`
  // es true) devuelve el foco al botón "Desactivar" sin importar qué haya
  // cerrado el diálogo — cancelar, Escape, o confirmar.
  useEffect(() => {
    if (!confirmandoDesactivar) return;
    dialogoDesactivarRef.current?.querySelector("button")?.focus();
    const botonDisparador = botonDesactivarRef.current;
    function alPresionarTecla(evt: KeyboardEvent) {
      if (evt.key === "Escape") setConfirmandoDesactivar(false);
    }
    document.addEventListener("keydown", alPresionarTecla);
    return () => {
      document.removeEventListener("keydown", alPresionarTecla);
      botonDisparador?.focus();
    };
  }, [confirmandoDesactivar]);

  /** Trampa de foco del diálogo de confirmación — solo dos botones, mismo
   * criterio que la trampa del Omnibox (consulta los focoseables en cada
   * pulsación, sin cachear). */
  function alPresionarTeclaEnDialogo(evt: React.KeyboardEvent<HTMLDivElement>) {
    if (evt.key !== "Tab" || !dialogoDesactivarRef.current) return;
    const focosables = Array.from(dialogoDesactivarRef.current.querySelectorAll<HTMLElement>("button"));
    if (focosables.length === 0) return;
    const primero = focosables[0];
    const ultimo = focosables[focosables.length - 1];
    if (!primero || !ultimo) return;
    if (evt.shiftKey && document.activeElement === primero) {
      evt.preventDefault();
      ultimo.focus();
    } else if (!evt.shiftKey && document.activeElement === ultimo) {
      evt.preventDefault();
      primero.focus();
    }
  }

  const rolIdsActuales = (roles ?? []).filter((r) => usuario.roles.includes(r.nombre)).map((r) => r.id);

  async function guardarNombre() {
    if (nombreCompleto.trim() === usuario.nombre_completo) return;
    try {
      await actualizar.mutateAsync({ id: usuario.id, datos: { nombre_completo: nombreCompleto.trim() } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo actualizar el nombre.");
    }
  }

  async function alternarRol(rolId: string) {
    const nuevos = rolIdsActuales.includes(rolId)
      ? rolIdsActuales.filter((id) => id !== rolId)
      : [...rolIdsActuales, rolId];
    setError(null);
    try {
      await asignarRoles.mutateAsync({ id: usuario.id, rolIds: nuevos });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron actualizar los roles.");
    }
  }

  async function activarUsuario() {
    setError(null);
    try {
      await activar.mutateAsync(usuario.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cambiar el estado.");
    }
  }

  async function confirmarDesactivar() {
    setError(null);
    try {
      await desactivar.mutateAsync(usuario.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cambiar el estado.");
    } finally {
      setConfirmandoDesactivar(false);
    }
  }

  return (
    <div className="space-y-4 border-t border-border bg-surface-alt p-4">
      {error && (
        <p role="alert" aria-live="polite" className="text-sm font-medium text-danger">
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-end gap-2">
        <div className="max-w-xs flex-1">
          <Input
            label="Nombre completo"
            value={nombreCompleto}
            onChange={(e) => setNombreCompleto(e.target.value)}
            onBlur={guardarNombre}
          />
        </div>
        <Button
          ref={botonDesactivarRef}
          size="sm"
          variant={usuario.estado === "activo" ? "destructive" : "secondary"}
          cargando={activar.isPending || desactivar.isPending}
          aria-haspopup={usuario.estado === "activo" ? "dialog" : undefined}
          aria-expanded={usuario.estado === "activo" ? confirmandoDesactivar : undefined}
          aria-controls={usuario.estado === "activo" ? idDialogoDesactivar : undefined}
          onClick={() => (usuario.estado === "activo" ? setConfirmandoDesactivar(true) : activarUsuario())}
        >
          {usuario.estado === "activo" ? "Desactivar" : "Activar"}
        </Button>
      </div>

      {confirmandoDesactivar && (
        <div
          id={idDialogoDesactivar}
          ref={dialogoDesactivarRef}
          role="alertdialog"
          aria-modal="true"
          aria-labelledby={`${idDialogoDesactivar}-titulo`}
          onKeyDown={alPresionarTeclaEnDialogo}
          className="rounded-md border border-danger/30 bg-[#FEF2F2] p-4"
        >
          <p id={`${idDialogoDesactivar}-titulo`} className="mb-1 text-sm font-semibold text-[#991B1B]">
            ¿Desactivar a {usuario.nombre_completo}?
          </p>
          <p className="mb-3 text-sm text-[#7F1D1D]">
            No podrá iniciar sesión hasta que se reactive su cuenta. Su historial y roles se conservan.
          </p>
          <div className="flex gap-2">
            <Button variant="destructive" size="sm" cargando={desactivar.isPending} onClick={confirmarDesactivar}>
              Sí, desactivar
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setConfirmandoDesactivar(false)}>
              Cancelar
            </Button>
          </div>
        </div>
      )}

      <div>
        <p className="mb-1.5 text-sm font-semibold text-ink-soft">Roles</p>
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          {roles?.map((rol) => (
            <Checkbox
              key={rol.id}
              name={rol.id}
              label={ETIQUETAS_ROL[rol.nombre] ?? rol.nombre}
              checked={rolIdsActuales.includes(rol.id)}
              onChange={() => alternarRol(rol.id)}
              disabled={asignarRoles.isPending}
            />
          ))}
        </div>
      </div>

      <div>
        <p className="mb-1.5 flex items-center gap-1.5 text-sm font-semibold text-ink-soft">
          <Monitor className="h-4 w-4" aria-hidden="true" />
          Sesiones activas
        </p>
        {cargandoSesiones && <Skeleton className="h-10 w-full" />}
        {!cargandoSesiones && sesiones?.length === 0 && (
          <p className="text-sm text-ink-soft">Sin sesiones activas.</p>
        )}
        {!!sesiones?.length && (
          <ul className="space-y-1.5">
            {sesiones.map((sesion) => (
              <li
                key={sesion.id}
                className="flex items-center justify-between gap-2 rounded-md border border-border bg-surface px-3 py-2 text-sm"
              >
                <div className="min-w-0">
                  <p className="truncate text-ink">{sesion.user_agent || "Dispositivo desconocido"}</p>
                  <p className="text-xs text-ink-soft">
                    {sesion.ip_origen ?? "IP desconocida"} · desde {formatearFecha(sesion.creado_en)}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  title="Cerrar esta sesión"
                  aria-label="Cerrar esta sesión"
                  cargando={cerrarSesion.isPending}
                  onClick={() => cerrarSesion.mutate(sesion.id)}
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
