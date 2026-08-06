import { Check, CheckCheck } from "lucide-react";

import { Button } from "@/shared/components/ui/button";

import { ETIQUETAS_ORIGEN, type Alerta } from "../types";
import { AlertaTipoBadge } from "./AlertaTipoBadge";

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
}

export function AlertaItem({
  alerta,
  onMarcarLeida,
  onResolver,
}: {
  alerta: Alerta;
  onMarcarLeida: (id: string) => void;
  onResolver: (id: string) => void;
}) {
  const noLeida = alerta.estado === "activa" && !alerta.leida_en;

  return (
    <div className={`rounded-md border border-border p-3 ${noLeida ? "bg-primary-tint/40" : "bg-surface"}`}>
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <AlertaTipoBadge tipo={alerta.tipo} />
        <span className="text-xs font-medium text-ink-soft">{ETIQUETAS_ORIGEN[alerta.origen_tipo]}</span>
        <span className="text-xs text-ink-soft">· {formatearFecha(alerta.creado_en)}</span>
      </div>
      <p className="text-sm text-ink">{alerta.mensaje}</p>
      {alerta.estado === "activa" && (
        <div className="mt-2 flex gap-2">
          {!alerta.leida_en && (
            <Button size="sm" variant="ghost" onClick={() => onMarcarLeida(alerta.id)}>
              <Check className="h-3.5 w-3.5" aria-hidden="true" />
              Marcar leída
            </Button>
          )}
          <Button size="sm" variant="secondary" onClick={() => onResolver(alerta.id)}>
            <CheckCheck className="h-3.5 w-3.5" aria-hidden="true" />
            Resolver
          </Button>
        </div>
      )}
    </div>
  );
}
