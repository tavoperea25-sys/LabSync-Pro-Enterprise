import { Badge } from "@/shared/components/ui/badge";

import { ETIQUETAS_ESTADO_DOCUMENTO } from "../types";

const VARIANTE_POR_ESTADO: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  vigente: "success",
  en_revision: "warning",
  obsoleto: "neutral",
  vencido: "danger",
};

export function DocumentoEstadoBadge({ estado }: { estado: string }) {
  return (
    <Badge variant={VARIANTE_POR_ESTADO[estado] ?? "neutral"}>
      {ETIQUETAS_ESTADO_DOCUMENTO[estado] ?? estado}
    </Badge>
  );
}
