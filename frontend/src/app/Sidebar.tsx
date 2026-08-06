import { FlaskConical } from "lucide-react";
import { NavLink } from "react-router-dom";

import { useAuth } from "@/features/auth/hooks/AuthProvider";

import { navItemsParaRoles } from "./navigation";

/** Ver docs/12-component-library.md — Sidebar. Navegación primaria,
 * filtrada por rol; el ítem activo se marca con `aria-current="page"`
 * además del estilo visual (nunca solo color). */
export function Sidebar() {
  const { usuario } = useAuth();
  const items = navItemsParaRoles(usuario?.roles ?? []);

  return (
    <aside className="hidden w-60 flex-shrink-0 flex-col border-r border-border bg-surface md:flex">
      <div className="flex h-16 items-center gap-2 border-b border-border px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-900">
          <FlaskConical className="h-4 w-4 text-white" aria-hidden="true" />
        </div>
        <span className="font-display text-sm font-semibold text-ink">LabSync Pro</span>
      </div>

      <nav aria-label="Principal" className="flex-1 space-y-1 overflow-y-auto p-3">
        {items.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-fast ${
                isActive
                  ? "border-l-2 border-primary-900 bg-primary-100 text-primary-900"
                  : "text-ink-soft hover:bg-surface-alt hover:text-ink"
              }`
            }
            end={item.path === "/dashboard"}
          >
            <item.icon className="h-[18px] w-[18px] flex-shrink-0" aria-hidden="true" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
