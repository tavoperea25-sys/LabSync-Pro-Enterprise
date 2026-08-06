import { LogOut, User } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { NotificacionesBell } from "@/features/alertas/components/NotificacionesBell";
import { useAuth } from "@/features/auth/hooks/AuthProvider";
import { Omnibox } from "@/features/busqueda/components/Omnibox";
import { ThemeToggle } from "@/shared/components/ThemeToggle";

/** Ver docs/12-component-library.md — Navbar. Búsqueda global (RF-SEARCH-*)
 * se implementó en Sprint 9, ver `Omnibox`. El centro de notificaciones
 * (RF-ALT-*) se implementó en Sprint 8, ver `NotificacionesBell`. */
export function Navbar() {
  const { usuario, cerrarSesion } = useAuth();
  const navigate = useNavigate();
  const [menuAbierto, setMenuAbierto] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const botonMenuRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!menuAbierto) return;

    function alHacerClicFuera(evt: MouseEvent) {
      if (!menuRef.current?.contains(evt.target as Node)) setMenuAbierto(false);
    }
    function alPresionarTecla(evt: KeyboardEvent) {
      if (evt.key === "Escape") {
        setMenuAbierto(false);
        botonMenuRef.current?.focus();
      }
    }

    document.addEventListener("mousedown", alHacerClicFuera);
    document.addEventListener("keydown", alPresionarTecla);
    return () => {
      document.removeEventListener("mousedown", alHacerClicFuera);
      document.removeEventListener("keydown", alPresionarTecla);
    };
  }, [menuAbierto]);

  async function handleLogout() {
    await cerrarSesion();
    navigate("/login");
  }

  return (
    <header className="flex h-16 flex-shrink-0 items-center justify-between border-b border-border bg-surface px-4 sm:px-6">
      <Omnibox />

      <div className="flex items-center gap-1.5">
        <NotificacionesBell />

        <ThemeToggle />

        <div className="relative ml-1" ref={menuRef}>
          <button
            ref={botonMenuRef}
            type="button"
            onClick={() => setMenuAbierto((v) => !v)}
            aria-haspopup="menu"
            aria-expanded={menuAbierto}
            className="flex h-9 w-9 items-center justify-center overflow-hidden rounded-full bg-primary-100 text-primary-900 transition-colors duration-fast hover:brightness-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-900"
          >
            {usuario?.foto_url ? (
              <img src={usuario.foto_url} alt="" className="h-full w-full object-cover" />
            ) : (
              <User className="h-[18px] w-[18px]" aria-hidden="true" />
            )}
            <span className="sr-only">Menú de perfil de {usuario?.nombre_completo}</span>
          </button>

          {menuAbierto && (
            <div
              role="menu"
              aria-label="Menú de perfil"
              className="absolute right-0 top-11 z-20 w-56 rounded-md border border-border bg-surface p-1.5 shadow-ambient"
            >
              <div className="flex items-center gap-2.5 border-b border-border px-2.5 py-2">
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center overflow-hidden rounded-full bg-primary-100 text-primary-900">
                  {usuario?.foto_url ? (
                    <img src={usuario.foto_url} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <User className="h-4 w-4" aria-hidden="true" />
                  )}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-ink">{usuario?.nombre_completo}</p>
                  <p className="truncate text-xs text-ink-soft">{usuario?.correo}</p>
                </div>
              </div>
              <button
                role="menuitem"
                type="button"
                onClick={handleLogout}
                className="mt-1 flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-ink transition-colors duration-fast hover:bg-surface-alt"
              >
                <LogOut className="h-4 w-4" aria-hidden="true" />
                Cerrar sesión
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
