import { AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/ui/empty-state";

/** `errorElement` de la ruta raíz (ver `router.tsx`) — reemplaza la pantalla
 * de error por defecto del data router (en inglés, y que en desarrollo
 * expone el detalle técnico del error lanzado) por un mensaje genérico en
 * español. No muestra el detalle del error a propósito: no es información
 * útil para quien usa la aplicación, y podría filtrar detalles internos. */
export function RouteErrorPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-alt px-6">
      <EmptyState
        icon={AlertTriangle}
        title="Ocurrió un error inesperado"
        description="Intenta recargar la página. Si el problema persiste, contacta al administrador del sistema."
        action={
          <Button onClick={() => window.location.reload()}>
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Recargar la página
          </Button>
        }
      />
    </div>
  );
}
