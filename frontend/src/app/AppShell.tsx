import { Suspense, type ReactNode } from "react";

import { NotificacionesProvider } from "@/features/alertas/hooks/NotificacionesProvider";

import { Navbar } from "./Navbar";
import { RouteFallback } from "./RouteFallback";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <NotificacionesProvider>
      <div className="flex h-dvh overflow-hidden bg-surface-alt">
        <a
          href="#contenido-principal"
          className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-primary-900 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white"
        >
          Saltar al contenido principal
        </a>
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Navbar />
          <main id="contenido-principal" tabIndex={-1} className="flex-1 overflow-y-auto">
            {/* La barra lateral y la navbar quedan fuera de este límite de
                Suspense a propósito — al cambiar de ruta, solo el contenido
                se reemplaza por el fallback; el chrome de navegación nunca
                desaparece ni parpadea. */}
            <Suspense fallback={<RouteFallback className="h-full" />}>{children}</Suspense>
          </main>
        </div>
      </div>
    </NotificacionesProvider>
  );
}
